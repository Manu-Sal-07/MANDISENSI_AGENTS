# Contributing

How work is done in this repository, so that history, tests and documentation stay trustworthy.

## Set up and check your change

```bash
python -m venv ms_env && ms_env\Scripts\activate         # source ms_env/bin/activate on Linux/macOS
pip install -r requirements.lock
cd frontend && npm ci && cd ..

python -m pytest mandisense_ai -q                        # application tests (no network, no API key)
cd frontend && npm test && npx tsc --noEmit && npx eslint . --quiet && cd ..
python scripts/smoke_ui.py                               # with both servers running
```

Continuous integration (`.github/workflows/ci.yml`) runs the backend tests, the front-end type-check, unit tests, lint and production build on
every push and pull request. A change that turns any of them red is not finished.

## Conventions

* **Branches:** `feature/<short-name>` from `main`; open a pull request; at least one teammate reviews before merging. Do not commit to `main` directly.
* **Commits:** one logical change each, with a subject that says what changed and why it matters (not "fix" or "update"). Commit under **your own** git identity
  (`git config user.name`, `git config user.email`): authorship is how contribution is evidenced. See [`CONTRIBUTIONS.md`](CONTRIBUTIONS.md).
* **Tests travel with code.** A new module gets tests in `mandisense_ai/tests/` (or `frontend/src/__tests__/`); a bug fix gets a test that fails without it.
  Tests must not need a network connection or an API key; `tests/conftest.py` switches the language models off.
* **Evidence travels with claims.** Anything the application states about accuracy, savings or a relationship between prices must come from a held-out test and say so. If a
  result does not survive its test, report it as a negative result (see `docs/AGENT_COUNCIL.md`, `docs/SHOCK_STUDY.md`) rather than dropping or softening it.
* **No synthetic data.** Do not generate prices, arrivals or outcomes to fill a gap. An absent value is absent; the models are told it is absent.
* **Secrets:** keys live in `.env` (git-ignored). Never paste a key into code, a test, a commit message or a chat. Rotate any key that has been shared.
* **Generated files:** artefacts under `mandisense_ai/models/`, `mandisense_ai/data/` and `research/results/` are produced by the pipeline, not edited by hand. Change the
  code, re-run the stage (`python scripts/pipeline.py --only <stage>`), and commit the result with the change that caused it.
* **Style:** Python follows the surrounding code (type hints, docstrings that explain *why*); TypeScript passes `tsc` and ESLint with no errors. Prefer deleting dead code to
  commenting it out; history keeps it.

## Adding things

| To add… | Do |
|---|---|
| A pipeline stage | Add a `Stage` to `scripts/pipeline.py` (command, inputs, outputs, purpose) and a script that reads only its declared inputs. |
| A trader tool | Add a component, a page under `frontend/src/app/trader-tools/<slug>/`, and an entry in `frontend/src/lib/traderTools.ts`; the registry test fails if they disagree. |
| A farmer-facing string | Add English, Kannada and Hindi together to the feature's copy table, then run `python scripts/language_review.py` so it enters the review checklist. |
| An API endpoint | Add it to a router in `api/`, register it in `api/main.py`, and add it to the endpoint list in `scripts/smoke_ui.py`. |
| A model or method | Record the alternatives and the evidence in `docs/TOOL_CHOICES.md`, and evaluate it against the current one on the same rows and folds before it is served. |

## Review checklist

- [ ] Tests added or updated, and green locally.
- [ ] No number, name or date in user-facing text is typed by hand; it comes from data.
- [ ] Anything the user might misread as a promise says what it is (an estimate, a past-test result, an interval).
- [ ] Absence of data is surfaced as `UNAVAILABLE` with a reason, not as a zero.
- [ ] Documentation that described the old behaviour is updated.
- [ ] `git status` shows nothing unintended (data exports, `.env`, caches).

## Releasing a rebuilt dataset

1. Put the new Agmarknet exports in `mandisense_ai/data/farmer/source/` (and `datasets/year_data/` for the research package).
2. `python scripts/pipeline.py` and read `logs/pipeline_report.json`; every stage should be `OK`.
3. `python scripts/smoke_ui.py` against the running servers.
4. Commit the regenerated artefacts with a message that says which export they came from.
