# Supply-shock study

Generated 2026-11-13T13:37:20Z from 2021-01-01 to 2026-11-11; crops garlic, ginger, onion, potato, tomato; districts bengaluru, bengaluru_rural, bengaluru_south, chikkaballapur, kolar.

A **shock onset** is a day when arrivals sit at least 1.5 standard deviations from their trailing norm in a district, with at least 7 days since the previous onset. The **effect** is the crop's own price change over the horizon minus the average change of the other crops in the same district on the same dates, so market-wide moves cancel. Intervals are block bootstraps over weeks; the **placebo** moves every district's shocks to random other dates (400 draws, shifts of at least 90 days) and asks how often a gap this large appears by chance; **Holm** correction is applied across all 30 tests. **Detectable** is the smallest effect each test could have found (2.8 standard errors).

A result is **ROBUST** only if it survives Holm correction, the placebo, an interval that excludes zero and agreement across districts. **SUGGESTIVE** means it shows in the sample but fails one of those. Farmers are only ever shown robust results.

## Own-crop price response (30 tests: 0 robust, 5 suggestive)

| Crop | Shock | Days after | Episodes | Effect | 95% interval | Detectable | Placebo p | Holm p | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| garlic | glut | 3 | 119 | +1.5% | -3.5 to +8.3 | ±9.6% | 0.728 | 1.000 | none |
| garlic | glut | 7 | 113 | +1.0% | -4.9 to +6.9 | ±11.5% | 0.835 | 1.000 | none |
| garlic | glut | 14 | 112 | +0.8% | -10.3 to +11.2 | ±13.2% | 0.883 | 1.000 | none |
| garlic | squeeze | 3 | 76 | +6.1% | -0.1 to +21.1 | ±17.1% | 0.224 | 1.000 | none |
| garlic | squeeze | 7 | 73 | +4.4% | -1.3 to +21.6 | ±22.4% | 0.484 | 1.000 | none |
| garlic | squeeze | 14 | 73 | +8.7% | +1.4 to +24.7 | ±20.6% | 0.209 | 1.000 | suggestive |
| ginger | glut | 3 | 213 | +3.3% | -1.7 to +8.7 | ±6.1% | 0.107 | 1.000 | none |
| ginger | glut | 7 | 206 | +2.4% | -1.4 to +7.6 | ±7.1% | 0.322 | 1.000 | none |
| ginger | glut | 14 | 207 | +5.2% | -1.1 to +11.3 | ±8.4% | 0.115 | 1.000 | none |
| ginger | squeeze | 3 | 137 | -8.5% | -16.3 to -0.8 | ±9.4% | 0.002 | 0.372 | suggestive |
| ginger | squeeze | 7 | 132 | -6.8% | -14.1 to -0.3 | ±8.3% | 0.035 | 0.677 | suggestive |
| ginger | squeeze | 14 | 132 | -9.0% | -16.5 to -1.3 | ±11.6% | 0.015 | 0.892 | suggestive |
| onion | glut | 3 | 231 | -2.1% | -5.8 to +0.9 | ±5.1% | 0.274 | 1.000 | none |
| onion | glut | 7 | 214 | +0.1% | -3.8 to +3.8 | ±5.7% | 0.943 | 1.000 | none |
| onion | glut | 14 | 217 | +1.2% | -4.2 to +6.5 | ±6.2% | 0.591 | 1.000 | none |
| onion | squeeze | 3 | 143 | +3.7% | -1.2 to +7.6 | ±6.7% | 0.142 | 1.000 | none |
| onion | squeeze | 7 | 140 | +1.3% | -3.9 to +6.9 | ±7.0% | 0.584 | 1.000 | none |
| onion | squeeze | 14 | 135 | -3.6% | -9.2 to +1.6 | ±7.8% | 0.200 | 1.000 | none |
| potato | glut | 3 | 213 | -0.7% | -4.9 to +3.2 | ±5.4% | 0.711 | 1.000 | none |
| potato | glut | 7 | 211 | -1.6% | -5.7 to +1.5 | ±6.4% | 0.401 | 1.000 | none |
| potato | glut | 14 | 210 | -1.1% | -6.0 to +2.3 | ±6.0% | 0.621 | 1.000 | none |
| potato | squeeze | 3 | 112 | +0.6% | -7.1 to +5.1 | ±7.1% | 0.863 | 1.000 | none |
| potato | squeeze | 7 | 111 | -4.7% | -7.8 to -1.9 | ±6.2% | 0.085 | 1.000 | suggestive |
| potato | squeeze | 14 | 105 | -0.9% | -5.9 to +3.1 | ±7.9% | 0.800 | 1.000 | none |
| tomato | glut | 3 | 163 | +0.3% | -5.8 to +5.2 | ±8.2% | 0.903 | 1.000 | none |
| tomato | glut | 7 | 159 | +0.7% | -5.6 to +6.1 | ±10.0% | 0.800 | 1.000 | none |
| tomato | glut | 14 | 162 | -0.5% | -9.4 to +8.1 | ±11.9% | 0.898 | 1.000 | none |
| tomato | squeeze | 3 | 330 | -1.5% | -6.0 to +3.6 | ±5.6% | 0.369 | 1.000 | none |
| tomato | squeeze | 7 | 328 | -3.8% | -9.7 to +2.0 | ±6.8% | 0.032 | 1.000 | none |
| tomato | squeeze | 14 | 326 | -1.1% | -10.0 to +7.0 | ±7.8% | 0.621 | 1.000 | none |

## Cross-commodity links (40 tested)

