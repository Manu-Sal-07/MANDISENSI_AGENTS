"""Deep-dive guide content, part 1: front matter and slides 1-10.  Entry format: see build_deep_dive.py."""

FRONT = {
    "how": [
        "This guide is for the three of you, not for the examiners. The speaker notes tell you **what to say** in a minute or two; this guide tells you **what everything on the slide actually means**, so that when someone asks a second or third question you are standing on solid ground.",
        "It follows the deck slide by slide (35 slides). Every slide has the same parts: **In one line**, **In plain words** (the idea without jargon), **Go deeper** (the technical content, explained term by term), **The numbers and what each one means**, **Why we did it this way**, **Limits (say these yourself)** and **If asked** (likely questions with answers).",
        "Technical words are never left unexplained: each is introduced once in plain language and then used. If a word still feels foreign, look it up in the glossary in Part A. The hardest slides are 14 to 27 (setup, results, validation, benchmarking, ablation); they have the longest sections on purpose.",
        "Every number comes from the deck, the thesis tables or the code outputs. Where a number is derived (for example a percentage worked back from two other numbers) the guide says so. Never quote a number that is not in the deck unless you have checked it in the thesis.",
    ],
    "storyline": [
        "**The problem.** A farmer near Bengaluru or Kolar picks where and when to sell with only yesterday's prices, and some mandis post no price at all on some days. A wrong pick costs hundreds of rupees per quintal.",
        "**Our idea.** Teach the model with what the farmer actually receives (after transport, fees, spoilage and the chance that the mandi is silent), not with the posted price. Then attach a floor: a minimum amount the farmer can count on nine days out of ten.",
        "**What worked.** Training on what the farmer receives beats every simple rule in all four crops, and the result is statistically solid. The floors stay close to their promised level.",
        "**What did not work, and we say so.** A fancier training loss (SPO+), a reporting head, silence features, a council of forecasters and a cross-crop spillover engine did not help. A published family of forecasting models turned out to peek at the future; when the peeking is removed, their gains vanish.",
        "**Five ways we make the advice checkable** (breakdown, what-if, track record, silence tax, crowd simulator) and **one way it reaches the farmer** (the 7 am Telegram digest).",
    ],
    "glossary": [
        ("Mandi / APMC", "A regulated wholesale market yard where farmers sell produce. APMC is the legal name of the committee that runs it."),
        ("Agmarknet", "The Government of India portal that publishes daily mandi prices and arrivals. Our only data source."),
        ("Quintal", "100 kg. All prices are rupees per quintal."),
        ("Modal price", "The most common trading price in a mandi that day (not the average)."),
        ("Net revenue", "What a farmer really keeps per quintal: price minus market fee, minus spoilage loss, minus transport, minus handling."),
        ("Hold (k days)", "Waiting k days (0 to 3) before selling. Waiting can earn a better price but costs spoilage."),
        ("Farm gate", "Selling at the farm to a buyer who comes there. No transport, but a lower price (we assume 80 percent of the day's average)."),
        ("Silent mandi / reporting gap", "A mandi that posted no price that day: closed, a holiday, or the data was not uploaded. The portal does not say which."),
        ("Panel", "The big table of prices: one row per mandi per crop per day."),
        ("Mandi-day", "One mandi on one day. 36,821 mandi-days means that many filled cells in the panel."),
        ("Oracle", "The imaginary seller who knows tomorrow's prices and always picks the best option in hindsight. No real method can reach it; it is the ceiling for comparison."),
        ("Regret", "Money lost compared with the oracle: oracle revenue minus the revenue you got. Lower is better."),
        ("Gap closed", "How far a method moves from the worst simple rule (nearest mandi) towards the oracle. 0 means no better than nearest mandi, 1 means as good as the oracle."),
        ("Label", "The 'right answer' a model is trained to predict. Our key idea is to use realised revenue as the label instead of the posted price."),
        ("Loss function", "The score that tells a model how wrong it is during training. Squared error is the usual one; SPO+ is a decision-aware alternative."),
        ("SPO+", "A training loss that punishes the model by how much worse the decision it leads to is, not by how far its prediction is from the number. It did not give a reliable gain here."),
        ("Floor (guaranteed revenue)", "A minimum net revenue we say the farmer can count on. We set it so that real revenue falls below it on about 1 day in 10."),
        ("Conformal prediction", "A way to turn past mistakes into a safety margin without assuming any particular shape of error. If past predictions missed by this much, leave this much room."),
        ("Adaptive conformal inference (ACI)", "A conformal method that keeps adjusting the margin day by day: after a miss it widens, after a hit it narrows slightly, so the long-run miss rate stays near the target."),
        ("Delayed feedback", "We only learn whether a floor held after the sale date, k days later. The calibrator may use an outcome only once its sale date is in the past."),
        ("Walk-forward test", "Train on the past, test on the next block of days, then slide forward. Like real life: you never see the future."),
        ("Nested walk-forward", "Walk-forward with an inner walk-forward inside each training window, used to tune settings without touching the test days."),
        ("Leakage / look-ahead", "Information from the future slipping into training or into inputs, which makes results look better than they could be in real use."),
        ("STL, VMD, ICEEMDAN", "Methods that split a price line into smooth parts (trend, seasonal, wiggles) before forecasting. They use points on both sides of a day to smooth it, which is where leakage comes from."),
        ("Skill", "How much better a forecast is than the simplest guess 'tomorrow equals today' (the random walk). +10 percent is better, -10 percent is worse."),
        ("Random walk / no change", "The forecast 'tomorrow's price will equal today's'. Surprisingly hard to beat for daily prices."),
        ("Bootstrap / confidence interval", "Re-shuffling the observed data many times to see how much a number would wobble by chance. The 95 percent interval is the range that usually contains the true value."),
        ("Block bootstrap", "A bootstrap that re-shuffles chunks of consecutive days (we use 14 days) instead of single days, because neighbouring days are related."),
        ("p-value and Holm correction", "A p-value measures how surprising a result would be if nothing were really going on. When many comparisons are made, some look good by luck; the Holm correction raises the bar to compensate. 'Holm p below 0.002' means very unlikely to be luck even after that."),
        ("Diebold-Mariano / Newey-West", "A standard test for whether one forecasting method is really better than another, with a correction for the fact that errors on neighbouring days are related."),
        ("Model confidence set", "The list of methods that cannot be told apart from the best one statistically. Being outside the set means significantly worse than the best."),
        ("Ablation", "Removing or adding one component at a time to see what it actually contributes."),
        ("Null result", "An honest finding that something does not work or cannot be shown. Reported with equal weight to positive results."),
        ("Spillover / transmission", "Does a shortage or glut in one crop move the price of another crop. We tested this and found no usable evidence."),
        ("FDR (false discovery rate)", "The expected share of 'discoveries' that are false alarms among everything declared significant. We hold it at 10 percent."),
        ("Grounding", "Making sure every number a language model writes can be found in the evidence it was given."),
        ("LLM writer and judge", "One language model writes the explanation; a different model from another family checks whether the writing is faithful to the evidence."),
        ("Decision intelligence brief", "A structured short recommendation (action, confidence, reasons, each reason tied to an evidence item)."),
        ("API / endpoint", "A web address on our server that returns data, for example /v1/market-choice. The app and the Telegram bot both call these."),
        ("CI", "Continuous integration: tests run automatically on every code push."),
        ("WBS, critical path, slack", "WBS breaks the project into work packages; the critical path is the longest chain of dependent tasks that fixes the earliest finish; slack is how long a task can slip without delaying the project."),
    ],
    "numbers": [
        ("63,524", "real Agmarknet records used (rows after cleaning)"),
        ("36,821", "mandi-days in the final panel across five crops (tomato, onion, potato, ginger, garlic)"),
        ("4 crops studied, 1 refused", "garlic has only one eligible mandi so there is no choice to make"),
        ("Rs 2,156 vs Rs 1,600 vs Rs 2,570", "tomato: our model, nearest mandi, oracle (revenue per quintal)"),
        ("+Rs 556", "our gain over the nearest mandi for tomato (2,156 minus 1,600)"),
        ("Rs 87 to 157", "how much per quintal regret falls when we train on realised revenue (four crops); Holm p below 0.002 in all four"),
        ("9.0, 6.3, 6.9, 10.5 percent", "floor violation at the 10 percent setting (tomato, onion, potato, ginger)"),
        ("+Rs 170 and +Rs 202", "back-test gain over the strongest simple rule for tomato and ginger"),
        ("+27 to +62 percent becomes -15 to -1 percent", "skill of decompose-then-forecast models under published versus causal evaluation"),
        ("-32.5 percent, Rs 241, Rs 482,705", "crowd simulator: price drop at the best yard, gain per quintal of the coordinated split, gain for the group of 200"),
        ("669 + 11 tests, 60-check smoke test", "automated checks (backend, web, whole system)"),
        ("24 weeks planned, about 27 actual", "schedule slip of 3.3 weeks (14 percent), caused by the data restart"),
    ],
}

