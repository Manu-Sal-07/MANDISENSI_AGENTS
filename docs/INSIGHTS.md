# Insights on the market-choice engine

Five features that explain, stress-test and audit the advice. All are computed from the served engine and the ingested panel
(`mandisense_ai/market_choice/insights.py`); none fits a model at request time.

| Feature | Endpoint | Where it appears |
|---|---|---|
| **Why this mandi?** per-quintal arithmetic: price, fee, spoilage, transport, handling, for the advice and the nearest / highest-yesterday / farm-gate alternatives | `GET /v1/market-choice/breakdown/{crop}` | Farmer: Best Place & Day to Sell |
| **What if my costs differ?** re-prices every action under the farmer's transport, spoilage, fee, handling and longest wait, and reports the exact cost at which the advice changes | `GET /v1/market-choice/simulate/{crop}` | Farmer: Best Place & Day to Sell |
| **Has this advice worked?** the advice replayed day by day on days it was not fitted on: wins, ties and losses against the nearest mandi and yesterday's highest price, share of days the minimum held, running gain | `GET /v1/market-choice/track-record/{crop}` | Farmer: Best Place & Day to Sell |
| **Silence Tax** expected rupees per quintal lost on a trip because a mandi reports no price, per mandi and weekday | `GET /v1/market-choice/reporting-value/{crop}` | Trader tool `/trader-tools/reporting-value` |
| **Crowd Simulator** what happens to a yard's price when many farmers follow the same advice, and a coordinated split | `GET /v1/market-choice/crowd/{crop}` | Trader tool `/trader-tools/crowd-simulator` |

## How each is computed, and what it does not claim

**Breakdown.** `price - fee - spoilage - transport - handling = net`, exactly the served net revenue (the code asserts it). The
price is the model's expected price, which already includes the chance a mandi reports nothing, because the model is trained on
what a farmer actually received.

**What-if.** Prices and the chance a mandi reports come from the served model and do not depend on the farmer's costs, so the
re-pricing is exact for the stated costs. The guaranteed floor keeps the error scale calibrated at the default costs, so it is
indicative when costs differ a lot (the response and the UI say so). A silent-price discount cannot be changed because it is
baked into the trained model.

**Track record.** `scripts/build_track_record.py` replays the walk-forward back-test with day-level output. Only the second half
of the scored period is listed, because the floor multiplier is fitted on the first half. The script checks that its headline
numbers reproduce `meta.json` and refuses to write otherwise. The floor is reported as it came out: 84% (tomato), 89% (onion),
92% (potato), 86% (ginger) of days against the 90% aimed for. Most days the advice ties with "highest price yesterday" because it
chooses the same action; the scoreboard shows ties explicitly.

**Silence tax.** `P(silent on an open day) x (mean price when it reports - silent fraction x mean day price)`, from the last 365 days of
the panel. A weekday on which a mandi is silent at least 90% of the time is treated as a known closed day and excluded: farmers
know it. A silent day may be a closed mandi or a missed upload. A tax of Rs 0 does not mean reliable: it means the mandi's usual
price is below the fallback, so silence costs no money on price, but the trip is still wasted; the table shows the surprise-silence
share next to it.

**Crowd.** A yard's price falls when it receives more than its median daily arrivals `A`: `P(x) = P (1 + x / A)^(-b)`. The default
flexibility `b = 0.115` is the within-mandi, within-month association of log price with log arrivals in the tomato panel (standard
error 0.023). It is an association, not a causal estimate, so it is a scenario with a slider, and at `b = 0` every policy is equal.
Three policies are compared with the single farmer's advice: everyone takes the best action, everyone goes to the nearest yard, and
a greedy-marginal-revenue split that maximises the group's total revenue. Example (tomato, Kolar farmers, 10 quintals each): for
200 farmers the best yard's price falls 32.5% and net revenue per quintal falls from Rs 1,824 to Rs 1,194; the coordinated split
earns Rs 1,436.

## Reproduce

```
python scripts/build_track_record.py        # or: python scripts/pipeline.py --only track_record
pytest mandisense_ai/tests/test_market_insights.py
```
