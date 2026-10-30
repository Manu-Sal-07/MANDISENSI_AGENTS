"""Deep-dive guide content, part 2: slides 11-22 (demo, tools, setup, results, validation, features)."""

SLIDES = []

SLIDES.append(dict(
    n=11, title="Live demonstration (1/2): farmer tool",
    one="Six steps that show the advice, its arithmetic, its sensitivity, its track record and the language switch.",
    plain=[
        "The demo follows one farmer: a tomato grower in Kolar with 10 quintals and a small truck (tempo). We ask the system where and when to sell, then ask it to prove itself in four ways.",
    ],
    deeper=[
        "**A1. Best Place and Day to Sell.** Result: Ramanagara, Wednesday 28 October, 103 km away. Expected net Rs 1,824 per quintal. The **floor** is Rs 1,316: the amount the farmer can count on about 9 days out of 10. It is Rs 592 above what selling at the nearest mandi (Kolar) would net. Note the farmer is told to go to a mandi 103 km away rather than the nearest one, and the next steps explain why that is worth it.",
        "**A2. Why this mandi.** 2,081 - 83 - 60 - 94 - 20 = 1,824. Read left to right: expected price Rs 2,081; market fee Rs 83 (4 percent); spoilage Rs 60 (one day of waiting at 3 percent on what is left after the fee); transport Rs 94 for 103 km in a tempo; handling Rs 20. The nearest mandi (Kolar) nets only Rs 1,233: its expected price is about Rs 1,305, fee Rs 52, no wait, no transport, handling Rs 20. The extra Rs 776 of price at Ramanagara beats the extra Rs 94 transport and Rs 60 spoilage by a wide margin.",
        "**A3. What if transport is Rs 3.00 per quintal-km.** The normal tempo rate is about Rs 0.70 per quintal-km (worked back from the Rs 94 transport for 103 km); Rs 3.00 is more than four times that. At Rs 3.00 the transport for 103 km becomes about Rs 400 per quintal (3.0 x 1.3 x 103), so net falls to Rs 1,515, **but the advice stays the same**. Message: the advice is robust to the truck.",
        "**A4. What if spoilage is 5 percent a day.** Waiting a day now costs so much that the advice flips: go to Ramanagara **today** (no wait), net Rs 1,789. Message: the advice is sensitive to how quickly the crop spoils. The what-if panel shows exactly where it flips (the break-even).",
        "**A5. Has this advice worked.** Replay on days the advice had not seen: better than the nearest mandi on 93 percent of days; the floor held on 84 percent of days against an aim of 90. We say this openly: it is slightly below the aim.",
        "**A6. Language switch** to Kannada and back: every panel switches, which proves the three-language support is real and not just labels.",
    ],
    numbers=[
        ("Rs 1,824 / Rs 1,316 / Rs 592", "expected net, floor, and gain over nearest mandi."),
        ("Rs 2,081 - 83 - 60 - 94 - 20", "price, fee, spoilage, transport, handling."),
        ("Rs 3.00", "stress value for transport; advice unchanged, net Rs 1,515."),
        ("5 percent spoilage", "makes the advice flip to selling today at Rs 1,789."),
        ("93 percent / 84 percent", "better than nearest on 93 percent of replayed days; floor held 84 percent."),
    ],
    limits=["Figures are from the data loaded on 29 October 2026 (prices to 26 October). If the app is run with fresher data the numbers will differ; say so if asked."],
    ask=[
        ("Is the demo live or recorded?", "Live from the repository. If the network fails, the digest builder has an offline dry-run mode and every screen is also shown as a screenshot on the results slides."),
        ("Why is the floor Rs 508 below the expected value?", "Rs 1,824 minus Rs 1,316 is Rs 508. That is the margin learned from past errors so that actual revenue falls below it only about once in ten."),
    ],
))