| When | Then | Episodes | Effect | 95% interval | Detectable | Placebo p | Published as |
|---|---|---|---|---|---|---|---|
| onion squeeze | ginger price | 111 | +11.2% | +4.6 to +18.0 | ±9.6% | 0.084 | not published |
| garlic glut | ginger price | 101 | +9.2% | +4.7 to +16.8 | ±8.6% | 0.138 | not published |
| potato squeeze | garlic price | 69 | -6.4% | -16.8 to +4.3 | ±15.1% | 0.399 | not published |
| tomato glut | ginger price | 126 | +6.2% | +1.0 to +12.8 | ±8.4% | 0.182 | not published |
| potato squeeze | ginger price | 95 | +6.1% | -5.9 to +14.5 | ±14.5% | 0.239 | not published |
| onion squeeze | tomato price | 141 | +5.9% | -1.5 to +14.6 | ±11.5% | 0.194 | not published |
| potato squeeze | tomato price | 110 | +5.4% | -2.5 to +14.7 | ±12.3% | 0.311 | not published |
| ginger squeeze | garlic price | 74 | -5.1% | -9.0 to +2.2 | ±8.0% | 0.445 | not published |
| garlic glut | tomato price | 118 | +4.0% | -3.1 to +10.9 | ±10.0% | 0.387 | not published |
| potato glut | ginger price | 177 | +3.9% | -0.4 to +10.2 | ±7.5% | 0.365 | not published |
| tomato glut | onion price | 93 | +3.6% | +0.9 to +9.3 | ±6.0% | 0.437 | not published |
| potato squeeze | onion price | 103 | +3.1% | +0.9 to +8.6 | ±5.5% | 0.451 | not published |
| garlic glut | potato price | 115 | +3.1% | -1.6 to +7.1 | ±6.2% | 0.303 | not published |
| onion squeeze | potato price | 129 | +3.1% | -1.5 to +6.6 | ±5.8% | 0.339 | not published |
| tomato glut | garlic price | 48 | +3.0% | -2.6 to +7.1 | ±6.9% | 0.649 | not published |
| potato glut | garlic price | 141 | +3.0% | -2.3 to +12.1 | ±10.3% | 0.565 | not published |
| ginger squeeze | tomato price | 134 | +3.0% | -1.8 to +7.8 | ±6.9% | 0.615 | not published |
| potato glut | tomato price | 211 | +2.7% | -4.8 to +10.2 | ±10.7% | 0.375 | not published |
| tomato squeeze | ginger price | 255 | +2.7% | -0.3 to +6.5 | ±4.9% | 0.421 | not published |
| onion glut | tomato price | 228 | +2.6% | -4.2 to +11.8 | ±11.4% | 0.443 | not published |
| ginger glut | onion price | 124 | -2.5% | -6.5 to +2.4 | ±6.4% | 0.489 | not published |
| ginger glut | tomato price | 212 | +2.5% | -4.7 to +11.2 | ±11.4% | 0.493 | not published |
| onion glut | ginger price | 164 | +2.4% | -2.4 to +7.7 | ±7.2% | 0.555 | not published |
| garlic squeeze | tomato price | 76 | +2.4% | -13.6 to +17.2 | ±22.1% | 0.657 | not published |
| tomato glut | potato price | 81 | +1.6% | -6.0 to +7.5 | ±9.7% | 0.745 | not published |
| ginger squeeze | potato price | 104 | +1.5% | -2.3 to +5.3 | ±5.5% | 0.583 | not published |
| onion glut | garlic price | 137 | -1.5% | -5.8 to +5.1 | ±7.8% | 0.792 | not published |
| onion squeeze | garlic price | 93 | +1.4% | -7.4 to +16.3 | ±16.9% | 0.864 | not published |
| garlic squeeze | ginger price | 67 | -1.4% | -8.9 to +9.1 | ±12.9% | 0.733 | not published |
| ginger glut | potato price | 141 | -1.3% | -4.4 to +1.5 | ±4.2% | 0.595 | not published |
| ginger glut | garlic price | 85 | -1.3% | -5.5 to +6.1 | ±8.3% | 0.848 | not published |
| tomato squeeze | garlic price | 121 | +1.3% | -7.7 to +12.2 | ±14.2% | 0.858 | not published |
| potato glut | onion price | 193 | +1.1% | -2.2 to +5.1 | ±5.2% | 0.743 | not published |
| garlic squeeze | onion price | 75 | +0.9% | -5.2 to +6.6 | ±8.4% | 0.824 | not published |
| garlic squeeze | potato price | 75 | +0.8% | -2.9 to +2.9 | ±4.2% | 0.780 | not published |
| tomato squeeze | onion price | 196 | -0.6% | -5.5 to +4.9 | ±7.4% | 0.858 | not published |
| onion glut | potato price | 196 | -0.6% | -4.2 to +2.0 | ±4.4% | 0.794 | not published |
| ginger squeeze | onion price | 93 | +0.4% | -4.3 to +6.5 | ±7.7% | 0.882 | not published |
| garlic glut | onion price | 115 | -0.3% | -4.7 to +5.6 | ±7.4% | 0.920 | not published |
| tomato squeeze | potato price | 218 | -0.2% | -2.6 to +2.4 | ±3.6% | 0.932 | not published |

## Reading

No own-crop price response is robust, so the application makes no claim that a glut or squeeze of arrivals will move a price. Where results are only suggestive they are shown to traders as leads to check, never as signals, and never to farmers. The farmer app reports only what is observed: arrivals against normal and the price gap to neighbouring districts.

## Limits

- Five crops in five districts over under six years give a few hundred episodes at best; the *detectable* column says how large an effect would have to be to be seen.
- Thirty-plus tests invite chance findings; the Holm column is the guard, and the suggestive rows should be read with it.
- Reported modal prices change in steps, so short-horizon price changes are lumpy and many are exactly zero.