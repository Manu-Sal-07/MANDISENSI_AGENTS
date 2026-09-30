# MandiSense AI

A decision-support platform for Indian mandi (agricultural market) prices: a forecasting
pipeline (specialist agents fused with a regime-aware weighting layer), calibrated
uncertainty bands, a sell/hold/wait decision policy with an abstain option, and a
farmer-facing web app in Kannada, Hindi and English.

The forecasting and evaluation methodology, walk-forward statistical results and their
limitations are written up in `IEEE_Paper/`, `IEEE_Access/` and `CICPS2027/`. This README
covers running the code, not the research claims — see those papers for what is actually
proven on real data, and their `experiments/` folders for the reproducible evaluation.

## Layout

- `mandisense_ai/` — the Python package: forecasting pipeline, decision policy,
  farmer-facing feature endpoints (`mandisense_ai/farmer/`), the intelligence/brief
  layer, and tests.
- `api/` — the FastAPI app that serves the platform (`api/main.py`). This is the live
  backend; `backend/app/` supplies the discovery-feed routes it mounts.
- `frontend/` — the Next.js app: a farmer-facing surface (`/`, `/sell-plan`,
  `/my-money`, `/tools`) and a trader-facing surface (`/terminal`,
  `/market-explorer`, `/intelligence-lab`).
- `scripts/` — operational scripts (nightly retraining job, DB init, validation suite).
- `data/`, `models/` — observation store, trained model bundles and the forecast store
  the API reads at request time (the API runs no model inference live).

## Running it locally

Backend (from `mandisense_ai/`'s parent, i.e. this directory):

```bash
python -m venv ms_env && ms_env/Scripts/activate   # or source ms_env/bin/activate
pip install -e .
python -m uvicorn api.main:app --port 8000
```

Frontend:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev -- -p 3001
```

Then open `http://localhost:3001`.

## Tests

```bash
python -m pytest mandisense_ai --ignore=mandisense_ai/scratch
```

## Data sources

Real observed prices come from data.gov.in's Agmarknet dataset (`mandisense_ai/forecasting/sources/datagov.py`)
and, optionally, the CEDA Agri Market API. A `DATAGOV_API_KEY` env var is recommended for
production (a shared rate-limited sample key is used otherwise — see
`mandisense_ai/forecasting/config.py`). The bundled `mandisense_ai/data/processed/v4/`
Karnataka dataset used by some trader-side views does **not** match the real Agmarknet
archive and should not be treated as real market history; see the papers' audit of this.