SLIDES.append(dict(
    n=12, title="Live demonstration (2/2): trader desk and Telegram",
    one="Silence tax, the crowd simulator, then the phone: a real message from the real bot.",
    plain=[
        "The second half moves to the trader's view and then to the farmer's phone. The crowd simulator is the most surprising screen: the same advice that is best for one farmer is bad when 200 follow it.",
    ],
    deeper=[
        "**B1. Silence tax (tomato).** Kanakapura costs Rs 313 per quintal (16.5 percent of its price) because it is often unexpectedly silent. Chikkaballapur is closed on Thursdays, so the app treats Thursday as a known closed day. Kolar shows Rs 0, but that does **not** mean Kolar is reliable: its price is low enough that silence costs no money on price. This is why the screen shows surprise silence beside the tax.",
        "**B2. Crowd simulator, 200 farmers x 10 quintals.** A single farmer following the advice nets Rs 1,824. If all 200 follow it, the best yard sees 2,000 extra quintals when it usually receives about 68 a day; its price falls 32.5 percent and each farmer nets only Rs 1,194, which is even worse than everyone going to the nearest mandi (Rs 1,207). A coordinated split, where farmers are told different actions with stated probabilities, nets Rs 1,436, i.e. about Rs 241 per quintal more than everyone following the same advice, Rs 482,705 for the group.",
        "**B3. Drag farmers to 1, and flexibility b to 0.** With one farmer, or with no price response to arrivals (b = 0), all policies are equal. This shows the result depends on a stated assumption, which is the honest way to present a scenario.",
        "**C1 to C3, Telegram.** The bot @MandiAis_BOT answers /today with a dated digest: Ramanagara at Rs 1,824 with floor Rs 1,316 for tomato; potato gets prices only (limited evidence). Typing 'onion chintamani' returns that crop and place. Running send_daily_digest.py is the 7 am job: the phone buzzes and the log line shows 'sent'.",
        "**D1. API docs (optional).** The interactive documentation lists the five insight endpoints and the notify routes, showing the system is a proper service, not a notebook.",
    ],
    why=["Showing the crowd result first with b at its estimated value and then at zero lets the audience see the assumption doing the work."],
    limits=["The crowd result is a scenario, not a measurement. The Telegram demo runs from a laptop with data three days old; the message says so."],
    ask=[
        ("Why would a farmer ever not follow the best advice?", "They would, individually. The point is that advice given to many people needs coordination, otherwise it destroys its own value. Our coordinated split assigns different actions with stated probabilities."),
        ("How do you know b = 0.115?", "It is the within-mandi, within-month association of price with arrivals in the tomato data (standard error 0.023). It is a statistical association, not a proven cause, so we treat it as an adjustable scenario."),
    ],
))

SLIDES.append(dict(
    n=13, title="Tools, technology stack and code quality",
    one="What we built it with, why each tool, and how we know it works.",
    plain=[
        "The stack is a standard modern one: Python for data and models, FastAPI for the service, Next.js for the web app, Telegram for messages. Every version is pinned, so the same code gives the same numbers on any machine.",
    ],
    deeper=[
        "**Data and statistics.** NumPy and pandas hold the panel and do the arithmetic; SciPy and statsmodels supply statistical tests (for example Newey-West). The versions are pinned because NumPy 2 broke pandas once (risk R4).",
        "**Learning.** LightGBM and XGBoost are gradient-boosted decision trees, the strongest standard method for table-shaped data (reference 19 shows trees beat deep networks on typical tabular data). scikit-learn provides utilities and linear stacking. Optuna searches for good settings automatically (TPE, a smart trial-and-error method). PyTorch is used for the neural model in a separate research environment.",
        "**Backend.** FastAPI provides typed, validated web endpoints and automatically generated API documentation; Uvicorn runs it; Pydantic checks that requests and responses have the right shape, so a malformed request is rejected before it reaches a model.",
        "**Frontend.** Next.js with React and TypeScript renders pages on the server, so they load fast even on weak mobile connections. Tailwind handles styling.",
        "**Language layer.** gpt-oss-120b writes the explanations and a Qwen model judges them, both through Groq. The judge is from a different model family on purpose, so the writer does not grade its own work. A Claude provider can be plugged in optionally. If the service fails, a deterministic writer takes over.",
        "**Quality.** pytest and vitest run the tests; GitHub Actions runs them on every push; Docker and a Render file describe deployment (not verified live).",
        "**Code-quality evidence.** 69 Git commits; README; requirements.lock; docs for architecture and tool choices; CI workflow; 669 backend tests and 11 web tests; a 60-check smoke test that exercises every endpoint and page; a fresh-clone check that the project works from a clean copy.",
        "**Reproducible.** pipeline.py regenerates every artefact, and the thesis tables are generated from those artefacts, not typed.",
    ],
    why=["Pinned versions plus one-command regeneration make the results repeatable; the smoke test and fresh-clone check catch the exact failures we hit (stale server code, missing store)."],
    limits=["Deployment is described by configuration files but not verified live."],
    ask=[
        ("Why gradient boosting and not deep learning?", "On table-shaped data of this size, trees usually win and are cheaper to train, run and explain. We tested a neural model too and it made equal decisions; we served the cheaper one."),
        ("What does a smoke test do?", "It starts the system and calls every endpoint and page once, so any broken route shows up immediately; 60 checks."),
    ],
))