SLIDES = []

SLIDES.append(dict(
    n=1, title="Title", one="Who we are, what the project is called, and what phase this is.",
    plain=[
        "The title promises two things: **where and when to sell**, and **verified revenue floors**. 'Where' is which mandi; 'when' is how many days to wait (0 to 3). 'Verified revenue floor' is a minimum amount the farmer can count on, which we then check against real days to show it holds.",
        "Everything in the project is built around those two promises. If an examiner asks 'what is your project in one sentence', answer with the title: it tells a farmer where and when to sell and gives a minimum amount to count on.",
    ],
    deeper=[
        "'Project work Phase II, 23DS7PWPP2, Review 2' is the course code and review stage. Review 2 is the review where results, validation, novelty and planning are examined.",
        "'Verified' is a deliberate word. A floor is only useful if it actually holds. We tested it on days the system had never seen and report how often it failed (slides 17 and 19).",
    ],
    ask=[("Why is the word 'verified' in the title?", "Because many systems state a range without ever checking it. We replayed the floors on unseen days and report the honest miss rate: close to the promised 10 percent on the main evaluation and 8 to 16 percent on the strictest replay.")],
))

SLIDES.append(dict(
    n=2, title="Table of contents", one="The ten blocks of the talk, in the order the review form asks for them.",
    plain=[
        "The order is: problem and objectives, method and architecture, implementation, results and validation, novelty and optimisation, planning and risk, report and SDG, paper status, conclusion, references. The live demo is inserted after the implementation block (slides 10 to 12) so that the results that follow can be tied back to screens the examiners have just seen.",
    ],
    deeper=["Think of the talk in three acts: **what and why** (slides 3 to 9), **show it** (10 to 12), **prove it** (13 to 27), **manage and conclude** (28 to 35)."],
    ask=[("Why is the demo before the results?", "So the evaluators have seen what the system does before they see the numbers that justify it; each result slide then refers to a screen they know.")],
))

