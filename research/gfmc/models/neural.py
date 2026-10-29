"""DeepSets price-vector network trained with a choice of loss.

Architecture. Each market's features pass through a shared encoder f; an
order-invariant context (masked mean of the encoded markets) is concatenated
back to every market and a shared head g emits the four hold-k log-returns.
Parameter sharing keeps the model small enough for ~2,000 training days, and
the context lets one market's silence or price move inform another's forecast.

Losses (the only thing that differs between the compared neural models):

* ``mse_obs``    MSE on log-returns at observed (market, hold) cells only. The
                 standard "predict" objective.
* ``mse_filled`` MSE on the same labels the decision loss sees, i.e. log of the
                 *realised* price including the fallback for silent mandis.
* ``spo``        SPO+ regret on the farmer's net revenue, plus ``aux`` times the
                 filled-MSE as a scale anchor (SPO+ alone does not pin levels).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

from gfmc import econ as E
from gfmc.config import N_HOLD, SEED, Economics
from gfmc.data import registry
from gfmc.dataset import DecisionData
from gfmc.models.base import PriceModel, standardise
from gfmc.models.losses import spo_plus

RS_SCALE = 1000.0   # revenues are expressed in thousands of rupees inside the loss


class DeepSets(nn.Module):
    def __init__(self, n_features: int, n_markets: int, emb: int = 4, hidden: int = 64, depth: int = 2,
                 dropout: float = 0.1, heads: int = 1):
        super().__init__()
        self.heads = heads
        self.emb = nn.Embedding(n_markets, emb)
        layers, d = [], n_features + emb
        for _ in range(depth):
            layers += [nn.Linear(d, hidden), nn.GELU(), nn.Dropout(dropout)]
            d = hidden
        self.f = nn.Sequential(*layers)
        self.g = nn.Sequential(nn.Linear(2 * hidden, hidden), nn.GELU(), nn.Linear(hidden, heads * N_HOLD))
        nn.init.zeros_(self.g[-1].weight)       # start exactly at the random walk
        nn.init.zeros_(self.g[-1].bias)
        if heads == 2:                          # reporting head starts at "reports with p ~ 0.85"
            with torch.no_grad():
                self.g[-1].bias[N_HOLD:] = 1.7

    def forward(self, x: torch.Tensor, elig: torch.Tensor) -> torch.Tensor:
        B, M, _ = x.shape
        e = self.emb.weight.unsqueeze(0).expand(B, M, -1)
        h = self.f(torch.cat([x, e], dim=-1))
        w = elig.float().unsqueeze(-1)
        ctx = (h * w).sum(1) / w.sum(1).clamp(min=1.0)
        out = self.g(torch.cat([h, ctx.unsqueeze(1).expand(B, M, -1)], dim=-1))
        return out if self.heads == 1 else out.view(B, M, 2, N_HOLD)


@dataclass
class Tensors:
    X: torch.Tensor           # (n, M, F)
    elig: torch.Tensor        # (n, M)
    ref_price: torch.Tensor   # (n, M)
    y_obs: torch.Tensor       # (n, M, K) log-return, 0 where unobserved
    obs: torch.Tensor         # (n, M, K) bool
    y_fill: torch.Tensor      # (n, M, K) log(realised price / ref)
    R: torch.Tensor           # (n, O, A) realised revenue / RS_SCALE
    amask: torch.Tensor       # (n, A)


def origin_costs(dd: DecisionData, econ: Economics, origins: Dict[str, Tuple[float, float]]) -> np.ndarray:
    """(O, M) Rs/quintal trip cost from every origin to every market."""
    return np.stack([E.trip_cost(dd.panel.dist_km(o), econ) for o in origins.values()])


def make_tensors(dd: DecisionData, idx: np.ndarray, econ: Economics, cols: np.ndarray, norm,
                 origins: Dict[str, Tuple[float, float]]) -> Tensors:
    ref = np.exp(np.nan_to_num(dd.ref_lp[idx], nan=0.0))
    realised = dd.realised_price(econ)[idx]
    with np.errstate(invalid="ignore", divide="ignore"):
        y_fill = np.log(np.where(realised > 0, realised, np.nan) / ref[:, :, None])
    y_fill = np.nan_to_num(y_fill, nan=0.0)
    R = np.stack([dd.realised_revenue(o, econ)[idx] for o in origins.values()], axis=1) / RS_SCALE
    t = lambda a, dt=torch.float32: torch.as_tensor(np.ascontiguousarray(a), dtype=dt)
    return Tensors(
        X=t(norm(dd.X[idx][:, :, cols])), elig=t(dd.elig[idx], torch.bool), ref_price=t(ref),
        y_obs=t(np.nan_to_num(dd.Y[idx], nan=0.0)), obs=t(dd.obs[idx] & dd.elig[idx][:, :, None], torch.bool),
        y_fill=t(y_fill), R=t(R), amask=t(dd.action_mask()[idx], torch.bool),
    )


def predicted_revenue(yhat: torch.Tensor, ref_price: torch.Tensor, elig: torch.Tensor, cost: torch.Tensor,
                      econ: Economics) -> torch.Tensor:
    """(n, O, A) predicted revenue (in RS_SCALE units) for every action and origin."""
    return revenue_from_price(ref_price.unsqueeze(-1) * torch.exp(yhat), elig, cost, econ)


def revenue_from_price(p_hat: torch.Tensor, elig: torch.Tensor, cost: torch.Tensor, econ: Economics) -> torch.Tensor:
    """Revenue of every action from an (n, M, K) expected-price tensor."""
    disc = torch.as_tensor(E.hold_discount(econ), dtype=torch.float32)
    rev = p_hat.unsqueeze(1) * disc - cost.unsqueeze(0).unsqueeze(-1)        # (n, O, M, K)
    flat = rev.flatten(2)                                                    # (n, O, M*K)
    w = elig.float()
    gate_price = (p_hat[:, :, 0] * w).sum(1) / w.sum(1).clamp(min=1.0)       # (n,)
    gate = (econ.farmgate_discount * gate_price).view(-1, 1, 1).expand(-1, flat.shape[1], 1)
    return torch.cat([flat, gate], dim=-1) / RS_SCALE


class DeepSetsModel(PriceModel):
    """DeepSets network with a selectable training loss."""

    def __init__(self, loss: str = "spo", hidden: int = 64, depth: int = 2, dropout: float = 0.1, emb: int = 4,
                 lr: float = 3e-3, weight_decay: float = 1e-4, epochs: int = 60, batch: int = 64, aux: float = 0.3,
                 huber: float = 0.15, n_seeds: int = 1, origins: Optional[Dict[str, Tuple[float, float]]] = None,
                 name: Optional[str] = None, structured: bool = False, w_rep: float = 0.5):
        assert loss in ("mse_obs", "mse_filled", "spo")
        assert not structured or loss == "spo"
        self.structured, self.w_rep = structured, w_rep
        self.report_prob_: Optional[np.ndarray] = None
        self.loss, self.hidden, self.depth, self.dropout, self.emb = loss, hidden, depth, dropout, emb
        self.lr, self.weight_decay, self.epochs, self.batch = lr, weight_decay, epochs, batch
        self.aux, self.huber, self.n_seeds = aux, huber, n_seeds
        self.origins = origins or registry.ORIGINS
        self.name = name or f"deepsets_{loss}"
        self.nets: list = []
        self.cols = None
        self.norm = None

    # ---- training -------------------------------------------------------
    def _expected_price(self, out: torch.Tensor, ref: torch.Tensor, elig: torch.Tensor, econ: Economics):
        """Structured head -> expected realised price (n, M, K), price head, report logits."""
        y, logit = out[:, :, 0, :], out[:, :, 1, :]
        p_hat = ref.unsqueeze(-1) * torch.exp(y)
        w = elig.float().unsqueeze(-1)
        p_bar = (p_hat * w).sum(1, keepdim=True) / w.sum(1, keepdim=True).clamp(min=1.0)     # (n, 1, K)
        rho = torch.sigmoid(logit)
        return rho * p_hat + (1.0 - rho) * econ.fallback_discount * p_bar, y, logit

    def _loss_structured(self, out, b: Tensors, cost, econ):
        hub = nn.functional.huber_loss
        e_price, y, logit = self._expected_price(out, b.ref_price, b.elig, econ)
        r_hat = revenue_from_price(e_price, b.elig, cost, econ)
        spo = spo_plus(r_hat, b.R, b.amask.unsqueeze(1).expand_as(b.R)).mean()
        price_loss = hub(y[b.obs], b.y_obs[b.obs], delta=self.huber) if b.obs.any() else y.sum() * 0.0
        cell = b.elig.unsqueeze(-1).expand_as(logit)
        rep_loss = nn.functional.binary_cross_entropy_with_logits(logit[cell], b.obs[cell].float())
        return spo + self.aux * price_loss + self.w_rep * rep_loss

    def _loss(self, yhat: torch.Tensor, b: Tensors, cost: torch.Tensor, econ: Economics) -> torch.Tensor:
        if self.structured:
            return self._loss_structured(yhat, b, cost, econ)
        hub = nn.functional.huber_loss
        if self.loss == "mse_obs":
            m = b.obs
            return hub(yhat[m], b.y_obs[m], delta=self.huber) if m.any() else yhat.sum() * 0.0
        m = b.elig.unsqueeze(-1).expand_as(yhat)
        filled = hub(yhat[m], b.y_fill[m], delta=self.huber)
        if self.loss == "mse_filled":
            return filled
        r_hat = predicted_revenue(yhat, b.ref_price, b.elig, cost, econ)
        return spo_plus(r_hat, b.R, b.amask.unsqueeze(1).expand_as(b.R)).mean() + self.aux * filled

    def fit(self, dd, idx, econ, cols):
        torch.set_num_threads(2)
        self.cols = cols
        self.econ = econ
        self.norm = standardise(dd.X[idx][:, :, cols], dd.elig[idx])
        tr = make_tensors(dd, idx, econ, cols, self.norm, self.origins)
        cost = torch.as_tensor(origin_costs(dd, econ, self.origins), dtype=torch.float32)
        n = len(idx)
        self.nets = []
        for s in range(self.n_seeds):
            torch.manual_seed(SEED + 17 * s)
            net = DeepSets(len(cols), dd.M, self.emb, self.hidden, self.depth, self.dropout,
                           heads=2 if self.structured else 1)
            opt = torch.optim.AdamW(net.parameters(), lr=self.lr, weight_decay=self.weight_decay)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(self.epochs, 1))
            gen = torch.Generator().manual_seed(SEED + s)
            for _ in range(self.epochs):
                net.train()
                perm = torch.randperm(n, generator=gen)
                for i in range(0, n, self.batch):
                    j = perm[i:i + self.batch]
                    b = Tensors(*(getattr(tr, f)[j] for f in Tensors.__dataclass_fields__))
                    loss = self._loss(net(b.X, b.elig), b, cost, econ)
                    opt.zero_grad()
                    loss.backward()
                    nn.utils.clip_grad_norm_(net.parameters(), 1.0)
                    opt.step()
                sched.step()
            net.eval()
            self.nets.append(net)
        return self

    # ---- inference ------------------------------------------------------
    @torch.no_grad()
    def predict(self, dd, idx):
        X = torch.as_tensor(self.norm(dd.X[idx][:, :, self.cols]), dtype=torch.float32)
        elig = torch.as_tensor(dd.elig[idx])
        out = torch.stack([net(X, elig) for net in self.nets]).mean(0)
        if not self.structured:
            return out.numpy().astype(float)
        ref = torch.as_tensor(np.exp(np.nan_to_num(dd.ref_lp[idx], nan=0.0)), dtype=torch.float32)
        e_price, _, logit = self._expected_price(out, ref, elig, self.econ)
        self.report_prob_ = torch.sigmoid(logit).numpy().astype(float)
        return torch.log(e_price / ref.unsqueeze(-1)).numpy().astype(float)