SLIDES.append(dict(
    n=14, title="Experimental setup and evaluation metrics",
    one="How the experiments were run so that no test result can have seen the future, and how every claim is measured.",
    plain=[
        "**The rule: only the past may be used to predict the future.** We cut the timeline into five test blocks from 2024 first half to October 2026. For each block, the model is trained only on days before it, then tested on that block. This is called walk-forward testing. It mimics real life, where you never have tomorrow's data.",
        "**Nested** means that inside each training period we repeat the same trick to choose settings (such as tree depth) without ever touching the real test days. Settings are searched by Optuna: 20 trials for neural models, 25 for boosting, the same for every method so no method gets an unfair advantage.",
    ],
    deeper=[
        "**The K+2 day gap.** A hold of up to 3 days means a decision on day t depends on prices up to day t+3, so a training example near the end of the training window would have a target that overlaps the first days of the test block. Leaving a gap of K+2 days before every validation or test block removes that overlap, so no four-day target is shared between training and test.",
        "**Metrics, one by one.** (1) *Realised revenue*: average net revenue per quintal actually received if you follow the method, over test days and five farmer origin points. (2) *Regret*: oracle revenue minus the method's revenue; lower is better. (3) *Share of oracle gap closed*: (method - nearest mandi) / (oracle - nearest mandi). For tomato: (2,156 - 1,600) / (2,570 - 1,600) = 0.57. (4) *Silent-market trips*: share of recommendations that sent the farmer to a mandi that was silent that day. (5) *Floor violation*: share of test days on which realised revenue fell below the stated floor, compared with the nominal level. (6) *Forecast skill*: improvement over the 'no change' forecast, in percent.",
        "**Baselines (all retrained or recomputed on the same split).** Random walk with transport costs (use yesterday's prices). LightGBM and XGBoost trained on observed prices (the standard predict-then-optimise approach). Nearest mandi, sell today (what many farmers do). Highest price yesterday (what a farmer reading the portal would do). Best seven-day mean. Farm gate. We also train LightGBM on realised outcomes so that we can separate a better label from a better learner.",
        "**Inference tools in plain words.** *Moving-block bootstrap, block 14*: to see how much a result could wobble by chance, we re-sample the test days in chunks of 14 consecutive days (not single days, because adjacent days are related), many times. *Newey-West Diebold-Mariano test*: a standard test of whether two methods differ in accuracy, corrected for the fact that errors on neighbouring days are related. *Holm correction*: when you run many comparisons, some look significant by luck; Holm tightens the threshold in a principled way across all pre-specified comparisons. *Model confidence set*: the list of methods that cannot be statistically separated from the best.",
        "**Pre-specified** means the model ladder (which models in which order), the 12 paired comparisons, the silence tests and the leakage protocol were written down before looking at tuned results. This stops us from picking the comparisons that happen to look good.",
        "**The dataset table.** Per crop: mandi-days (filled cells), number of mandis, 'eligible' mandis (at least 700 reported days), scored test days. Tomato 17,582 mandi-days, 14 mandis, 12 eligible, 963 test days; onion 5,343, 11, 4, 511; potato 5,000, 12, 3, 569; ginger 6,423, 10, 3, 776. Garlic 2,473 mandi-days, 7 mandis but only 1 eligible: refused.",
        "**Hardware.** Core i9-13900HX, 31.7 GB RAM, RTX 4060: an ordinary high-end laptop. Fixed random seeds are recorded.",
    ],
    why=["Walk-forward with a gap, pre-specification and an equal tuning budget are what make the comparisons fair. Each is a defence against a specific way results can be inflated."],
    limits=["Only 5.8 years of data and one region; a silent day is treated as no sale at a discounted fallback; offline only."],
    ask=[
        ("What is 'oracle'?", "A seller who knows the future prices and picks the best action each day. It is the unreachable ceiling that makes 'gap closed' interpretable."),
        ("Why 12 comparisons, and what is Holm for?", "Comparisons were fixed in advance. When you test many, a few will look significant by chance; Holm adjusts the p-values to account for that."),
        ("Why 14-day blocks?", "Prices on neighbouring days are strongly related; blocks of 14 days keep that relation intact when re-sampling, so the uncertainty is not understated."),
    ],
))

