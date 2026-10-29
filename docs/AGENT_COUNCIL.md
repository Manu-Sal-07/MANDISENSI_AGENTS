# Agent council: evaluation

Generated 2026-10-29T12:02:35Z in 51.3 s. Agents: `seasonality` (11 features), `supply` (8 features), `activity` (7 features), `trend` (28 features).

Each agent is a gradient-boosted model that sees only its own family of evidence. The meta-ensemble weights them with non-negative least squares fitted inside each walk-forward fold, on the agents' out-of-sample predictions for the later quarter of that fold's training window, so a fold never chooses weights with its own test period. Everything is scored on the same rows, folds and target as the single served model. Skill is the reduction in mean absolute error against a forecast of no change.

Promotion rule: promote where the paired block-bootstrap CI of (council - single) absolute error excludes 0 on the better side and the council wins at least 3 folds.

## Results

| Horizon | n | No-change MAE | Single model | Equal-weight | Council (weights sum <= 1) | Council, unconstrained weights | Council vs single (MAE diff, 95% CI) | Folds won | Promoted |
|---|---|---|---|---|---|---|---|---|---|
| 3d | 16983 | 0.13454 | +0.6% | -0.0% | +0.2% | -1.8% | +0.00053 [-0.00022, +0.00112] | 1/4 | no |
| 5d | 17369 | 0.15943 | +0.7% | +0.1% | +0.3% | -2.1% | +0.00067 [-0.00050, +0.00162] | 1/4 | no |
| 7d | 17633 | 0.17944 | +0.8% | +0.3% | +0.4% | -1.6% | +0.00063 [-0.00061, +0.00151] | 0/4 | no |

## Each agent alone (skill against no change)

| Horizon | seasonality | supply | activity | trend |
|---|---|---|---|---|
| 3d | -3.9% | -2.1% | -1.5% | +0.2% |
| 5d | -3.6% | -1.6% | -1.6% | +0.5% |
| 7d | -3.1% | -1.7% | -1.4% | +0.7% |

## Learned weights (mean over folds)

| Horizon | seasonality | supply | activity | trend | Sum | Sum before constraint |
|---|---|---|---|---|---|---|
| 3d | 0.18 | 0.12 | 0.11 | 0.59 | 1.00 | 2.38 |
| 5d | 0.20 | 0.07 | 0.33 | 0.39 | 1.00 | 3.12 |
| 7d | 0.18 | 0.13 | 0.26 | 0.42 | 1.00 | 2.65 |

## When the feed carries no arrival volumes

| Horizon | Single | Council |
|---|---|---|
| 3d | +0.6% | +0.1% |
| 5d | +0.7% | +0.3% |
| 7d | +0.8% | +0.6% |

## Reading

The council is **not** promoted at any horizon: its difference from the single model is not significant, or it does not win enough folds. It is kept as an explanation of what each specialist sees, and the served forecast remains the single model.

External factors (weather, news) are shown as live context and carry no forecast weight, because there is no historical panel of them to validate a weight against.

## Limits

- All agents share one learner family and one panel, so their errors are correlated and a weighted average can add little.
- Skills at these horizons are small in absolute terms; differences of a fraction of a percentage point need the intervals above to be read, not the point values.
- The weights are fitted on a quarter of each training window, which is a deliberately small sample.
- The unconstrained version was the first design and is kept in the table: it was worse because least squares inflated weak agent forecasts (weights summing to 2-3); constraining the sum was a change made after seeing that result, not before.