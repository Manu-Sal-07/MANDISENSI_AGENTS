# Supply-shock study

Generated 2026-10-29T12:36:54Z from 2021-01-01 to 2026-10-26; crops garlic, ginger, onion, potato, tomato; districts bengaluru, bengaluru_rural, bengaluru_south, chikkaballapur, kolar.

A **shock onset** is a day when arrivals sit at least 1.5 standard deviations from their trailing norm in a district, with at least 7 days since the previous onset. The **effect** is the crop's own price change over the horizon minus the average change of the other crops in the same district on the same dates, so market-wide moves cancel. Intervals are block bootstraps over weeks; the **placebo** moves every district's shocks to random other dates (400 draws, shifts of at least 90 days) and asks how often a gap this large appears by chance; **Holm** correction is applied across all 30 tests. **Detectable** is the smallest effect each test could have found (2.8 standard errors).

A result is **ROBUST** only if it survives Holm correction, the placebo, an interval that excludes zero and agreement across districts. **SUGGESTIVE** means it shows in the sample but fails one of those. Farmers are only ever shown robust results.

## Own-crop price response (30 tests: 0 robust, 5 suggestive)

| Crop | Shock | Days after | Episodes | Effect | 95% interval | Detectable | Placebo p | Holm p | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| garlic | glut | 3 | 118 | +1.5% | -3.4 to +8.5 | ±9.6% | 0.771 | 1.000 | none |
| garlic | glut | 7 | 113 | +1.0% | -4.9 to +6.9 | ±11.5% | 0.833 | 1.000 | none |
| garlic | glut | 14 | 111 | +0.7% | -10.9 to +10.9 | ±13.3% | 0.903 | 1.000 | none |
| garlic | squeeze | 3 | 75 | +6.1% | -0.2 to +21.1 | ±17.4% | 0.259 | 1.000 | none |
| garlic | squeeze | 7 | 72 | +4.3% | -0.9 to +21.3 | ±22.7% | 0.534 | 1.000 | none |
| garlic | squeeze | 14 | 71 | +8.7% | +1.6 to +25.2 | ±21.2% | 0.204 | 1.000 | suggestive |
| ginger | glut | 3 | 210 | +2.9% | -1.9 to +8.6 | ±6.1% | 0.172 | 1.000 | none |
| ginger | glut | 7 | 203 | +2.3% | -1.5 to +7.4 | ±7.0% | 0.389 | 1.000 | none |
| ginger | glut | 14 | 203 | +4.6% | -1.1 to +11.5 | ±8.6% | 0.182 | 1.000 | none |
| ginger | squeeze | 3 | 136 | -8.3% | -16.1 to -0.7 | ±9.4% | 0.002 | 0.455 | suggestive |
| ginger | squeeze | 7 | 130 | -7.1% | -14.8 to -0.3 | ±8.4% | 0.027 | 0.568 | suggestive |
| ginger | squeeze | 14 | 129 | -9.3% | -16.4 to -0.4 | ±11.8% | 0.015 | 0.810 | suggestive |
| onion | glut | 3 | 229 | -2.0% | -5.8 to +0.9 | ±5.2% | 0.344 | 1.000 | none |
| onion | glut | 7 | 211 | +0.1% | -4.0 to +3.7 | ±5.8% | 0.965 | 1.000 | none |
| onion | glut | 14 | 214 | +1.2% | -4.3 to +6.3 | ±6.3% | 0.569 | 1.000 | none |
| onion | squeeze | 3 | 141 | +3.5% | -1.5 to +7.9 | ±6.7% | 0.175 | 1.000 | none |
| onion | squeeze | 7 | 139 | +1.2% | -3.7 to +7.0 | ±7.1% | 0.683 | 1.000 | none |
| onion | squeeze | 14 | 134 | -3.7% | -9.7 to +1.7 | ±7.9% | 0.207 | 1.000 | none |
| potato | glut | 3 | 211 | -0.8% | -4.8 to +3.1 | ±5.5% | 0.698 | 1.000 | none |
| potato | glut | 7 | 209 | -1.4% | -5.9 to +1.3 | ±6.5% | 0.481 | 1.000 | none |
| potato | glut | 14 | 209 | -1.2% | -5.9 to +2.3 | ±6.0% | 0.638 | 1.000 | none |
| potato | squeeze | 3 | 109 | +0.7% | -7.8 to +4.8 | ±7.3% | 0.843 | 1.000 | none |
| potato | squeeze | 7 | 108 | -3.8% | -7.9 to -2.0 | ±6.7% | 0.175 | 1.000 | suggestive |
| potato | squeeze | 14 | 103 | -0.7% | -5.8 to +3.1 | ±8.0% | 0.805 | 1.000 | none |
| tomato | glut | 3 | 163 | +0.3% | -5.8 to +5.2 | ±8.2% | 0.913 | 1.000 | none |
| tomato | glut | 7 | 158 | +0.6% | -5.7 to +5.9 | ±10.1% | 0.818 | 1.000 | none |
| tomato | glut | 14 | 161 | -0.4% | -10.1 to +8.3 | ±11.9% | 0.910 | 1.000 | none |
| tomato | squeeze | 3 | 327 | -1.2% | -6.2 to +3.8 | ±5.7% | 0.469 | 1.000 | none |
| tomato | squeeze | 7 | 324 | -3.4% | -10.0 to +2.5 | ±6.8% | 0.050 | 1.000 | none |
| tomato | squeeze | 14 | 323 | -1.1% | -10.2 to +7.0 | ±7.9% | 0.601 | 1.000 | none |

## Cross-commodity links (40 tested)