SLIDES.append(dict(
    n=15, title="Results and validation: decision quality",
    one="Models trained on what the farmer receives earn the most in every crop, and the reason is that they avoid silent mandis.",
    plain=[
        "For tomato, over 963 test days: sending the farmer to the nearest mandi earns Rs 1,600 per quintal; our model trained on realised revenue earns Rs 2,156; the hindsight oracle earns Rs 2,570. So we capture most of the available improvement: Rs 556 more than nearest mandi.",
        "**Why does it win?** Models trained on observed prices recommend a silent mandi 12 to 43 percent of the time, because on silent days there is no price row to learn from, so the model never learns that silence exists. Models trained on realised revenue learn it from the label (silent days carry the lower fallback revenue) and cut such trips to 5 to 21 percent.",
    ],
    deeper=[
        "**Reading the three big numbers.** 'Rs 2,156: tomato, realised-label model (oracle 2,570)'; '+Rs 556 over nearest mandi'; 'Holm p < 0.002: labels effect in all four crops' (the lowest-evidence crop, potato, has p = 0.002).",
        "**Ordering seen in every crop.** Nearest mandi worst; then highest price yesterday, the random walk and the boosted model on observed prices, which are close to each other; then the two models trained on realised outcomes (LightGBM and the neural SPO+ model) best. For tomato the highest price yesterday earns Rs 2,021.",
        "**Mechanism.** A model trained on the posted price sees only the days the mandi reported. Every row it learns from is an open mandi. It therefore overestimates the price at unreliable mandis and recommends them. Training on realised revenue, where silent days appear with their lower fallback value, teaches it to discount unreliable mandis. The slide's second line is this mechanism in one sentence.",
    ],
    numbers=[
        ("Rs 1,600 / 2,021 / 2,156 / 2,570", "tomato: nearest mandi / highest price yesterday / ours / oracle."),
        ("12 to 43 percent vs 5 to 21 percent", "silent-market recommendation share: observed-price models vs realised-label models."),
        ("963 days", "scored test days for tomato (511 onion, 569 potato, 776 ginger)."),
    ],
    limits=["One region and one data source; revenue parameters are assumptions (varied in a sensitivity sweep: across 10 settings the realised-label models close 9 to 36 percent of the gap relative to highest price yesterday while observed-price models stay between -8 and +2 percent)."],
    ask=[
        ("Is Rs 556 a lot?", "It is 35 percent more than the nearest-mandi revenue (556 / 1,600) and 57 percent of the whole possible improvement to the oracle."),
        ("Why not 100 percent of the gap?", "Nobody can see the future; the oracle is only a ceiling."),
    ],
))

