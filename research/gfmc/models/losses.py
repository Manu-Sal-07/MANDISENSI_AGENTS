"""The SPO+ surrogate loss for choosing the best of a finite set of actions.

For a maximisation problem with predicted revenues r_hat and realised revenues
r over a finite action set S, with a* = argmax_S r:

    SPO+(r_hat, r) = max_{a in S} (2 r_hat_a - r_a) - 2 r_hat_{a*} + r_{a*}

It is convex in r_hat, upper-bounds the regret of the decision induced by
r_hat, and is Fisher-consistent (Elmachtoub & Grigas 2022, Thm 1 and 2). It is
exact here because the farmer's revenue is affine in the predicted prices.
"""

from __future__ import annotations

import torch

NEG = -1e9


def spo_plus(r_hat: torch.Tensor, r: torch.Tensor, amask: torch.Tensor) -> torch.Tensor:
    """Per-sample SPO+ loss.

    r_hat, r : (..., A)   predicted / realised revenue
    amask    : (..., A)   True for actions the farmer is offered
    returns  : (...)      loss >= 0, zero when r_hat ranks the offered actions as r does
    """
    r_masked = r.masked_fill(~amask, NEG)
    a_star = r_masked.argmax(-1, keepdim=True)                              # (..., 1)
    term1 = (2.0 * r_hat - r).masked_fill(~amask, NEG).max(-1).values
    rh_star = r_hat.gather(-1, a_star).squeeze(-1)
    r_star = r.gather(-1, a_star).squeeze(-1)
    return term1 - 2.0 * rh_star + r_star


def regret(r_hat: torch.Tensor, r: torch.Tensor, amask: torch.Tensor) -> torch.Tensor:
    """Realised regret of the decision argmax(r_hat): best achievable minus achieved."""
    best = r.masked_fill(~amask, NEG).max(-1).values
    pick = r_hat.masked_fill(~amask, NEG).argmax(-1, keepdim=True)
    got = r.gather(-1, pick).squeeze(-1)
    return best - got
