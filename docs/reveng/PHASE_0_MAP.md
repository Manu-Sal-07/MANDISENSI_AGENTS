# Phase 0 — Repository Map & Coverage Ledger

> **AUTHORED BY THE PHASE-1 AUDITOR, 2026-09-06. THIS IS NOT A RECOVERED ARTEFACT.**
>
> The Phase-1 task instructed the auditor to read this file and work through the files it
> assigned to Phase 1. **The file did not exist** — `docs/reveng/` contained only
> `PHASE_7_EDA_VIZ.md`, and `find "d:/BMS COLL/PROJECT" -iname "PHASE_0*"` returned nothing.
> This ledger was therefore constructed from the Phase-1 mandatory search sweep plus a full
> traversal of the data directories, so that Step 7 has a target and later phases inherit a
> ledger. Its **Phase** assignments are the auditor's judgement, not a prior phase's.
>
> **Root:** `d:\BMS COLL\PROJECT\MS-AI\MS-AI\` — all paths below are relative to it.

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `COVERED-P1` | Opened, and every claim made about it in `PHASE_1_SOURCES.md` rests on a region actually read — not on grep output alone. |
| `PENDING` | Not opened, or opened only far enough to see grep hits. Any citation to it in Phase 1 rests on a `rg` line, which is evidence but not the full read R5 requires. |
| `OUT-OF-SCOPE-P1` | Contains no data-acquisition surface; assigned to a later phase. |

---

## Phase 1 assignment — acquisition surface (68 files)

### 1A. External fetch clients

| # | File | Phase | Status | Note |
|---|---|---|---|---|
| 1 | `mandisense_ai/lib/agmarknet_client.py` | 1 | `COVERED-P1` | Read in full (150 lines). Source S2. |
| 2 | `mandisense_ai/core/agents/external_factors_agent/ingestion/weather_fetcher.py` | 1 | `COVERED-P1` | Read in full (267 lines). Source S3. |
| 3 | `mandisense_ai/core/agents/external_factors_agent/ingestion/news_fetcher.py` | 1 | `COVERED-P1` | Read in full (254 lines). Source S4. |
| 4 | `mandisense_ai/core/agents/external_factors_agent/ingestion/news_ingestor.py` | 1 | `COVERED-P1` | Read in full (61 lines). Sources S4, S12. |
| 5 | `mandisense_ai/core/agents/external_factors_agent/ingestion/__init__.py` | 1 | `COVERED-P1` | Read in full (1 line: a comment). No exports. |
| 6 | `mandisense_ai/services/mandi_data_service.py` | 1 | `COVERED-P1` | Read in full (149 lines). Sources S2, S13. |
| 7 | `backend/services/mandi_data_service.py` | 1 | `COVERED-P1` | Read in full (3 lines). Re-export shim. |
| 8 | `mandisense_ai/lib/validator.py` | 1 | `COVERED-P1` | Read in full (47 lines). Gates S2/S13. |
| 9 | `mandisense_ai/services/__init__.py` | 1 | `COVERED-P1` | Read in full. Establishes S2 has no live caller. |
| 10 | `mandisense_ai/core/agents/external_factors_agent/__init__.py` | 1 | `COVERED-P1` | Read in full (71 lines). Live EFA entry point; `policy_signal = 0.0`. |
| 11 | `mandisense_ai/core/agents/external_factors_agent/processing/weather_signal.py` | 1 | `COVERED-P1` | Read L1–L60 and L180–L234 — covers every claim (coord resolution, fetch call, swallow). |
| 12 | `mandisense_ai/core/agents/external_factors_agent/orchestration/config_manager.py` | 1 | `COVERED-P1` | Read in full (16 lines). `NEWS_API_KEY` resolution. |
| 13 | `mandisense_ai/core/agents/external_factors_agent/orchestration/pipeline_runner.py` | 1 | `COVERED-P1` | Read L1–L60 (the complete import block); unimportability verified by executing the import. |
| 14 | `mandisense_ai/cognition/test_breaker.py` | 1 | `COVERED-P1` | Read in full (25 lines). Source S18. |
| 15 | `scratch/capture_traderos.py` | 1 | `PENDING` | Read L40–L75 only. Source S17 field 11 (landing location) is `UNKNOWN` as a direct result. |

### 1B. Synthetic / in-code data generators

| # | File | Phase | Status | Note |
|---|---|---|---|---|
| 16 | `mandisense_ai/tasks/ingest_historical_data.py` | 1 | `COVERED-P1` | Read in full (157 lines). **Source S7 — the generator behind the served dataset.** |
| 17 | `mandisense_ai/scratch/generate_mandi_master.py` | 1 | `COVERED-P1` | Read in full (69 lines). Source S8. |
| 18 | `mandisense_ai/core/agents/external_factors_agent/ml/dataset_builder.py` | 1 | `COVERED-P1` | Read in full (52 lines). Source S11. |
| 19 | `mandisense_ai/cognition/world_model/topology.py` | 1 | `COVERED-P1` | Read L1–L70 — covers `MANDI_COORDS`, `DISTRICT_MAPPINGS`, `resolve_coordinates`. Source S14. |
| 20 | `scratch/generate_cross_commodity_suite.py` | 1 | `COVERED-P1` | Read L15–L35 — the complete data-definition block. Source S15. |
| 21 | `scratch/generate_system_latency.py` | 1 | `COVERED-P1` | Read L10–L55 — the complete generation block. Source S16. |
| 22 | `scratch/generate_shap_plots.py` | 1 | `COVERED-P1` | Read L55–L80 — the synthetic-feature block. |
| 23 | `scratch/generate_decision_performance.py` | 1 | `COVERED-P1` | Read L50–L72 — the label-perturbation block. |
| 24 | `scratch/generate_agent_contribution.py` | 1 | `COVERED-P1` | Read L20–L50 and L100–L165 — loader plus synthetic back-fill. |
| 25 | `scratch/generate_plot.py` | 1 | `COVERED-P1` | Read L1–L40. Reads v4 (synthetic); fabricates `predicted_price`. |
| 26 | `scratch/generate_regime_timeline.py` | 1 | `PENDING` | Only L32–L33 seen via grep. The data-path claim is grep-backed; the EGARCH/HMM body is unread. |
| 27 | `scratch/check_data_regimes.py` | 1 | `PENDING` | Only L6 seen via grep (reader of `meta_predictions.jsonl`). |

### 1C. Transformation chain v1 → v4 (acquisition-adjacent: these define the served dataset)

| # | File | Phase | Status | Note |
|---|---|---|---|---|
| 28 | `mandisense_ai/tasks/refine_raw_data.py` | 1 | `COVERED-P1` | Read in full (178 lines). v1→v2; non-idempotent master mutation. |
| 29 | `mandisense_ai/tasks/finalize_raw_data.py` | 1 | `COVERED-P1` | Read in full (98 lines). v2→v3. |
| 30 | `mandisense_ai/tasks/finalize_v4_dataset.py` | 1 | `COVERED-P1` | Read in full (108 lines). v3→v4. |
| 31 | `mandisense_ai/data/prepare_datasets.py` | 1 | `COVERED-P1` | Read in full (150 lines). The **only** consumer of the real Agmarknet CSVs into `processed/{commodity}/`. |
| 32 | `mandisense_ai/data/ingestion/agmarknet_ingestor.py` | 1 | `COVERED-P1` | Read in full (92 lines). Glob-reads `data/raw/*.csv`. |
| 33 | `mandisense_ai/data/preprocessing/pipeline.py` | 1 | `COVERED-P1` | Read L1–L130 and L200–L300; all write calls located by grep and confirmed in the read regions. |
| 34 | `mandisense_ai/data/preprocessing/config.py` | 1 | `COVERED-P1` | Read in full (106 lines). Output paths, formats, horizons. |
| 35 | `mandisense_ai/data/repository.py` | 1 | `COVERED-P1` | Read in full (64 lines). Parquet read layer. |
| 36 | `mandisense_ai/core/data/data_service.py` | 1 | `COVERED-P1` | Read in full (177 lines). **The live API read path — v4 synthetic CSVs.** |
| 37 | `mandisense_ai/tasks/backfill.py` | 1 | `COVERED-P1` | Read in full (138 lines). Broken `_prices.csv` path; `TODO` for `market_prices`. |
| 38 | `mandisense_ai/data/preprocessing/cleaner.py` | 2 | `OUT-OF-SCOPE-P1` | Transformation stage; no acquisition surface. |
| 39 | `mandisense_ai/data/preprocessing/enhanced_cleaner.py` | 2 | `OUT-OF-SCOPE-P1` | As above. |
| 40 | `mandisense_ai/data/preprocessing/outlier_handler.py` | 2 | `OUT-OF-SCOPE-P1` | As above. |
| 41 | `mandisense_ai/data/preprocessing/schema_normalizer.py` | 2 | `OUT-OF-SCOPE-P1` | As above. |
| 42 | `mandisense_ai/data/preprocessing/target_engineer.py` | 2 | `OUT-OF-SCOPE-P1` | As above. |
| 43 | `mandisense_ai/data/preprocessing/validator.py` | 2 | `OUT-OF-SCOPE-P1` | As above. |
| 44 | `mandisense_ai/data/preprocessing/feature_engineering.py` | 2 | `OUT-OF-SCOPE-P1` | As above. |
| 45 | `mandisense_ai/data/preprocessing/agent_features.py` | 2 | `OUT-OF-SCOPE-P1` | As above. |

### 1D. Storage back-ends and sinks

| # | File | Phase | Status | Note |
|---|---|---|---|---|
| 46 | `mandisense_ai/db/connection.py` | 1 | `COVERED-P1` | Read in full (218 lines). Source S5. |
| 47 | `mandisense_ai/db/schema.sql` | 1 | `COVERED-P1` | Read in full (170 lines). All five table DDLs. |
| 48 | `mandisense_ai/db/queries.py` | 1 | `COVERED-P1` | Read L125–L180; every `SELECT`/`INSERT` located by grep and confirmed. Market-data section is dead. |
| 49 | `scripts/init_db.py` | 1 | `COVERED-P1` | Read in full (93 lines). Bootstraps the schema. |
| 50 | `mandisense_ai/lib/cache.py` | 1 | `COVERED-P1` | Read L1–L60 plus the file-fallback region located by grep. Source S6. |
| 51 | `mandisense_ai/ensemble/prediction_logger.py` | 1 | `COVERED-P1` | Read L20–L70. JSONL landing location. |
| 52 | `mandisense_ai/db/client.py` | 1 | `PENDING` | SQL statements located by grep only; not opened. Sink, not source. |
| 53 | `mandisense_ai/db/prediction_logger_db.py` | 1 | `PENDING` | As above. |
| 54 | `mandisense_ai/db/migrate_jsonl_to_pg.py` | 1 | `PENDING` | As above. |
| 55 | `mandisense_ai/ensemble/feedback_store.py` | 1 | `PENDING` | Only L42 seen via grep. |
| 56 | `mandisense_ai/core/agents/external_factors_agent/adaptive/feedback_store.py` | 1 | `COVERED-P1` | Read in full (35 lines). CWD-relative read/write. |
| 57 | `mandisense_ai/core/agents/external_factors_agent/orchestration/cache_manager.py` | 1 | `PENDING` | Only L5–L22 seen via grep. |

### 1E. Configuration, environment and deployment

| # | File | Phase | Status | Note |
|---|---|---|---|---|
| 58 | `.env` / `.env.example` | 1 | `COVERED-P1` | Read in full (50 lines); confirmed byte-identical by `diff`. |
| 59 | `render.yaml` | 1 | `COVERED-P1` | Read in full (31 lines). No worker, no `NEWS_API_KEY`. |
| 60 | `.gitignore` (root) | 1 | `COVERED-P1` | Read in full. The v4 carve-out. |
| 61 | `mandisense_ai/.gitignore` | 1 | `PENDING` | Read L40–L50 only; `git check-ignore` used to confirm effect. |
| 62 | `mandisense_ai/config/settings.py` | 1 | `COVERED-P1` | Read in full (95 lines). Path resolution verified by executing it. |
| 63 | `docker-compose.yml` | 1 | `PENDING` | Only L25 seen via grep (the `curl` healthcheck). |

### 1F. Downstream consumers cited for the reader column

| # | File | Phase | Status | Note |
|---|---|---|---|---|
| 64 | `mandisense_ai/core/agents/inference_engine_v3.py` | 1 | `COVERED-P1` | Read L1–L90 — model load and data-service call. The live inference path. |
| 65 | `mandisense_ai/core/agents/arrival/train_arrival.py` | 1 | `COVERED-P1` | Read L1–L40 — path constants and all four `read_csv` calls. |
| 66 | `mandisense_ai/core/agents/external_factors_agent/ml/trainer.py` | 1 | `COVERED-P1` | Read L1–L40. |
| 67 | `mandisense_ai/evaluation/backtester.py` | 1 | `COVERED-P1` | Read L1–L60 — the historical-replay file resolution. |
| 68 | `mandisense_ai/evaluation/error_boxplot.py` | 1 | `COVERED-P1` | Read L10–L30 and the `__main__` block. |
| 69 | `README.md` | 1 | `COVERED-P1` | Read L25–L45, L105–L140, L400–L420 plus a targeted grep. Every §7 claim lies in a read region. |
| 70 | `mandisense_ai/core/agents/seasonality_agent.py` | 1 | `PENDING` | Read L20–L55 only; the `L261` repository call is grep-backed. |
| 71 | `mandisense_ai/core/agents/training_pipeline.py` | 1 | `PENDING` | Grep only (L11, L47, L151). |
| 72 | `mandisense_ai/core/agents/training_pipeline_v2.py` | 1 | `PENDING` | Grep only (L11, L57, L175–L181). |
| 73 | `mandisense_ai/core/agents/calibration_engine.py` | 1 | `PENDING` | Grep only (L9, L44, L108, L115–L119). |
| 74 | `mandisense_ai/core/agents/inference_engine.py` | 1 | `PENDING` | Grep only (L39–L40). |
| 75 | `mandisense_ai/core/agents/inference_engine_v2.py` | 1 | `PENDING` | Grep only (L31, L43–L44). |
| 76 | `mandisense_ai/core/agents/arrival_volume_agent.py` | 1 | `PENDING` | Grep only (L18, L394–L397). Its model-load path is the `UNKNOWN` in §3A. |
| 77 | `mandisense_ai/core/agents/seasonality/train_seasonality.py` | 1 | `PENDING` | Grep only (L27–L33). |
| 78 | `mandisense_ai/core/agents/seasonality/trainer.py` | 1 | `PENDING` | Grep only (L20–L21). |
| 79 | `mandisense_ai/evaluation/time_series_viz.py` | 1 | `PENDING` | Grep only (L16–L24, L107–L108). |
| 80 | `mandisense_ai/evaluation/model_comparison.py` | 1 | `PENDING` | Grep only (L21–L26, L152–L153). |
| 81 | `mandisense_ai/evaluation/statistical_validation.py` | 1 | `PENDING` | Grep only (L7–L12, L67–L68). |
| 82 | `mandisense_ai/evaluation/regime_analysis.py` | 1 | `PENDING` | Grep only (L14–L19, L110–L111). |
| 83 | `mandisense_ai/evaluation/error_distribution.py` | 1 | `PENDING` | Read the `__main__` block only; L16 is grep-backed. |
| 84 | `mandisense_ai/core/agents/external_factors_agent/processing/external_fusion.py` | 1 | `PENDING` | Read L15–L25 only (the `WEIGHTS` dict). |
| 85 | `api/main.py` | 1 | `PENDING` | Read L300–L340 and L630–L700. Performs no data acquisition (verified by grep for `read_csv`/`read_parquet`/`requests`). |
| 86 | `backend/app/main.py` | 1 | `PENDING` | Grep only (L71, L84, L90). |
| 87 | `backend/app/services/model_loader.py` | 1 | `PENDING` | Grep only (L11, L19, L26). |
| 88 | `mandisense_ai/api/routes/history.py` | 1 | `PENDING` | Grep only (L15, L32). |
| 89 | `mandisense_ai/cognition/deployment.py` | 1 | `PENDING` | Grep only (L80–L129). |
| 90 | `mandisense_ai/README.md` | 1 | `PENDING` | Grep only (L6). |
| 91 | `mandisense_ai/tests/verify_database.py` | 1 | `PENDING` | Grep only (L64–L65, L130, L144). |
| 92 | `mandisense_ai/tasks/retraining.py` | 1 | `PENDING` | Grep only (L4 — the Celery docstring). |
| 93 | `mandisense_ai/core/agents/external_factors_agent/tests/test_news_fetcher.py` | 1 | `PENDING` | Grep only (L21–L93); used to establish that a fixture exists for S4. |

---

## Coverage tally

Counted mechanically over the numbered rows of this file.

| Measure | Count |
|---|---:|
| Numbered rows in this ledger | 93 |
| Assigned `OUT-OF-SCOPE-P1` (rows 38–45, Phase 2) | 8 |
| **Phase-1 denominator** | **85** |
| `COVERED-P1` | **51** |
| `PENDING` | **34** |

Counting command:

```
python -c "import re;rows=[l for l in open('docs/reveng/PHASE_0_MAP.md',encoding='utf-8') if re.match(r'^\|\s*\d+\s*\|',l)];
from collections import Counter;print(Counter(s for l in rows for s in ('COVERED-P1','OUT-OF-SCOPE-P1','PENDING') if s in l))"
```

---

## Data-file inventory (not code — for later phases)

| Group | Count | Tracked by git? | Classification (see `PHASE_1_SOURCES.md` §3) |
|---|---:|---|---|
| `mandisense_ai/data/raw/agmarknet_*.csv` | 5 (12,445 rows) | **No** | EXTERNAL-STALE |
| `mandisense_ai/data/raw/festival_calendar.csv` | 1 (132 rows) | **No** | UNKNOWN-PROVENANCE |
| `mandisense_ai/data/raw/v1/**/*.csv` | 75 | **No** | SYNTHETIC |
| `mandisense_ai/data/raw/v2/**/*.csv` | 75 | **No** | SYNTHETIC |
| `mandisense_ai/data/raw/v3/**/*.csv` | 75 | **No** | SYNTHETIC |
| `mandisense_ai/data/processed/v4/*.csv` | 5 | **Yes — the only tracked dataset** | SYNTHETIC |
| `mandisense_ai/data/processed/{commodity}/*.csv` + `feature_config.json` | 30 | **No** | DERIVED |
| `mandisense_ai/data/processed/*.parquet` + `*.metadata.json` | 15 | **No** | DERIVED |
| `data/cache/weather/*.json` | 10 | No | EXTERNAL-REAL |
| `data/cache/news/*.json` | 17 | No | EXTERNAL-REAL |
| `mandisense_ai/data/cache/**` (shadow tree) | 9 | Yes | EXTERNAL-REAL, orphaned by CWD |
| `mandisense_ai/config/mandi_master.csv` | 1 | Yes | SYNTHETIC (hardcoded + mutated) |
| `mandisense_ai/config/mandi_metadata.csv` | 1 | Yes | UNKNOWN-PROVENANCE |
| `mandi_master_temp.csv` | 1 | No | SYNTHETIC — orphan |
| `mandisense_ai/logs/*.csv` | 10 | No | DERIVED — 9 of 10 are write-only orphans |
| `mandisense_ai/models/**` | 161 files | Partly | SYNTHETIC (v2/v3 trees) / DERIVED (arrival, seasonality trees) |
| `*.jsonl` prediction stores | 3 | Yes | DERIVED |