SLIDES.append(dict(
    n=3, title="Introduction and problem statement",
    one="Farmers choose a market with almost no information, and our job is to choose better and say how sure we are.",
    plain=[
        "A farmer in the Bengaluru-Kolar belt has a truckload of tomatoes. There are a dozen mandis within reach. The only information is yesterday's price in each. But tomatoes spoil: a day of waiting costs about 3 percent of their value. Some mandis post no price on some days (closed, holiday, or the data was not uploaded), so a trip can end at a mandi with no market that day. And the price swings enormously: Kolar tomato ranged from Rs 100 to Rs 9,330 per quintal across the data.",
        "So the decision is: **which mandi, and wait 0, 1, 2 or 3 days, or sell at the farm gate**, to keep the most money. And the farmer also needs a minimum they can count on, because a farmer who stakes a whole harvest cannot live with 'the forecast says about Rs 1,800'.",
    ],
    deeper=[
        "**Silent on 189 of 2,125 days** means that for Kolar tomato, out of 2,125 calendar days in the history, there was no price on 189. That is 8.9 percent of days. A model trained only on posted prices never sees these days (they are missing rows), so it cannot learn that a mandi can be silent.",
        "**The gap** has three strands, each from the literature survey (references 1 to 6): (1) forecasting models are judged by forecast error (RMSE, MAPE), not by how good the resulting decision is; (2) reporting gaps are ignored; (3) 'decompose-then-forecast' hybrids report large gains that were never audited for look-ahead leakage.",
        "**Problem statement as a formula** (slide 6): choose the action (m, k) that maximises net revenue, and state a floor L such that the actual revenue falls below L on only about 10 percent of days.",
        "**Scope**: four crops (tomato, onion, potato, ginger) from the Agmarknet data only, evaluated offline on stored history. **Garlic is refused** because only one mandi has enough data, so there is no choice to make and advice would be meaningless.",
    ],
    numbers=[
        ("63,524", "real records after cleaning (each is one crop, one mandi, one day)."),
        ("36,821", "mandi-days in the panel after combining and aligning (garlic included here)."),
        ("Rs 100 to 9,330", "the full range of Kolar tomato modal prices in the data: the market is extremely volatile."),
        ("189 of 2,125", "days with no Kolar tomato price: about 9 percent."),
    ],
    why=["Why 'net revenue' and not 'price'? Because the farmer cannot spend the posted price; they keep what is left after fee, transport and spoilage, and nothing at all from a mandi that is silent."],
    limits=["One region (Bengaluru-Kolar), one source (Agmarknet), 5.8 years of data, offline evaluation. No farmer has acted on the advice."],
    ask=[
        ("Why only four crops?", "Garlic has one mandi with enough data, so no choice exists; we refuse rather than fake a recommendation. The other four have 3 to 12 eligible mandis."),
        ("Where does the 'information friction' claim come from?", "From the studies by Jensen (fisheries, South India) and Aker (grain markets, Niger), which show that price information changes what sellers earn. NOTE TO FIX BEFORE PRESENTING: the slide text cites [7], [8], but on the references slide those numbers are Jha and Sinha and Wu et al.; Jensen and Aker are [3] and [4]. Either change the slide to [3], [4] or be ready to say so. We cite these for motivation, not as proof of our own effect."),
    ],
))