SLIDES.append(dict(
    n=16, title="Statistical validation: what actually improved decisions",
    one="Two separate ideas were tested; only the first (better labels) is a reliable improvement.",
    plain=[
        "A change could help for two different reasons and we tested them one at a time. **Idea 1: change the label** from the observed price to realised revenue (same learner). **Idea 2: change the loss** from squared error to SPO+ (same labels). The table shows how much the regret changes, in rupees per quintal; negative means better.",
        "Result: Idea 1 helps in all four crops with very strong evidence. Idea 2 gives small changes whose intervals include zero, so it is not reliable. In plain words: **the gain comes from teaching the model what the farmer actually gets, not from fancy training mathematics.**",
    ],
    deeper=[
        "**How to read a row.** Tomato, labels: -140 [-181, -102], Holm p < 0.0001. On average the regret falls by Rs 140 per quintal. The bracket is the 95 percent confidence interval: the true effect is very likely between -181 and -102. Since the whole interval is below zero, the improvement is real. Holm p tells you it is not a fluke even after correcting for the many comparisons we ran.",
        "**Tomato, SPO+ vs squared error:** -25 [-53, +3], Holm p = 0.51. The point estimate is an improvement of 25 rupees, but the interval runs from -53 to +3, which includes zero, and the adjusted p-value of 0.51 means such a result could easily happen by chance. So we cannot claim an improvement. Potato even shows +1 (no change). Ginger shows -66 but with a very wide interval [-180, +30].",
        "**Model confidence set.** This procedure keeps every model that cannot be statistically distinguished from the best one. Only models trained on realised outcomes survive in every crop; **no observed-price model survives in any crop**. Tomato keeps 7 specifications, the others 3. Being kicked out of the set means significantly worse than the best.",
        "**Why we present it this way.** The expected hypothesis from the literature was that SPO+ would help. We report that in this problem it did not, consistent with the large benchmark by Mandi and co-authors showing that its benefit depends on the problem.",
    ],
    numbers=[
        ("-87 to -157 Rs/q", "labels effect on regret, potato to onion."),
        ("-66 to +1 Rs/q", "range of SPO+ effects, none reliably different from zero (Holm p 0.17 to 0.95)."),
        ("7 and 3", "specifications kept in the model confidence set: tomato, and the other crops."),
    ],
    limits=["One region, one source, 5.8 years; revenue parameters are scenarios; a silent day is treated as no sale at a discounted fallback; offline only."],
    ask=[
        ("If SPO+ is 'decision-focused', why did it not help?", "Possibly because once the labels already contain the decision-relevant information, the loss adds little; and the theory behind SPO+ assumes a particular structure. We simply report that on this data it did not help."),
        ("What is a confidence interval in one sentence?", "A range that, if we repeated the study many times, would contain the true value 95 times out of 100."),
        ("What is Holm in one sentence?", "A correction that makes it harder to call something significant when we have run many tests, so that we are not fooled by luck."),
    ],
))

SLIDES.append(dict(
    n=17, title="Verified floors and served-engine back-test",
    one="The floors hold close to their promised rate, and the engines that the app actually serves beat the best simple rule in three of four crops.",
    plain=[
        "**Left table: do the floors keep their promise?** A floor is violated on a day if the farmer's actual revenue turns out lower than it. If we set the floor for a 10 percent miss rate, about 10 percent of days should be violations. The table shows the real rates for five ways of making a floor.",
        "**Right table: do the served engines actually beat simple rules?** We replayed the engines the app uses over the last 330 days, using on each day only information available then. The gain is how many rupees per quintal more than the strongest simple rule (the highest price yesterday) and than going to the nearest mandi.",
    ],
    deeper=[
        "**Columns of the left table.** *Adaptive 5, 10, 20 percent*: our adaptive floor aimed at that miss rate. *Static 10 percent*: a floor from one fixed conformal margin that does not adapt. *Naive Gaussian*: the textbook floor that assumes errors are bell-shaped (mean minus 1.28 standard deviations for 10 percent).",
        "**What the numbers show.** At the 10 percent setting our adaptive floors were violated on 9.0 (tomato), 6.3 (onion), 6.9 (potato) and 10.5 (ginger) percent of days: close to the target and never wildly off. At 5 percent: 3.0, 1.6, 2.5, 4.3. At 20 percent: 21.3, 15.5, 17.7, 20.4. The static version is cautious (4.0 to 8.9 percent at the 10 percent setting), safe but unnecessarily low. The naive Gaussian floor is broken on 26 to 35 percent of days in three crops against a 10 percent target (27.4, 34.5, 25.8), meaning it promises something it cannot deliver; it looks fine for ginger (11.9) only by coincidence.",
        "**Objective 4 reading.** The aim was within two points of 10 percent. Tomato (9.0) and ginger (10.5) are inside; onion and potato are lower, i.e. conservative.",
        "**The back-test table.** Tomato: our advice beat the highest price yesterday by Rs 170 per quintal, 95 percent interval [+104, +255] (excludes zero, strong); and beat the nearest mandi by Rs 571. The advice closes 62 percent of the gap between nearest mandi and oracle. Onion: +60 [+16, +119] strong, gap closed 46 percent. Potato: +15 [-38, +60], interval includes zero, only 11 percent of the gap: **limited evidence**, and the app labels potato advice as limited. Ginger: +202 [+25, +429], gap closed 67 percent, strong but with a wide interval (few days, big swings).",
        "**Do not confuse with slide 25.** Slide 25's 'gap closed' (0.57 for tomato) is from the research evaluation over 963 test days across five blocks. Slide 17's 62 percent is the served engine over the last 330 days. Different windows and different models, hence slightly different numbers.",
    ],
    why=["The evidence tier (strong or limited) is a safeguard: the app only gives advice for a crop when the back-test supports it, and tells the farmer when it does not."],
    limits=["Floors are close, not exact; the strictest replay on slide 19 gives lower hold rates. Potato advice cannot be distinguished from the best heuristic."],
    ask=[
        ("Why are onion and potato floors so low (6 to 7 percent) at a 10 percent target?", "The adaptive rule was conservative on those crops: it leaves more room than needed. That is safe for the farmer but not as sharp as promised."),
        ("Why is the naive Gaussian floor so bad?", "Price errors have heavy tails and change over time; assuming a bell curve underestimates bad days."),
    ],
))

