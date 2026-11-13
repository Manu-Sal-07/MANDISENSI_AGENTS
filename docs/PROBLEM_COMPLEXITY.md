# Why this problem is hard

"Predict the price of tomatoes" is a tutorial. The problem here is to tell a small farmer **where and on which day to sell a load, and
the least they can count on**, from public data in which most mandis are silent most days. Six difficulties, each with the requirements that
compete, the decision taken, and the measurement behind it. Figures are held-out (nested walk-forward) from [RESULTS](RESULTS.md).

| # | Difficulty | Competing requirements | What we decided | Evidence |
|---|---|---|---|---|
| 1 | **Silence is information.** 62% of mandi-days have no report; a farmer who drives to a silent mandi has wasted a trip. | Use all the data vs not inventing prices; a clean panel vs a truthful one | Never impute. Train on what the farmer *actually received*, including the discounted fallback after a wasted trip. | Training on realised outcomes cuts regret by ₹140 / 157 / 87 / 149 per quintal (tomato / onion / potato / ginger), Holm p ≤ 0.0016 on all four. |
| 2 | **Forecast skill is almost nil.** Mandi prices barely beat "no change". | Honest forecasts vs a product that must still advise | Use forecasts for direction and risk bands only; put the value in the decision layer. | 5-day skill +0.7% against no change; the interval against it, [-0.0027, +0.0010] in log-return MAE, includes zero. |
| 3 | **Published methods look better than they are.** Decompose-then-forecast hybrids (STL, VMD) are widely reported. | Matching the literature vs being right | Re-ran them without look-ahead; report the gap. | +27 to +62% skill under the published protocol, -15 to -1% once the decomposition cannot see the future. |
| 4 | **A floor a farmer can rely on.** "At least ₹X" is only useful if it holds at the stated rate. | Tight floors vs honest floors; simple vs calibrated | An adaptive conformal floor, validated out of sample. | Research (tomato, research predictor): stated 5 / 10 / 20% risk was violated 4.6 / 10.6 / 23.3% of the time. Served engine at 10%: 9.6 to 12.3% by crop. A naive Gaussian floor aimed at 10% was violated 27.4% (tomato), 34.5% (onion), 25.8% (potato), 11.9% (ginger). |
| 5 | **Two audiences, low connectivity and literacy.** Farmers want one line in Kannada; traders want evidence tiers and limits. | Simplicity vs rigour; free vs accurate language | One engine, two surfaces; plain-language reasons written by code in three languages; a language model may only paraphrase, behind an independent judge, so figures cannot change. | Recommendation and every figure identical with and without the model in 24 of 24 cases; judge caught 9 of 9 corrupted rewrites. |
| 6 | **Claims that do not survive testing.** | A longer feature list vs a defensible one | Test, report, and withdraw: the supply-shock radar claims no price response, and the specialist-agent council is shown but not promoted. | Shock study: 30 own-crop tests, 0 robust, 5 suggestive. Council not significantly better than the single served model. |

## What an off-the-shelf approach would have got wrong

* A standard forecaster trained on observed prices treats a silent mandi as missing and recommends it anyway, and loses ₹87 to ₹157 per
  quintal against the same model trained on outcomes (difficulty 1).
* A Gaussian "confidence band" on a standard model is wrong up to three and a half times as often as it claims (27.4% tomato, 34.5% onion, 25.8% potato against a 10% target; ginger 11.9%; difficulty 4).
* Following the hybrid-forecasting literature would have shipped a model whose skill disappears once evaluated honestly (difficulty 3).

## Where the competing requirements were resolved, not just acknowledged

* **Accuracy against interpretability:** LightGBM trained on realised outcomes, not a neural network. A structured SPO+ network on the
  same labels was statistically indistinguishable (+₹14/q, CI -8 to +39), so the simpler, faster and more explainable model was kept.
* **Offline cost against reach:** no paid service is required for any answer; the language model is optional and falls back to rules.
* **Evidence against ambition:** the production advice beats "highest price yesterday" in tomato (+₹170/q, CI +104 to +255), onion
  (+₹60/q) and ginger (+₹202/q), is not distinguishable in potato (+₹15/q, CI -38 to +60), and is refused for garlic.

Say the limits first: forecast skill is small, the floor describes past tests of a method and is not a guarantee on one sale, and the data
is five crops in one region, with advice served on four (garlic is refused).