SLIDES.append(dict(
    n=4, title="Objectives", one="Ten objectives, each with a clear status and the evidence for it: 7 met, 1 partly met, 1 null result, 1 built and tested.",
    plain=[
        "Each row is something we promised in the approved scope, whether we delivered it, and the number that proves it. The slide is honest on purpose: one objective is only partly met (floors), one gave a null result (spillover), and one was built and tested but never piloted with farmers (digest).",
    ],
    deeper=[
        "**Objective 1 (data):** at least 30,000 mandi-days; we have 36,821 from 63,524 records, with every exclusion recorded.",
        "**Objective 2 (model):** at least 500 held-out days per crop; we have 511 to 963 scored days per crop. 'Held-out' means days the model never trained on.",
        "**Objective 3 (labels and loss):** test two separate ideas, better labels (realised revenue) and a better loss (SPO+), with paired statistical tests. Result: labels cut regret by Rs 87 to 157 per quintal; the loss adds nothing reliable. That is a valid answer to the objective.",
        "**Objective 4 (floors):** floor violation within 2 points of the nominal 10 percent, meaning between 8 and 12 percent. Tomato 9.0 and ginger 10.5 meet it. Onion 6.3 and potato 6.9 are below 8, so the floors were more cautious than required. That is the safe direction but outside the stated band, hence 'partly met'.",
        "**Objective 5 (system):** FastAPI service, trilingual app, tests and a one-command pipeline: 669 backend tests, 11 web tests.",
        "**Objective 6 (audit):** measure look-ahead leakage in decompose-then-forecast models and include a foundation-model baseline. Skill drops from +27 to +62 percent to -15 to -1 percent when the decomposition is done causally.",
        "**Objective 7 (LLM briefs):** language model briefs that are grounded and verified; the judge caught 9 of 9 deliberately corrupted explanations; 30 unit tests.",
        "**Objective 8 (spillover):** estimate how a shock in one crop moves others with false-discovery-rate control. Null result: zero shock episodes were detected, so all 40 pair-direction edges were published as 'insufficient evidence'.",
        "**Objective 9 (inspectable advice):** five features (breakdown, what-if, track record, silence tax, crowd simulator). The parts of the breakdown add up to the net revenue exactly; the replay covers 165 days; 11 tests.",
        "**Objective 10 (digest):** a dated morning message in English, Kannada and Hindi on a free channel (Telegram). Built, tested and shown live, but no farmer pilot.",
    ],
    why=["We report the null result and the partial result in the same table as the successes. Hiding them would be easy to catch (the thesis contains them) and would damage trust in everything else."],
    ask=[
        ("Why is spillover a 'null result' and not a 'failure'?", "The engine worked as designed: it refuses to publish a number it cannot support. Zero episodes on the real data means no claim could be made. We also found why: the labelling stage did not mark any week as a squeeze or glut. That diagnosis is listed as future work."),
        ("What does 'partly met' mean for the floors?", "Two of four crops are inside the 8 to 12 percent band; the other two are lower (6.3 and 6.9), i.e. over-cautious. Over-cautious is safe for the farmer but outside the band we promised."),
    ],
))

SLIDES.append(dict(
    n=5, title="Proposed methodology and system architecture",
    one="Train on what the farmer would really receive, choose the best guaranteed revenue, and wrap it in a layered system.",
    plain=[
        "**The idea in one picture.** A usual model learns 'what will the price be at each mandi tomorrow'. Ours learns 'what will the farmer actually be left with if they go there'. The difference is large: a mandi that looks like Rs 2,100 on paper may be silent, may cost Rs 90 to reach, and tomatoes lose 3 percent per day of waiting.",
        "**The action** is a pair: (which mandi, how many days to wait, 0 to 3), or sell at the farm gate. For each pair we predict the net revenue, subtract a safety margin, and recommend the pair with the best **guaranteed** revenue. So the recommendation is not the highest hope but the best amount the farmer can count on.",
    ],
    deeper=[
        "**Why two approaches were rejected.** (1) Predict-then-optimise on posted prices: it never sees a silent market because silent days are missing rows, so it believes every mandi is always open. (2) Decompose-then-forecast hybrids: they split the price series into smooth parts using methods that look on both sides of each day, which quietly includes future prices (look-ahead). Both are discussed with numbers on slides 15 and 23.",
        "**The architecture, left to right.** Agmarknet exports are loaded, cleaned and audited (data layer). They become the market panel and an observation store (the 'facts'). Models then use these facts: market-choice engines with conformal floors, price forecasters and the specialist council, and the shock and spillover studies (model layer). A FastAPI service exposes them as typed web endpoints for the farmer pages, trader pages and chat (service layer). The language layer adds decision-intelligence briefs and an explanation writer checked by an independent judge. The Next.js web app in English, Kannada and Hindi is the presentation layer. The Telegram bot sends the 7 am digest by calling the same service.",
        "**The five insight features** (breakdown, what-if, track record, silence tax, crowd simulator) sit inside the service layer. None of them trains a model when a request arrives: they read the stored engine and data and compute on the fly.",
        "**'No synthetic data enter any result'** is a deliberate sentence. The first dataset we received turned out to be synthetic; we discarded it and re-collected real Agmarknet exports (risk R1 on slide 29). Test fixtures are small made-up arrays used only to check that code runs.",
    ],
    why=["Layering means each part can be tested and replaced alone. For example the language model can fail and the system falls back to rule-written text without breaking the app."],
    limits=["The architecture is proven offline on stored data. 'Live' use would need a refreshed data feed; we have none (the exports are downloaded by hand)."],
    ask=[
        ("Why not just forecast the price and pick the highest?", "Because the highest posted price may be a silent mandi, or a far one whose transport eats the gain. That is the 12 to 43 percent silent-market trips of observed-price models on slide 15."),
        ("Is the floor a forecast?", "No. It is a deliberately pessimistic number: the prediction minus a margin learned from the model's own past errors."),
    ],
))