SLIDES.append(dict(
    n=18, title="Explaining the advice: why this mandi, what if",
    one="The arithmetic behind the recommendation and where it breaks.",
    plain=[
        "This is the demo's Why-this-mandi and What-if screens, written as sentences. The advice (Ramanagara, tomorrow) wins because its expected price is Rs 776 higher than the nearest mandi (Kolar), and that gain is larger than the Rs 94 of extra transport and Rs 60 of spoilage. It is robust to the truck cost and sensitive to shelf life.",
    ],
    deeper=[
        "**Parts add up:** 2,081 - 83 - 60 - 94 - 20 = 1,824. The nearest mandi keeps Rs 1,232 (Rs 1,233 on the demo slide; rounding). Advantage: 1,824 - 1,232 = Rs 592.",
        "**Why it wins:** 776 (extra price) - 94 (extra transport) - 60 (spoilage) - 32 (extra fee, 4 percent of 776 is about 31) leaves the remaining advantage close to 592. In words: you gain 776 in price and give back about 185 in costs.",
        "**Robust to the truck:** at the extreme transport of Rs 3.00 per quintal-km the net is Rs 1,515 and the advice is unchanged: even at that cost the farmer is better off.",
        "**Sensitive to shelf life:** at 5.0 percent spoilage a day, or if the farmer cannot wait at all, the advice becomes Ramanagara **today**, net Rs 1,789. The break-even for spoilage is where it flips.",
        "**Floor is indicative far from defaults:** the floor margin was calibrated at the default costs. If a farmer enters very different costs, the net is still exact but the floor margin is only a guide, and the screen says so.",
    ],
    ask=[("Why not simply tell farmers to go to the highest-price mandi?", "Because the highest price may be far, silent that day, or lose value while waiting. The breakdown shows the real trade-off in rupees.")],
))

SLIDES.append(dict(
    n=19, title="Public track record on days the advice had not seen",
    one="On 165 days after the floor was fitted, the advice wins against the nearest mandi on most days and the floors hold on 84 to 92 percent of days.",
    plain=[
        "A track record is only honest if it uses days the system was not tuned on. We replay the advice on 165 days (12 May to 23 October 2026). The floor multiplier was fitted on the earlier half, so every day shown is a day the floor was not fitted on.",
    ],
    deeper=[
        "**Columns.** *vs nearest*: win, tie, loss of the advice compared with going to the nearest mandi. *vs yesterday's best*: compared with going to yesterday's highest-priced mandi. *Floor held*: share of days where realised revenue was at least the floor.",
        "**Reading tomato.** vs nearest: 93 percent wins, 0 ties, 7 percent losses. vs yesterday's best: 24 wins, 68 ties, 8 losses: on 68 percent of days the advice picks the same action as yesterday's best, so the difference is within Rs 1 (a tie); where they differ, the advice wins 24 percent against 8 percent losses. Floor held on 84 percent of days.",
        "**Onion** 82/0/18 vs nearest; 34/39/27 vs yesterday; floor 89. **Potato** 63/2/35; 52/12/36; floor 92. **Ginger** 90/0/10; 23/54/23; floor 86. Note that for ginger wins equal losses (23 each) against yesterday's best: no edge there on this measure, even though the back-test average gain is positive.",
        "**The honest part.** The floor was set to hold on nine days in ten (90 percent), but held on 84, 89, 92 and 86 percent. Three of four are below the aim. Why lower than slide 17? Because this replay is the strictest of three evaluations: one multiplier fitted on half of the window and then frozen. The three views of the same question: the served rule's 330-day back-test violated 9.6 to 12.3 percent; a static multiplier evaluated out of sample 7.8 to 17.7 percent; this replay 8 to 16 percent violated.",
        "**What a tie means.** A difference of at most Rs 1. Against yesterday's highest price the advice often chooses the same action, so ties dominate. This is not a weakness: it shows the system agrees with the sensible simple rule on most days and improves on the days where the rule fails.",
    ],
    limits=["165 days is a short window; only the second half of the scored days; potato's 35 percent loss rate against nearest mandi shows its advice is weaker."],
    ask=[
        ("The floor held only 84 percent for tomato. Is that a failure?", "It is below the 90 percent aim and we say so. It is the strictest evaluation (one multiplier fitted on half the window and frozen). On the main evaluation of slide 17 the violation was 9.0 percent. The floors are close to their level, not exact, and the app tells the farmer."),
        ("Why does potato show 35 percent losses to the nearest mandi?", "Potato prices vary little across mandis, so the gain is small and noisy; the app marks potato evidence as limited."),
    ],
))

