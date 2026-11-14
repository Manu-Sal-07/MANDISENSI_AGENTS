# Agent council: evaluation

Generated 2026-11-14T02:05:27Z in 35.6 s. Agents: `seasonality` (11 features), `supply` (8 features), `activity` (7 features), `trend` (28 features).

Each agent is a gradient-boosted model that sees only its own family of evidence. The meta-ensemble weights them with non-negative least squares fitted inside each walk-forward fold, on the agents' out-of-sample predictions for the later quarter of that fold's training window, so a fold never chooses weights with its own test period. Everything is scored on the same rows, folds and target as the single served model. Skill is the reduction in mean absolute error against a forecast of no change.

Promotion rule: promote where the paired block-bootstrap CI of (council - single) absolute error excludes 0 on the better side and the council wins at least 3 folds.

## Results

| Horizon | n | No-change MAE | Single model | vs no change (MAE diff, 95% CI) | Linear | Equal-weight | Council (weights sum <= 1) | Council, unconstrained | Council vs single (MAE diff, 95% CI) | Folds won | Promoted |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3d | 17177 | 0.13487 | +0.6% | -0.00085 [-0.00254, +0.00096] | -2.2% | +0.1% | +0.3% | -1.5% | +0.00039 [-0.00038, +0.00104] | 1/4 | no |
| 5d | 17575 | 0.15938 | +0.7% | -0.00116 [-0.00322, +0.00089] | -2.1% | +0.1% | +0.2% | -2.4% | +0.00076 [-0.00063, +0.00209] | 1/4 | no |
| 7d | 17831 | 0.17854 | +1.0% | -0.00183 [-0.00375, +0.00007] | -2.9% | +0.4% | +0.5% | -1.3% | +0.00094 [-0.00031, +0.00218] | 1/4 | no |

Negative MAE differences mean the first method is better. The single model's interval against no change says whether its small skill is distinguishable from zero.


## Each agent alone (skill against no change)

| Horizon | seasonality | supply | activity | trend |
|---|---|---|---|---|
| 3d | -3.5% | -1.7% | -1.5% | +0.3% |
| 5d | -3.5% | -1.6% | -1.5% | +0.6% |
| 7d | -3.1% | -1.6% | -1.4% | +0.8% |

## Learned weights (mean over folds)

| Horizon | seasonality | supply | activity | trend | Sum | Sum before constraint |
|---|---|---|---|---|---|---|
| 3d | 0.20 | 0.13 | 0.14 | 0.54 | 1.00 | 2.42 |
| 5d | 0.20 | 0.13 | 0.30 | 0.36 | 1.00 | 3.32 |
| 7d | 0.19 | 0.17 | 0.25 | 0.39 | 1.00 | 2.71 |

## When the feed carries no arrival volumes

| Horizon | Single | Council |
|---|---|---|
| 3d | +0.6% | +0.3% |
| 5d | +0.7% | +0.3% |
| 7d | +1.0% | +0.6% |

## Reading

The council is **not** promoted at any horizon: its difference from the single model is not significant, or it does not win enough folds. It is kept as an explanation of what each specialist sees, and the served forecast remains the single model.

External factors (weather, news) are shown as live context and carry no forecast weight, because there is no historical panel of them to validate a weight against.

## Limits

- All agents share one learner family and one panel, so their errors are correlated and a weighted average can add little.
- Skills at these horizons are small in absolute terms; differences of a fraction of a percentage point need the intervals above to be read, not the point values.
- The weights are fitted on a quarter of each training window, which is a deliberately small sample.
- The unconstrained version was the first design and is kept in the table: it was worse because least squares inflated weak agent forecasts (weights summing to 2-3); constraining the sum was a change made after seeing that result, not before.