SLIDES.append(dict(
    n=6, title="Key formulation: revenue, loss and verified floor",
    one="Three formulas: what the farmer keeps, how the model is scored, and how the floor is set and kept honest.",
    plain=[
        "**Formula 1, net revenue.** What a farmer keeps per quintal when they go to mandi m and wait k days: take the price, remove a 4 percent market fee, remove 3 percent (for tomato) of the produce for each day waited, subtract the cost of moving the load, subtract Rs 20 handling. If the mandi turns out to be silent, we assume the farmer still sells but at only 85 percent of that day's average price elsewhere, because a wasted trip leaves them with a weaker position. Farm gate is simple: 80 percent of the average, no transport.",
        "**Formula 2, the SPO+ loss.** A way of scoring a model by the harm of the decision it leads to. We tested whether it beats the usual squared-error score. It did not.",
        "**Formula 3, the floor.** Take the predicted revenue, subtract a margin q times a typical error size. The margin comes from past mistakes. The tolerance level alpha is nudged each day depending on whether the floor was broken, so the floor learns to stay at its promised hit rate.",
    ],
    deeper=[
        "**R(m,k | origin) = (1 - f)(1 - delta)^k times P~(m, t+k) - tau times rho times d(origin, m) - c0.** Read it from the left. (1 - f) keeps 96 percent after the 4 percent fee. (1 - delta)^k is the produce left after k days: at 3 percent a day, one day leaves 0.97, two days 0.9409, three days 0.9127. P~ is the price at mandi m on the sale day t+k (t is the day of decision). tau times rho times d is the transport: tau is rupees per quintal-km, rho = 1.3 turns straight-line distance into road distance, d is the distance. c0 = Rs 20 is a handling cost per trip.",
        "**P~ is P when the mandi reports, else phi times the day's average.** phi = 0.85 means a silent mandi leaves you with 85 percent of what the other mandis paid that day: you still sell (somewhere), but poorly. The slide notes that all these numbers are **scenario assumptions**, not measured quantities; transport, spoilage and phi are varied in a sensitivity sweep (10 settings per crop) and the conclusions hold across all of them.",
        "**SPO+ in a tiny example.** Two options, A and B. True revenues: A = 80, B = 95 (B is best). The model predicts A = 100, B = 90, so it recommends A (the wrong one) and loses 95 - 80 = 15 rupees (that is the regret). SPO+ computes max over actions of (2 x predicted - true) = max(2x100 - 80, 2x90 - 95) = max(120, 85) = 120; then subtracts 2 x predicted for the truly best action (2 x 90 = 180) and adds its true value (95): 120 - 180 + 95 = 35. 35 is at least the regret of 15, which is why the slide says SPO+ is an upper bound on regret, and it is zero when predictions are exactly right. The idea is that training on this number should prefer predictions that lead to good choices, even if the numbers themselves are less accurate.",
        "**Why the loss is 'exact' here.** Because revenue R is a straight-line (affine) function of the price vector, SPO+ is a precise surrogate for this problem; there is no approximation in that step.",
        "**Floor: L = r-hat minus q times sigma-hat.** r-hat is the predicted revenue of the chosen action, sigma-hat a recent measure of how big prediction errors are, q a multiplier. q is the (1 - alpha_t) quantile of past 'normalised scores' (past errors divided by their error scale) of recommended actions. If alpha_t is 0.10, q is the 90th percentile of past scores, so about 90 percent of past outcomes were above r-hat minus q times sigma-hat.",
        "**Adaptive update: alpha_{t+1} = alpha_t + gamma (alpha - 1[R < L]).** The bracket is the target miss rate alpha (0.10) minus an indicator that is 1 if revenue fell below the floor and 0 otherwise. Take gamma = 0.01. After a miss the update is alpha_t + 0.01 x (0.10 - 1) = alpha_t - 0.009, so alpha shrinks, q rises and the next floors are lower and safer. After a hit it is alpha_t + 0.001, so the floor creeps back up. Over many days, misses settle near the target rate (that is the theory behind adaptive conformal inference).",
        "**Delayed feedback.** A k-day hold only resolves k days later (you only know the real revenue when the sale day passes). The calibrator is therefore only allowed to use an outcome once its sale date is strictly in the past. Using it earlier would be another form of look-ahead. This is the novel adaptation: standard adaptive conformal inference assumes you see the outcome right away.",
        "**The table of defaults** (f 4 percent, c0 Rs 20, tau Rs 0.35 per quintal-km, rho 1.3, delta 3, 0.8 and 0.4 percent for tomato, onion and potato, phi 0.85, farm-gate 0.80, floor level 0.10, step 0.01) is the full set of assumptions behind every number on the results slides.",
    ],
    numbers=[
        ("0.97, 0.9409, 0.9127", "fraction of tomato left after 1, 2 and 3 days at 3 percent daily loss."),
        ("alpha 0.10, gamma 0.01", "target miss rate and the size of the daily nudge."),
    ],
    why=[
        "Why 4 hold options (0 to 3 days)? Longer waits are rarely sensible for perishables and also lengthen the delay before a floor can be checked.",
        "Why a conformal floor rather than a normal-distribution margin? A normal margin assumes errors are bell-shaped and stable; they are not. On slide 17 the naive Gaussian floor is broken on 26 to 35 percent of days against a 10 percent target in three crops.",
    ],
    limits=["tau, delta and phi are assumptions chosen to be realistic, not estimated from data. We say so on the slide and we test across 10 settings per crop."],
    ask=[
        ("What is the difference between regret and loss?", "Regret is the actual rupees lost against the best choice in hindsight. Loss is the number a model is trained to reduce. SPO+ is a loss designed to track regret."),
        ("Why 0.85 for silent mandis?", "It is an assumption: a wasted trip does not mean zero revenue but a weaker sale. We sweep it; models trained on realised outcomes keep winning in every setting."),
        ("Is it ACI or conformal?", "ACI (adaptive conformal inference) is a type of conformal prediction that adapts the level online. We adapted it to outcomes that arrive k days late."),
    ],
))