SLIDES.append(dict(
    n=20, title="Silence tax: what an unreliable mandi costs a trip",
    one="Rupees lost per quintal because a mandi reports no price on a day you travelled there.",
    plain=[
        "If you drive to a mandi and it has no market that day, you sell in a weaker position (we assume 85 percent of what other mandis paid that day). The silence tax is the expected rupees per quintal lost to that risk. A mandi with a good price but frequent surprise closures can be a worse choice than a plainer reliable one.",
    ],
    deeper=[
        "**Formula (slide 8).** T = s x max(P_m - 0.85 x P_day, 0): the share of surprise silence times how much the mandi's usual price exceeds the fallback.",
        "**Columns.** *Reported*: share of days with a price. *Surprise silence*: share of open days (known closed days excluded) when it was silent anyway. *Known closed*: weekday on which it is silent on at least 90 percent of occasions, which farmers already know (Sunday for most). *Tax per quintal*: expected loss, with its percentage of the mandi's price.",
        "**Reading the table.** Kanakapura: reported on 44 percent of days, surprise silence 49 percent, closed Sundays, tax Rs 313 (16.5 percent of its price): by far the worst. Binny Mill Rs 206 (8.5 percent). Doddaballapur Rs 135. Gauribidanur Rs 121 (closed Tuesdays). Channapatna Rs 120. Bagepalli Rs 69. Ramanagara just Rs 40 (1.8 percent), reporting on 95 percent of days. The mean over 13 tomato mandis is Rs 78 per quintal per trip.",
        "**Derived cross-check.** Rs 313 at a 16.5 percent tax means Kanakapura's typical price is about Rs 1,900 (313 / 0.165). Dividing the tax by its surprise silence (0.49) gives about Rs 640: that is how much its usual price exceeds the 85-percent fallback.",
        "**Chikkaballapur.** It reported on none of last year's Thursdays, so Thursday is treated as a closed day and a farmer is warned not to bring a Thursday load there.",
        "**Two cautions.** (1) A silent day may be a closed mandi or a missed upload; the portal does not say. (2) Rs 0 for a cheap mandi such as Kolar does not mean it is reliable: its usual price is below the fallback, so silence costs nothing in price terms. That is why 'surprise silence' is shown alongside the tax.",
    ],
    why=["This is the one feature that turns the data's weakness (missing days) into information. It is also the reason realised-label models beat observed-price ones."],
    limits=["The 0.85 fallback is an assumption; closed versus missed upload cannot be distinguished."],
    ask=[
        ("What is the difference between 'reported' and 'surprise silence'?", "Reported counts all days. Surprise silence counts only days the mandi was normally open, so Sunday closures do not count against it."),
        ("Why is Ramanagara used in the advice even though others have higher prices?", "It reports on 95 percent of days, so a trip there rarely ends in a wasted journey: its silence tax is only Rs 40."),
    ],
))