| When | Then | Episodes | Effect | 95% interval | Detectable | Placebo p | Published as |
|---|---|---|---|---|---|---|---|
| onion squeeze | ginger price | 109 | +11.1% | +4.1 to +17.2 | ±9.3% | 0.066 | not published |
| garlic glut | ginger price | 100 | +9.5% | +5.2 to +16.8 | ±8.3% | 0.100 | not published |
| potato squeeze | garlic price | 67 | -6.7% | -16.9 to +3.6 | ±14.6% | 0.371 | not published |
| potato squeeze | ginger price | 92 | +6.4% | -6.7 to +14.2 | ±14.9% | 0.256 | not published |
| tomato glut | ginger price | 125 | +6.0% | +1.4 to +13.3 | ±8.5% | 0.222 | not published |
| onion squeeze | tomato price | 140 | +5.9% | -1.4 to +14.3 | ±11.2% | 0.196 | not published |
| ginger squeeze | garlic price | 73 | -5.3% | -9.2 to +1.9 | ±7.9% | 0.399 | not published |
| potato squeeze | tomato price | 108 | +5.0% | -2.4 to +15.4 | ±12.7% | 0.399 | not published |
| garlic glut | tomato price | 117 | +4.1% | -3.4 to +11.0 | ±10.3% | 0.403 | not published |
| tomato glut | onion price | 92 | +3.9% | +0.7 to +9.6 | ±6.4% | 0.395 | not published |
| potato glut | ginger price | 176 | +3.8% | +0.1 to +10.3 | ±7.3% | 0.343 | not published |
| potato squeeze | onion price | 101 | +3.3% | +1.0 to +8.6 | ±5.5% | 0.449 | not published |
| onion squeeze | potato price | 128 | +3.2% | -1.5 to +6.6 | ±5.8% | 0.339 | not published |
| ginger squeeze | tomato price | 131 | +3.1% | -2.1 to +8.0 | ±7.2% | 0.561 | not published |
| potato glut | garlic price | 141 | +3.0% | -2.3 to +12.1 | ±10.3% | 0.567 | not published |
| onion glut | tomato price | 225 | +3.0% | -4.1 to +11.7 | ±11.2% | 0.405 | not published |
| tomato glut | garlic price | 47 | +2.9% | -2.5 to +7.0 | ±6.8% | 0.701 | not published |
| potato glut | tomato price | 210 | +2.8% | -5.0 to +10.2 | ±10.9% | 0.403 | not published |
| garlic glut | potato price | 114 | +2.8% | -1.8 to +7.3 | ±6.5% | 0.301 | not published |
| ginger glut | tomato price | 208 | +2.6% | -4.5 to +10.9 | ±11.0% | 0.423 | not published |
| ginger glut | onion price | 121 | -2.4% | -6.8 to +2.2 | ±6.4% | 0.521 | not published |
| garlic squeeze | tomato price | 74 | +2.4% | -13.3 to +15.9 | ±20.9% | 0.657 | not published |
| onion glut | ginger price | 161 | +2.3% | -1.5 to +7.9 | ±6.7% | 0.569 | not published |
| tomato squeeze | ginger price | 252 | +2.1% | -0.4 to +6.5 | ±4.9% | 0.527 | not published |
| onion glut | garlic price | 135 | -1.6% | -5.4 to +5.3 | ±7.6% | 0.741 | not published |
| ginger glut | garlic price | 83 | -1.5% | -5.1 to +6.7 | ±8.4% | 0.834 | not published |
| ginger glut | potato price | 138 | -1.5% | -4.5 to +1.4 | ±4.2% | 0.573 | not published |
| onion squeeze | garlic price | 92 | +1.5% | -7.5 to +16.3 | ±17.0% | 0.834 | not published |
| tomato squeeze | garlic price | 120 | +1.3% | -7.8 to +11.8 | ±14.0% | 0.856 | not published |
| potato glut | onion price | 192 | +1.2% | -2.2 to +5.0 | ±5.2% | 0.733 | not published |
| tomato glut | potato price | 80 | +1.1% | -6.4 to +7.6 | ±9.9% | 0.798 | not published |
| garlic squeeze | onion price | 73 | +1.1% | -5.3 to +6.5 | ±8.5% | 0.796 | not published |
| ginger squeeze | potato price | 101 | +0.9% | -2.4 to +5.4 | ±5.6% | 0.756 | not published |
| onion glut | potato price | 193 | -0.9% | -4.4 to +1.8 | ±4.5% | 0.707 | not published |
| tomato squeeze | onion price | 194 | -0.8% | -5.5 to +5.1 | ±7.5% | 0.804 | not published |
| ginger squeeze | onion price | 90 | +0.7% | -4.5 to +5.9 | ±7.4% | 0.870 | not published |
| garlic squeeze | potato price | 73 | +0.2% | -3.1 to +3.0 | ±4.3% | 0.920 | not published |
| garlic squeeze | ginger price | 65 | -0.2% | -8.6 to +9.4 | ±12.9% | 0.932 | not published |
| garlic glut | onion price | 114 | -0.2% | -4.6 to +5.6 | ±7.3% | 0.946 | not published |
| tomato squeeze | potato price | 216 | +0.0% | -2.6 to +2.5 | ±3.6% | 0.996 | not published |

## Reading

No own-crop price response is robust, so the application makes no claim that a glut or squeeze of arrivals will move a price. Where results are only suggestive they are shown to traders as leads to check, never as signals, and never to farmers. The farmer app reports only what is observed: arrivals against normal and the price gap to neighbouring districts.

## Limits

- Five crops in five districts over under six years give a few hundred episodes at best; the *detectable* column says how large an effect would have to be to be seen.
- Thirty-plus tests invite chance findings; the Holm column is the guard, and the suggestive rows should be read with it.
- Reported modal prices change in steps, so short-horizon price changes are lumpy and many are exactly zero.