SLIDES.append(dict(
    n=7, title="Decision intelligence and cross-commodity spillover",
    one="Two research extensions: language-model briefs that are checked against evidence, and a test of whether crops move each other's prices.",
    plain=[
        "**Objective 7, grounded briefs.** The engines give numbers; a farmer wants a short recommendation with reasons. We let a language model write it, but not freely. It must fill a fixed form (action, confidence, reasons), every reason must name the evidence it relies on, and then a checking program verifies every number against the evidence. If anything fails, the brief is still shown but marked as 'not grounded' with the problems listed, and if the model service is down a rule-based writer takes over.",
        "**Objective 8, spillover.** Do the prices of tomato, onion, potato, ginger and garlic push each other? If an onion shortage makes potato rise, that would be useful to know. We built a careful test and it found no usable evidence, so the system says 'insufficient evidence' instead of printing a number.",
    ],
    deeper=[
        "**Evidence bundle.** A flat list of labelled facts, e.g. forecast.h5.point (the five-day forecast point), the market-choice result, arrivals, the spillover matrix, plus a list of things that were not available and why. Language-model text may only rely on these labels.",
        "**Fixed schema.** Action is one of BUY, SELL, HOLD, WAIT. Confidence is HIGH, MEDIUM, LOW or INSUFFICIENT_EVIDENCE. Every reason has a direction (supports, opposes, neutral) and an evidence key. A reason without a key is treated as invented.",
        "**The grounding check** has three rules. Every number in the text must match some evidence value within 1 percent (small whole numbers below 32 are ignored as ordinary words such as 'three days'). Every cited key must exist. The brief may only name mandis that appear in its own evidence. These catch the classic failure: a fluent but invented price.",
        "**Never fails silently.** If the language model provider errors, a deterministic provider writes the brief from rules. If a brief fails grounding it is served with grounded: false and the issue list. The service never crashes the request.",
        "**Policy override.** The brief's action follows the validated decision policy of the engines, and a HOLD is overridden when spoilage over the waiting period would outrun the expected price gain.",
        "**Spillover method, step by step.** (1) Take weekly returns (percentage price changes) of 5 crops at one reference market each, over 232 weeks (3 Jan 2021 to 1 Nov 2026). (2) Remove the first common factor (the part that moves all crops together, which explained 24.5 percent of variance) and the average of each calendar month (seasonality), so shared shocks and seasons are not mistaken for one crop causing another. (3) Define an episode: the source crop enters a squeeze (supply shortage) or glut (oversupply); onsets closer than 4 weeks are merged. (4) Effect at horizon h = 1 to 4 weeks is the average cumulative response of the target crop after episodes minus its usual average over the same horizon. (5) Uncertainty: resample whole episodes 2,000 times to get a 90 percent interval (whole episodes because weeks within one episode are dependent). (6) Because 40 directed pairs are tested at once, control the false discovery rate at 10 percent (Benjamini-Hochberg). (7) Publish an edge only if there are at least 8 episodes, its interval excludes zero and the effect exceeds 1 percent; otherwise publish INSUFFICIENT_EVIDENCE.",
    ],
    numbers=[
        ("232 weeks", "length of the weekly panel."),
        ("24.5 percent", "variance explained by the common factor, i.e. co-movement that would otherwise be misread as transmission."),
        ("40 edges", "5 source crops x 4 target crops x 2 shock types (squeeze, glut)."),
        ("at least 8 episodes", "the evidence floor; the real panel gave 0 in every case."),
    ],
    why=["Publishing 'insufficient evidence' is a feature. A number with a wide interval printed to two decimals looks authoritative to a farmer and is worse than silence."],
    limits=["Grounding proves a number is traceable, not that the recommendation is right; the recommendation itself comes from the engine. No user study of the briefs has been done."],
    ask=[
        ("Why zero episodes?", "The episode detector depends on supply-regime labels (squeeze or glut) built from arrivals; on the real weekly panel no week was labelled either. Whether the market was genuinely calm, the threshold too strict, or the labelling stage not fed from the real panel is unresolved and is in future work. A separate event study that defines shocks directly from arrivals did find some suggestive same-crop effects, so the data are not shock-free."),
        ("What stops the language model inventing prices?", "The grounding check: every number must match an evidence value within 1 percent, every cited key must exist, only mandis in the evidence may be named. A failing brief is shown as grounded false with its issues."),
    ],
))

