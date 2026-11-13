# Agent council: evaluation

Generated 2026-11-13T13:38:02Z in 39.6 s. Agents: `seasonality` (11 features), `supply` (8 features), `activity` (7 features), `trend` (28 features).

Each agent is a gradient-boosted model that sees only its own family of evidence. The meta-ensemble weights them with non-negative least squares fitted inside each walk-forward fold, on the agents' out-of-sample predictions for the later quarter of that fold's training window, so a fold never chooses weights with its own test period. Everything is scored on the same rows, folds and target as the single served model. Skill is the reduction in mean absolute error against a forecast of no change.

Promotion rule: promote where the paired block-bootstrap CI of (council - single) absolute error excludes 0 on the better side and the council wins at least 3 folds.

## Results

| Horizon | n | No-change MAE | Single model | vs no change (MAE diff, 95% CI) | Linear | Equal-weight | Council (weights sum <= 1) | Council, unconstrained | Council vs single (MAE diff, 95% CI) | Folds won | Promoted |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3d | 17046 | 0.13435 | +0.5% | -0.00066 [-0.00232, +0.00129] | -2.3% | +0.1% | +0.2% | -1.7% | +0.00036 [-0.00040, +0.00104] | 1/4 | no |
| 5d | 17438 | 0.15935 | +0.8% | -0.00129 [-0.00307, +0.00054] | -2.5% | +0.1% | +0.3% | -1.9% | +0.00075 [-0.00037, +0.00181] | 1/4 | no |
| 7d | 17692 | 0.17896 | +1.0% | -0.00171 [-0.00351, +0.00022] | -3.1% | +0.4% | +0.5% | -1.1% | +0.00086 [-0.00039, +0.00186] | 2/4 | no |

Negative MAE differences mean the first method is better. The single model's interval against no change says whether its small skill is distinguishable from zero.


## Each agent alone (skill against no change)

| Horizon | seasonality | supply | activity | trend |
|---|---|---|---|---|
| 3d | -3.6% | -1.7% | -1.5% | +0.4% |
| 5d | -3.4% | -1.6% | -1.5% | +0.7% |
| 7d | -3.0% | -1.5% | -1.3% | +0.7% |

## Learned weights (mean over folds)

| Horizon | seasonality | supply | activity | trend | Sum | Sum before constraint |
|---|---|---|---|---|---|---|
| 3d | 0.21 | 0.15 | 0.08 | 0.56 | 1.00 | 2.49 |
| 5d | 0.22 | 0.11 | 0.26 | 0.41 | 1.00 | 3.02 |
| 7d | 0.18 | 0.13 | 0.27 | 0.41 | 1.00 | 2.57 |

## When the feed carries no arrival volumes

| Horizon | Single | Council |
|---|---|---|
| 3d | +0.5% | +0.3% |
| 5d | +0.8% | +0.4% |
| 7d | +1.0% | +0.5% |

## Reading

The council is **not** promoted at any horizon: its difference from the single model is not significant, or it does not win enough folds. It is kept as an explanation of what each specialist sees, and the served forecast remains the single model.

External factors (weather, news) are shown as live context and carry no forecast weight, because there is no historical panel of them to validate a weight against.

## Limits

- All agents share one learner family and one panel, so their errors are correlated and a weighted average can add little.
- Skills at these horizons are small in absolute terms; differences of a fraction of a percentage point need the intervals above to be read, not the point values.
- The weights are fitted on a quarter of each training window, which is a deliberately small sample.
- The unconstrained version was the first design and is kept in the table: it was worse because least squares inflated weak agent forecasts (weights summing to 2-3); constraining the sum was a change made after seeing that result, not before.