SLIDES.append(dict(
    n=21, title="Crowd simulator: what if everyone follows the advice?",
    one="Advice that is best for one farmer can be poor for two hundred, unless it is coordinated.",
    plain=[
        "Imagine 200 farmers in Kolar each with 10 quintals of tomato all read the same screen and drive to Ramanagara. That is 2,000 quintals arriving at a yard that normally receives about 68 quintals a day. Price falls. The simulator shows how far, and what a smarter way of spreading farmers would earn.",
    ],
    deeper=[
        "**Formula.** P(x) = P x (1 + x / A)^(-b). Worked check: x = 2,000, A = 68, b = 0.115 gives (1 + 29.4)^(-0.115) = 30.4^(-0.115) = e^(-0.115 x 3.41) = e^(-0.392) = 0.675. So the price falls 32.5 percent, the number on the slide.",
        "**Three policies.** *All follow the best*: everyone goes to Ramanagara; each nets Rs 1,194. *All go to the nearest mandi*: Rs 1,207 (the nearest, Kolar, then gets crowded too). *Coordinated split*: farmers are given different actions, in steps, each step to the action with the best marginal revenue; each nets Rs 1,436. A single lone farmer following the advice nets Rs 1,824.",
        "**Gains.** The coordinated split earns Rs 241 per quintal more than everyone following the same advice (1,436 - 1,194 = 242 from rounded numbers), which is Rs 482,705 more for the group of 200 farmers over 2,000 quintals (241.35 x 2,000).",
        "**Why b matters.** b is the price flexibility: how strongly price falls as arrivals rise above normal. b = 0 means no price response, and all policies are the same. The result strengthens as b rises. 0.115 is an association measured in past data (standard error 0.023), not a proven cause.",
        "**As the crowd grows to 2,000 farmers** every policy gets worse and coordination matters more (thesis table).",
    ],
    numbers=[
        ("-32.5 percent", "price drop at the best yard when 200 farmers (2,000 quintals) arrive."),
        ("Rs 241 per quintal", "gain of the coordinated split over everyone following the same advice."),
        ("Rs 482,705", "gain for the whole group of 200 (241 x 2,000)."),
        ("68 quintals", "the yard's usual daily arrivals (median over the last year)."),
    ],
    limits=["A scenario, not a measurement. The real response to a crowd of advised farmers has never been observed; a field pilot is needed."],
    ask=[
        ("Is this realistic, would 200 farmers follow one app?", "Probably not at first, which is why it is a scenario. The point is a warning: advice built for one farmer must not be scaled blindly, and coordination changes the outcome."),
        ("How is the coordinated split implemented?", "The quantity is handed out in small lots; each lot goes to whichever option currently gives the best marginal revenue; each farmer then gets an action with a stated probability."),
    ],
))

SLIDES.append(dict(
    n=22, title="Daily digest on Telegram",
    one="A dated morning message in the farmer's language, with advice only where the evidence is strong.",
    plain=[
        "Farmers do not open dashboards; they read messages. The bot sends one message at 7 am: the latest price in their district for each crop they chose, with its date, and for the crops where our back-test is strong, the best place and day to sell with the floor. Telegram is free, which matters for a project with no budget.",
    ],
    deeper=[
        "**Dated, always.** Every price carries its date, and the second line says how old the data is (3 days old on 29 October). There is no live feed: Agmarknet exports are loaded by hand, so we say how fresh the message is instead of pretending.",
        "**Advice only with evidence.** Tomato, onion and ginger have strong back-tests, so they get the best place and day with the floor. Potato (limited evidence) and garlic (no choice) get prices only.",
        "**Warns about silent days.** If the recommended mandi was silent on most past occurrences of the sale weekday, the message says so.",
        "**Three languages.** English, Kannada, Hindi. Commands: /start (choose language and crops), /today (send now), /stop (unsubscribe). A farmer can also type a free sentence such as 'tomato kolar' and it is parsed for crop and place in all three languages.",
        "**Logged and tested.** Every send is logged (two logged sends to a real account); a blocked bot marks the subscriber inactive; 8 unit tests use a fake Telegram client with no network: dates present, advice only for strong crops, Kannada labels, free-text parsing, onboarding, refusing a farmer with no crop, unsubscribe.",
        "**How the 7 am happens.** The script send_daily_digest.py is the daily job. A real deployment would schedule it on a server; on our laptop we run it by hand or on a timer, and a dry-run mode builds messages without sending.",
        "**Not claimed.** A farmer pilot, or a live price feed. The digest is built from stored data only.",
    ],
    why=["Telegram has a free official bot interface and works on low-end phones; SMS gateways require paid registration in India, so they cannot be shown freely."],
    limits=["Only one real account (a team member) has received messages; no farmer has used it."],
    ask=[
        ("Why Telegram and not SMS or WhatsApp?", "Free and official API, no registration cost, rich text and buttons. SMS in India needs paid, registered senders; WhatsApp Business requires approval and fees."),
        ("Where is the token stored?", "In a git-ignored environment file; it is never printed or logged."),
    ],
))