SLIDES.append(dict(
    n=8, title="Insight features: method",
    one="Five calculations that make the advice inspectable: breakdown, what-if, track record, silence tax and crowd simulator.",
    plain=[
        "These five are what make a farmer or an examiner able to check the advice instead of just trusting it. **Breakdown**: where every rupee goes. **What-if**: change your costs and see if the advice changes. **Track record**: how the advice would have done on days it had not seen. **Silence tax**: what an unreliable mandi costs a trip. **Crowd simulator**: what happens to the price if many farmers follow the same advice.",
        "None of them trains a new model on request. They reuse the stored engine and data and show their assumptions with the answer.",
    ],
    deeper=[
        "**1. Breakdown.** R = P - f P - (1 - f) P [1 - (1 - delta)^k] - tau rho d - c0. This is the same net revenue formula written as separate parts: price, minus fee (f P), minus spoilage loss on the part left after the fee, minus transport, minus handling. The code asserts that the parts add up to the served net revenue within Rs 1, and it prints the same breakdown for three alternatives (nearest mandi today, highest price yesterday, farm gate) so that the farmer can compare line by line.",
        "**2. What-if (break-even cost).** x* = the smallest value x on a grid where the best action differs from the best action at the default cost x0. We re-price every action under the farmer's own costs (predicted prices and the chance a mandi reports do not depend on the farmer's costs, so this is exact, not a re-fit), sweep one cost across a grid (transport 0.1 to 3.0 Rs per quintal-km; spoilage 0 to 8 percent a day) and report where the best action flips. A flip point is what a farmer understands: 'the advice changes once spoilage passes 5 percent a day'.",
        "**3. Track record.** The walk-forward back-test is replayed day by day. A multiplier for the floor is fitted on the first half of the scored days, and only the second half is reported, so every day in the table is one the floor was not fitted on. Each day: win if the advice beats the comparison by more than Rs 1, tie if within Rs 1, loss if worse by more than Rs 1. Floor 'held' means actual revenue was at least the floor.",
        "**4. Silence tax.** T_m = s_m x max(P_m - phi x P_day, 0). s_m is the share of the mandi's open days on which it was unexpectedly silent. P_m is the mandi's typical price when it reports, P_day the average price across mandis that day, phi = 0.85. The max term is how much better this mandi's usual price is than the fallback you would get if it were silent; multiplying by how often it is silent gives the expected rupees lost per quintal on a trip. **Known closed days**: a weekday on which the mandi is silent on at least 90 percent of occasions is treated as a closed day farmers already know about, and excluded.",
        "**5. Crowd simulator.** P_m(x) = P_m x (1 + x / A_m)^(-b). A_m is the mandi's usual daily arrivals (median over the last year), x the extra quintals arriving, b the price flexibility. Example: A = 68 quintals, 200 farmers x 10 quintals = 2,000 quintals: (1 + 2000/68)^(-0.115) = 30.4^(-0.115) = about 0.675, a 32.5 percent drop. This matches the slide. Three policies are compared for N farmers: all take the best action, all go to the nearest mandi, and a coordinated split that hands out the quantity in small steps, each to the action with the best marginal revenue.",
        "**b = 0.115** is the within-mandi, within-month association of log price with log arrivals in the tomato panel (standard error 0.023). It is an association, not a cause. So it is treated as a scenario that the user can change, and when b = 0 the crowd costs nothing and every policy is equal.",
    ],
    why=["Each feature answers an examiner's natural challenge: 'show me the arithmetic' (breakdown), 'what if my costs are different' (what-if), 'has it actually worked' (track record), 'what about unreliable mandis' (silence tax), 'what if everybody follows you' (crowd)."],
    limits=["The floor is only calibrated at default costs; with very different costs it is indicative and the screen says so. Silence is ambiguous (closed or missed upload). b is an association, not a measurement."],
    ask=[
        ("Is the what-if a new model run?", "No. Predicted prices and the chance a mandi reports do not depend on the farmer's costs, so every action can be re-priced exactly with the new costs; it is arithmetic on stored predictions."),
        ("Why 'tie within Rs 1'?", "So that identical actions that differ by rounding are not counted as wins or losses."),
    ],
))

SLIDES.append(dict(
    n=9, title="Implementation and system integration",
    one="How the parts were joined into one reproducible system, and what broke along the way.",
    plain=[
        "A single command (scripts/pipeline.py) runs 13 stages in order, from raw exports to final tests. Each stage declares the files it must produce, so a stage can be run alone, skipped or dry-run. The API, web app, engines and language layer share one data store, which is why the numbers on the farmer's screen are the same as the numbers in the thesis tables.",
        "**What is manual:** refreshing the Agmarknet exports (we download them by hand) and verifying a public deployment (config files exist but we have not verified it live).",
    ],
    deeper=[
        "**The stages** (from the diagram): world (data), forecasts, market choice, track record, transmission, shock, spillover, council, research evidence, results document, tests. Each has declared outputs, so the pipeline can tell whether a stage ran successfully.",
        "**Pipeline switches:** --list shows stages, --only runs one, --skip skips one, --dry-run prints what would run without running it.",
        "**Endpoints:** /v1/market-choice (plus 5 insight routes), /v1/farmer, /v1/trader, /v1/shock, /v1/council, /v1/spillover, /v1/intelligence, /v1/chat and /v1/notify (the digest). 'v1' means version 1 of the interface.",
        "**Four defects that were found and fixed**, each with a lesson: (1) NumPy 2 broke pandas: libraries were pinned (NumPy 1.26.4) and a lock file added. (2) A fresh clone missed the observation store: the clone check was added. (3) Hard deletion emptied trader pages: replaced by soft delete and re-seeding. (4) Council weights summed above 1: constrained to at most 1.",
    ],
    why=["One command and declared outputs mean anyone can regenerate every table in the thesis from raw data. This is the reproducibility the course asks for."],
    limits=["Public deployment is not verified; the Telegram digest runs from a laptop."],
    ask=[("What does 'one data store' buy you?", "No copies drifting apart. The app, API and thesis read the same stored results, so a number cannot differ between the screen and the report.")],
))

SLIDES.append(dict(
    n=10, title="What you will see: five features and a digest",
    one="A map of the demo: six items, each tied to a screen and an address.",
    plain=[
        "This slide is the contents page of the demo. Each item is a screen in the farmer app or the trader desk, plus the Telegram bot. It tells the audience what to look for so that the next two slides (the run-of-show) make sense.",
    ],
    deeper=[
        "**1 Why this mandi** (route /breakdown): the arithmetic of the advice per quintal. **2 What if my costs differ** (/simulate): sliders for transport, spoilage and longest wait. **3 Has this advice worked** (/track-record): replay on 165 days it had not seen. **4 Silence tax** (trader desk /reporting-value). **5 Crowd simulator** (trader desk /crowd). **6 Daily digest** (Telegram, /v1/notify).",
        "The first three are farmer-facing; the next two are trader-facing; the digest is the delivery channel for the farmer.",
    ],
    ask=[("Why are features 4 and 5 on the trader desk and not on the farmer app?", "Silence tax and the crowd effect are about the market as a whole and are most useful to someone who handles volumes or advises groups. The farmer sees their results through the advice itself.")],
))
