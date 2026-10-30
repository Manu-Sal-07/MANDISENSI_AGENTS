"""Deep-dive guide content, part 3: slides 23-35 and the appendices."""

SLIDES = []

SLIDES.append(dict(
    n=23, title="Look-ahead audit of decompose-then-forecast models",
    one="A popular family of forecasting models looks very good only because it peeks at the future; remove the peek and the advantage disappears.",
    plain=[
        "Many recent papers on agricultural price forecasting first split the price line into smooth parts (a slow trend, a seasonal wave, fast wiggles), forecast each part, and add the forecasts back. They report big improvements. We asked: **is the splitting step done fairly?**",
        "**The problem in one image.** Imagine smoothing a price line with a centred moving average: the smooth value for Tuesday uses Monday, Tuesday and Wednesday. If you do this once on the whole history and then 'forecast' Wednesday, the Wednesday information is already inside Tuesday's component. The model is, in effect, told part of the answer.",
    ],
    deeper=[
        "**STL and VMD are two-sided.** STL (seasonal-trend decomposition using loess) fits local curves through points on both sides of each day. VMD (variational mode decomposition) solves one optimisation over the entire series to find modes, so every mode at day t depends on the whole series including its future. ICEEMDAN works in a similar whole-series way. That is what 'two-sided smoother' means on the slide.",
        "**Published protocol.** Decompose the whole series once, split the components into training and test periods, forecast each component, add them up, and score on the test period. The test-period components were built with the future data inside the process.",
        "**Causal protocol.** At each forecast origin, decompose only the data available up to that day, forecast, and move on. This is slower but honest: nothing from the future can enter.",
        "**Skill.** Improvement over the random-walk forecast ('tomorrow = today'). +27 percent means the error is 27 percent lower than the random walk's; -15 percent means it is 15 percent worse.",
        "**Result for tomato.** Published protocol: +27 to +62 percent skill. Causal protocol: -15 to -1 percent for the same models. The raw series without any decomposition scores -14 to -1.5 percent. So with leakage removed the decomposition adds nothing. The gap between published and causal is 30 to 71 points with confidence intervals that exclude zero: that gap is the size of the leak.",
        "**Foundation-model baseline.** Chronos-Bolt is a pretrained time-series model used zero-shot (no training on our data). It scores -9.4 percent at one day, worse than 'no change'. So **no model in this comparison beats the random walk on the daily tomato series**. This is a sobering and honest finding: short-term daily forecasting of this series is not where the value lies, which is why we decided to optimise the decision instead.",
    ],
    numbers=[
        ("+27 to +62 percent", "skill reported when the decomposition is done once over the whole series."),
        ("-15 to -1 percent", "skill of the same models when decomposition is done only on data available at each forecast day."),
        ("30 to 71 points", "size of the leak (published minus causal)."),
        ("-9.4 percent", "Chronos-Bolt zero-shot at one day."),
    ],
    why=["This is objective 6 and a novelty claim: we measured how large the look-ahead leak is. Nobody had quantified it for agricultural decomposition hybrids."],
    limits=["We did not audit the specific published papers; the claim is about the protocol they describe. Tomato only, one series, daily."],
    ask=[
        ("Are you saying the published papers are wrong?", "No. We say that the protocol they describe (decompose the full series once) leaks future information, and we measured how much on our data. Their numbers may well be what they report under that protocol; they are not what a farmer would get in real use."),
        ("Why does a better-looking forecast not matter for your goal?", "Because even honest forecasts barely beat 'no change' at the daily level. The valuable thing is choosing between mandis, which is a decision problem, and that is where training on realised revenue helps."),
    ],
))

SLIDES.append(dict(
    n=24, title="Council, shocks, spillover and language layer",
    one="Five side studies, each reported with its verdict, three of which are honest negatives.",
    plain=[
        "A table of five studies we ran beyond the main model. The right-hand column says what we did with each result: promoted, served, withheld or not promoted. This is the place where we show that we do not publish anything the data cannot support.",
    ],
    deeper=[
        "**Specialist council (not promoted).** Four agents, each looking at one family of features (for example trend, seasonality), whose forecasts are combined with learned weights that must sum to at most 1. Result: council skill +0.2 to +0.4 percent against +0.6 to +0.8 percent for a single model, and the council beat the single model in only 0 to 1 of 4 folds. An earlier version with unconstrained weights (sums of 2.4 to 3.1) was significantly worse. So it was not promoted and is kept as an inspectable diagnostic.",
        "**Supply-shock event study (not served).** Question: do big surges in arrivals move prices over 3, 7 and 14 days? We tested 30 crop-horizon combinations, compared with placebo circular shifts (shifting the shock series in time to see what pure chance looks like), and corrected with Holm. None was robust; 5 were suggestive, but the smallest effect we could detect (minimum detectable effect) was as large as the estimate, so power was marginal. The shock page labels the evidence tier.",
        "**Cross-commodity spillover (withheld).** 5 crops, 40 directed edges, false discovery rate 10 percent, at least 8 episodes needed. Result: 0 shock episodes in all 10 source cells, so 40 of 40 edges are 'insufficient evidence'. This is also a finding about the pipeline: the detector relies on supply-regime labels (squeeze or glut) derived from arrivals, and no week of the real panel was labelled either. Whether the market was calm, the threshold too strict, or labelling not fed from the real panel is unresolved (future work).",
        "**District forecasts (served for 3, 5 and 7 days).** Forecast of the district modal price compared with 'no change', with a 90 percent band. Skill +3.0 to +4.0 percent, direction correct on 60 to 62 percent of occasions, band coverage 89.8 percent (target 90). The bands are wide (62 to 75 percent of the price), the price of honest uncertainty. The 1-day horizon was not served: its skill (0.2 percent) is not distinguishable from no change.",
        "**Explanation layer (verified, small sample).** 24 explanations (120 sentences) in English, Kannada and Hindi (8 per language) written by gpt-oss-120b and judged by a Qwen model. No sentence failed the number validator. The judge rejected 2 of 40 English, 9 of 40 Kannada and 7 of 40 Hindi sentences (these fall back to the original rule-written text). The share kept from the model: English 0.83 to 0.99, Kannada 0.62 to 0.88, Hindi 0.68 to 0.91. To test the judge itself, 9 deliberately corrupted explanations (reversed meaning, an added claim, a dropped qualifier, a wrong meaning) and 3 faithful ones were presented: it caught 9 of 9 and falsely rejected 0 of 3. The sample is small, so this shows the judge is not blind rather than that it is reliable.",
    ],
    numbers=[
        ("0 of 40", "spillover edges with enough evidence."),
        ("89.8 percent", "coverage of the 90 percent district bands: nearly exact."),
        ("9 of 9, 0 of 3", "corrupted explanations caught, faithful ones wrongly rejected."),
    ],
    limits=["Small n for the language layer; Kannada and Hindi weaker than English; no native-speaker review yet (future work)."],
    ask=[
        ("Why report things that did not work?", "Because the thesis claims only what survived testing. Showing negatives also protects the positives: it proves we did not simply keep what looked good."),
        ("What is a placebo shift?", "We move the shock dates by a random amount and re-run the test; if real shocks show effects no larger than these fake ones, the effects are not credible."),
        ("What is minimum detectable effect?", "The smallest effect the data could reliably detect. If it is as large as the estimate, a real effect of that size could not be told from noise."),
    ],
))

SLIDES.append(dict(
    n=25, title="Comparative benchmarking",
    one="All methods compared under identical conditions: ours wins in every crop against every simple rule and every observed-price model, except where stated.",
    plain=[
        "No other published study scores mandi choice by regret on real data with reporting gaps, so we cannot compare against another paper's number. Instead we compare against what farmers really do (nearest mandi, highest price yesterday, best seven-day mean, farm gate) and against the standard predict-then-optimise models, all retrained on the same split with the same tuning budget.",
    ],
    deeper=[
        "**Each cell shows two numbers: gap closed / share of recommendations that went to a silent market.** Gap closed: 0 = no better than nearest mandi, 1 = as good as the oracle. Silent share: lower is better.",
        "**Tomato row by row.** Nearest mandi: 0.00 and 34 percent silent: the baseline and a third of trips wasted. Highest price yesterday: 0.43 / 28 percent. LightGBM on observed prices: 0.43 / 29 percent, no better than the simple rule. LightGBM on realised outcomes (ours): 0.57 / 12 percent. Neural SPO+ on realised outcomes (ours): 0.58 / 12 percent.",
        "**Onion:** 0.00 / 34; 0.26 / 43; 0.24 / 43; 0.48 / 18; 0.50 / 20. **Potato:** 0.00 / 34; 0.17 / 35; 0.12 / 34; 0.31 / 21; 0.28 / 17. **Ginger:** 0.00 / 24; 0.69 / 11; 0.69 / 12; 0.76 / 5; 0.76 / 5.",
        "**Where we win:** all four crops against every heuristic and every observed-price model.",
        "**Where we do not:** the potato back-test gain over the best heuristic is not distinguishable from zero (interval includes zero); and the neural SPO+ model ties the same learner trained with squared error (no loss effect). Note also that for ginger the highest-price-yesterday rule is already strong (0.69), so our improvement there is small in the table (0.76) even though the back-test gain is large in rupees.",
        "**How to read the pattern.** Observed-price models look like the simple rules because both only react to posted prices. Switching the labels to realised revenue is what separates the groups.",
    ],
    why=["Same split, same metric, all retrained, and a model trained on the same realised labels, so that 'better label' and 'better learner' are not confused."],
    limits=["Comparison is against heuristics and standard baselines, not against another published mandi-choice system, because none exists with this protocol."],
    ask=[
        ("Why is there no comparison with other papers?", "Because their metrics (RMSE of price) answer a different question. We included the closest equivalent we could build: a standard predict-then-optimise baseline, plus the leakage audit of published protocols."),
        ("Why is ginger's gap closed so high for everyone?", "Ginger prices differ a lot between mandis and are slower-moving, so even the simple rule catches much of the oracle gain."),
    ],
))

SLIDES.append(dict(
    n=26, title="Novelty and research contribution",
    one="What already existed, what is new, and what we adapted from others.",
    plain=[
        "**Already exists:** forecasters of agricultural prices, SPO+ and decision-focused learning, adaptive conformal inference. We cite these. **New here:** four things. **Adapted:** we reused SPO+, ACI, DeepSets, Optuna and Chronos.",
    ],
    deeper=[
        "**New 1. Revenue labels that include silent markets, on real mandi data.** The label is realised net revenue including the fallback when a mandi is silent, so the model learns reliability.",
        "**New 2. Floors for selected actions whose outcome resolves k days later.** Standard adaptive conformal inference assumes the outcome is seen immediately, and for a fixed prediction. Here the action is chosen by the model, and the outcome is known only after the hold period. The calibrator only receives an outcome once its sale date has passed.",
        "**New 3. A measurement of how large the look-ahead leakage is** in STL and VMD hybrids (30 to 71 points on tomato).",
        "**New 4. Verified language briefs and a withheld-by-default spillover engine.** Briefs whose every number is checked against evidence; spillover results published only when they pass strict gates.",
        "**Ours versus adapted.** Ours: the formulation, the pipeline, the leakage protocol, the grounding verifier, the engines and the app. Adapted: SPO+ (Elmachtoub and Grigas), adaptive conformal inference (Gibbs and Candes), DeepSets (Zaheer et al.), Optuna (Akiba et al.), Chronos (Ansari et al.). Using them is normal practice; claiming them would not be.",
        "**The honest scope line.** What survived testing as a positive contribution: the label effect, the floor validity and the audit. The loss, reporting head, silence features, council and spillover are bounded negative results (we know where they do not help).",
    ],
    ask=[
        ("What is your single novelty?", "Training market choice on realised, silence-aware revenue and certifying it with delayed-feedback conformal floors; plus measuring the leakage in published decomposition hybrids."),
        ("Is a negative result a contribution?", "Yes, when it is pre-specified and well tested: it tells others where not to spend effort. We kept them separate from the positive claims."),
    ],
))

SLIDES.append(dict(
    n=27, title="Optimisation and ablation study",
    one="Which parts of the model genuinely matter: changing one thing at a time shows that only the labels do.",
    plain=[
        "An **ablation** is a controlled experiment: change one component, keep everything else the same, and measure the change in regret. If a component is truly useful, removing or adding it should move the result reliably. We tried several clever components; most did not.",
        "**Tuning.** Settings of each method were chosen by Optuna's TPE search, per fold, on that method's native criterion, with the same trial budget for all. Tuning the most complete model on forecast loss instead of decision regret made no reliable difference.",
    ],
    deeper=[
        "**Row 1. SPO+ loss instead of squared error: -25 [-53, +3], Holm p 0.505.** Regret fell by Rs 25 on average, but the interval includes zero and the adjusted p-value is 0.5: no reliable difference.",
        "**Row 2. Add a reporting head (with SPO+): +23 [+8, +36], p 0.012: worse.** A reporting head is an extra output of the neural network that predicts whether each mandi will report on the sale day. It seemed natural: modelling the silence directly. In practice it made decisions worse by Rs 23 per quintal (interval entirely above zero; remember positive regret change means worse). A pre-specified hypothesis that failed.",
        "**Row 3. Add network-silence features (GBM): -12 [-31, +3], p 0.695.** Features telling the model whether neighbouring markets were silent. No reliable help.",
        "**Also tried and did not work:** decision-regret tuning instead of forecast-loss tuning; unconstrained council weights (summed 2.4 to 3.1, significantly worse); SPO+ over squared error.",
        "**Cost decision.** The served model is the boosted tree rather than the neural network: equal decisions, far cheaper to train, run and explain.",
        "**The ablations are shown for tomato, and the other crops agree.**",
    ],
    why=["Reporting failed ablations is evidence of discipline. It also directs future work: the next gains are unlikely to come from the loss or more silence modelling, but from better data (more regions, longer history, real transport and spoilage estimates)."],
    limits=["Single crop shown on slide; the thesis table lists all ablations."],
    ask=[
        ("Positive p = worse. How do you read the sign?", "Delta regret is the change in regret; negative means regret fell, i.e. better. +23 means regret rose by Rs 23, i.e. worse."),
        ("Why did the reporting head hurt?", "A plausible reason: asking one network to learn two jobs with limited data adds noise to the revenue head. We did not prove the cause; we report the measured effect."),
    ],
))

SLIDES.append(dict(
    n=28, title="Project planning: WBS and critical path",
    one="How 970 hours of work were broken down, who owned what, and which chain of tasks fixed the finish date.",
    plain=[
        "A **work breakdown structure (WBS)** splits the project into packages: management and documentation 130 h (Shreejith), data 100 h (Manohara), models and research 290 h (Manohara), application 360 h (Srijan), verification 90 h (Shreejith and Manohara). Total 970 hours. These are team estimates, not logged time. Each leaf task has one owner and child hours add up to the parent.",
        "The **critical path** is the longest chain of tasks that must happen one after another. It decides the earliest finish. Ours is Requirements, Data, Market choice, Forecasters, Experiments, Testing, Integration, Report: A to B to C to F to G to I to J to K, taking 2 + 3 + 4 + 3 + 4 + 3 + 2 + 3 = 24 weeks.",
    ],
    deeper=[
        "**Not on the critical path** are Backend API (D, 4 weeks), Web app (E, 5 weeks) and LLM layer (H, 3 weeks). They have slack: they can slip without delaying the project, up to a limit.",
        "**How slack is worked out** (the 'worked slack' box). Forward pass gives the earliest start (ES) of each task; backward pass gives the latest start (LS) that does not delay the end. Slack = LS - ES.",
        "**Activity E (web app).** Testing (I) must start at week 16 (A 2 + B 3 + C 4 + F 3 + G 4 = 16), so E must finish by week 16: LF(E) = LS(I) = 16. E takes 5 weeks: LS(E) = 16 - 5 = 11. E can start at the earliest in week 6 (after D, which follows requirements: A 2 + D 4 = 6): ES(E) = 6. Slack = 11 - 6 = 5 weeks.",
        "**Activity H (LLM layer).** LS(H) = 16 - 3 = 13; ES(H) = 6; slack = 7 weeks.",
        "**Activity D (backend).** It must finish before both E and H can start, so its latest finish is the smaller of their latest starts: LF(D) = min(LS(E), LS(H)) = min(11, 13) = 11. LS(D) = 11 - 4 = 7; ES(D) = 2 (after A); slack = 7 - 2 = 5 weeks.",
        "**RAM (responsibility assignment matrix).** Each work package has one primary owner who is Responsible and the guide is Accountable. Hours by person: Manohara 430 h, Srijan 360 h, Shreejith 180 h.",
    ],
    numbers=[
        ("970 h", "total estimated effort across five packages."),
        ("24 weeks", "critical path length (2+3+4+3+4+3+2+3)."),
        ("Slack: E 5, H 7, D 5 weeks", "how much the three off-path tasks could slip."),
    ],
    limits=["Hours are estimates, not time logs; the baseline schedule was reconstructed from the roadmap after the fact, which the thesis states."],
    ask=[
        ("Why does critical path matter?", "Any delay on those tasks delays the whole project week for week; off-path tasks can absorb delays up to their slack. That is why the backend and web app delays on slide 29 did not move the end date."),
        ("Why is Manohara's load the largest?", "Models and research (290 h) and data (100 h) are the heaviest packages and belong to Manohara."),
    ],
))

SLIDES.append(dict(
    n=29, title="Schedule tracking and risk management",
    one="Planned 24 weeks, took about 27, because the data had to be redone; the risk register shows what happened and what is still open.",
    plain=[
        "The chart shows two bars per activity: the baseline (planned) and the actual. The project overran by about 3.3 weeks (14 percent). The cause: **Data (B) was reopened** after we discovered the first dataset was synthetic. That pushed Market choice (C) and Experiments (G), which are on the critical path, while Backend, Web app and LLM layer (not on the path) used their slack to absorb the delay.",
    ],
    deeper=[
        "**Milestones.** M1 requirements (week 3), M2 first deployed prototype (9 June), M3 farmer feature suite (30 September), M4 research results (29 October), M5 final report (week 27).",
        "**Risk score P x I.** Probability times impact, each on a 1 to 5 scale, so the maximum is 25. Higher means attend to it first.",
        "**R1 Source data synthetic (15), occurred.** Trigger: results that looked too clean. Action: discard, re-acquire the Agmarknet exports, add an integrity check, remove synthetic data, re-run every experiment. This is why the thesis states that no synthetic data enter any result.",
        "**R2 Look-ahead leakage (20), occurred.** Leakage unit tests caught two features centred on the whole series; fixed. The same discipline led to the leakage audit.",
        "**R3 Hard deletion broke trader pages (9), occurred.** Fixed with soft delete, re-seeding and id aliasing.",
        "**R4 NumPy 2 broke pandas (9), occurred.** Pinned NumPy 1.26.4 and a lock file.",
        "**R5 LLM rate limit of about 8,000 tokens a minute (8), occurred.** Throttling and a small evaluation set (which is why the language evaluation is small).",
        "**R6 Uneven team contribution (12), open.** Contribution record and owner split.",
        "**R7 Deployment unverified (9), open.** Docker and Render files exist; to verify.",
        "**R8 No field trial (12), open.** Stated as a limitation; the survey is ready.",
        "**R10 Stale server served old code (6), occurred.** Restart; the smoke test lists every endpoint.",
    ],
    numbers=[("+3.3 weeks, 14 percent", "24 planned versus about 27 actual.")],
    why=["Showing materialised risks and what we did about them demonstrates risk management in practice, not just a table."],
    ask=[
        ("Why was the data risk so costly?", "Because everything downstream (labels, models, tests) depends on it. When the dataset was found to be synthetic, the experiments had to be rebuilt."),
        ("Why are only some risks 'occurred'?", "Because the register is honest: those risks really happened; the others are still open at the time of review."),
    ],
))

SLIDES.append(dict(
    n=30, title="Project report and documentation status",
    one="State of the thesis and appendices, and what remains.",
    plain=[
        "The report follows the BMSCE thesis template, compiled in LaTeX. Every table is generated by scripts from the experiment results, so there are no hand-typed numbers. Appendices: A code excerpts read from the source files, B survey instrument, C per-fold evaluation, D dataset description, E programme outcome (PO) and SDG mapping, F similarity record.",
        "**Remaining:** the official Drillbit plagiarism report (similarity target below 20 percent, references excluded), the CO to PO matrix from the course file, the declaration date and supervisor corrections.",
    ],
    deeper=[
        "**Why generated tables matter.** If a number in the report differs from the app, either could be wrong; generating both from the same artefacts removes that risk.",
        "**Similarity.** We have not run Drillbit yet, so we claim no percentage. A self-check of the conference draft found no verbatim web matches, which is not a substitute.",
    ],
    limits=["**UPDATE BEFORE PRESENTING.** The slide says 83 pages and 40 references. After the guide's feedback the thesis now has about 113 to 120 pages, a much larger literature review (25 surveyed studies in comparison tables) and 63 references. Change the slide text to the current numbers, or be ready to say 'the thesis has since grown to about 113 pages with 63 references'. Check the current page count in the PDF before the review."],
    ask=[("Is the report plagiarism-checked?", "The official Drillbit check is pending; we will include the report in Appendix F. We do not claim a percentage until then.")],
))

SLIDES.append(dict(
    n=31, title="SDG mapping and societal impact",
    one="Which UN goals the work supports, how strongly, and what is only a potential.",
    plain=[
        "**Stakeholders.** Smallholder farmers need a plain answer and a floor. Traders need evidence tiers and arrivals. Mandi officials and policymakers need transparent data use.",
        "The status column is the honest part: 'Measured offline', 'Not measured', 'Potential', 'Engineering'. We claim impact only where held-out numbers support it.",
    ],
    deeper=[
        "**SDG 2, target 2.3 (income of small-scale producers through market information): measured offline.** Back-test gains of Rs 60 to 202 per quintal over the best simple rule in three of four crops. The morning digest is on a free channel but untested with farmers.",
        "**SDG 1, target 1.4 (access to economic services): not measured.** A free, trilingual tool for small sellers; we have not measured access or use.",
        "**SDG 12, target 12.3 (reduce food loss along supply chains): potential.** Spoilage is built into the advice, so waiting and distance trade-offs are priced; we have not measured kilograms avoided.",
        "**SDG 9, target 9.c (access to information technology): engineering.** An open pipeline on a public data feed.",
        "The benefit to real farmer income needs a field trial, which this project did not conduct.",
    ],
    ask=[("Do you claim you increased farmers' income?", "No. We show that, offline, the advice would have earned Rs 60 to 202 more per quintal than the best simple rule in three of four crops. Real income effects need a field trial.")],
))

SLIDES.append(dict(
    n=32, title="Research paper status",
    one="Two manuscripts and a proposal are drafted; none has been submitted yet.",
    plain=[
        "We say clearly that nothing is submitted. The primary target is IEEE Access (broad applied engineering, accepts long empirical papers with negative results). The second is the CICPS 2027 conference (Springer LNNS). The third item is the KSCST SPP 50th series project proposal.",
    ],
    deeper=[
        "**Manuscript 1:** Where and When to Sell: Outcome-Supervised Market Choice with Conformal Revenue Floors, and a Look-Ahead Audit of Decomposition Forecasters. IEEE Access, 14 pages, drafted.",
        "**Manuscript 2:** Fusing Specialist Agents and Market Signals into Calibrated Price Ranges: A Pre-Registered Evaluation on Indian Agricultural Mandis. CICPS 2027, 12 pages, drafted.",
        "**Proposal:** MandiSense project proposal for the KSCST Student Project Programme, 14 pages, drafted.",
        "**Similarity:** only a self-check exists for the conference draft; official Drillbit percentages will be added at submission.",
    ],
    ask=[("Why IEEE Access?", "It publishes long empirical work and accepts negative results; our contribution includes several.")],
))

SLIDES.append(dict(
    n=33, title="Conclusion and future work",
    one="What we achieved, what limits it, and the next steps that follow directly from the limits.",
    plain=[
        "**Key outcome:** advice trained on realised revenue beats the best simple rule by Rs 170 per quintal for tomato and Rs 202 for ginger, with floors that hold close to their level. Against the objectives: 7 met, 1 partly met, 1 null result and 1 built and tested; negative results are reported.",
    ],
    deeper=[
        "**Limitations.** One region, one source, 5.8 years. Offline only: no farmer acted on the advice and the digest was not piloted. Revenue and crowd parameters are scenarios, and replayed floors held 84 to 92 percent (aim 90). Briefs are checked for traceability, not user-tested. Spillover found no episodes; deployment unverified.",
        "**Future work, each from a limit.** (1) A field pilot through the bot with an outcome form and the survey. (2) Estimate transport, spoilage and silence from data instead of assuming them. (3) Diagnose the spillover labelling and define episodes from arrivals. (4) User test of briefs and a native-speaker review of Kannada and Hindi. (5) Verify deployment and monitor live floor violations.",
        "**How to close.** 'The main result is simple: teach the model what the farmer actually keeps, and say how sure you are. It worked, and we measured exactly where it does not.'",
    ],
    ask=[("What would you do first with more time?", "A small field pilot: the bot with an outcome form, so we measure real farmer decisions and real floor violations, the two things offline evaluation cannot give.")],
))

SLIDES.append(dict(
    n=34, title="References", one="Numbered references used on the slides; the full list is in the thesis.",
    plain=["The slide lists 34 numbered entries. The thesis bibliography is larger (63 entries after the literature review was expanded and 25 studies were surveyed in tables)."],
    deeper=[
        "**How they map to the talk.** [1]-[8] motivation and forecasting studies; [9]-[16] decomposition and evaluation (STL, VMD, Bergmeir, Cerqueira); [17], [18] Chronos and the foundation-model study; [19] trees on tabular data; [20] Optuna; [21], [22] SPO+ and decision-focused learning; [23] XGBoost and LightGBM; [24]-[27] statistical tests (Diebold-Mariano, Newey-West, model confidence set); [28] conformal prediction; [26] adaptive conformal inference; [29] DeepSets; [30]-[31] Holm and block bootstrap; [32] conformalised quantile regression; [33]-[34] missing data.",
        "**Known mismatches to check before presenting.** Slide 3 cites [7], [8] for information frictions; those numbers are Jha and Wu on the references slide, while Jensen and Aker are [3] and [4]. Slide 26 cites ACI as [26] and conformal prediction as [25]-[28]; the references slide gives [25] as Newey-West and [26] as Gibbs-Candes. Align the numbers in the slide text with this list or be ready to explain.",
    ],
    ask=[("Where is the full list?", "In the thesis bibliography, with 63 entries, each matched to a published record.")],
))

SLIDES.append(dict(n=35, title="Thank you", one="Close and invite questions.",
    plain=["End on the one-sentence result and offer to return to any demo screen. Keep this guide's 'If asked' answers and Appendix D (question bank) at hand."],
    deeper=[], ask=[]))

APPX = {
    "formulas": [
        ("Net revenue", "R(m,k) = (1 - f)(1 - delta)^k x P~ - tau x rho x d - c0", "What you keep per quintal: price after fee, after spoilage over k days, minus transport and handling. P~ is the posted price if the mandi reported, else 0.85 of the day's average."),
        ("Regret", "oracle revenue - method revenue", "Rupees lost against the best hindsight choice."),
        ("Gap closed", "(method - nearest) / (oracle - nearest)", "0 = as bad as nearest mandi; 1 = oracle."),
        ("SPO+ loss", "max_a (2 r-hat_a - r_a) - 2 r-hat_a* + r_a*", "Penalises the harm of the decision a prediction leads to; an upper bound on regret, zero at the truth."),
        ("Floor", "L = r-hat - q x sigma-hat", "Predicted revenue minus a learned margin: the amount we say you can count on."),
        ("Adaptive level", "alpha_{t+1} = alpha_t + gamma (alpha - 1[R < L])", "After a miss alpha falls by 0.009 (floors get safer); after a hit it rises by 0.001."),
        ("Silence tax", "T = s x max(P_m - 0.85 x P_day, 0)", "Expected rupees lost per quintal to surprise silence."),
        ("Crowd price", "P(x) = P x (1 + x/A)^(-b)", "Price after x extra quintals arrive; A usual arrivals, b flexibility."),
        ("Spillover effect", "mean over episodes of cumulative target return over h weeks, minus baseline", "Response of a crop after another crop's shock."),
        ("Skill", "1 - error of model / error of random walk", "Positive is better than 'tomorrow = today'."),
    ],
    "traps": [
        ("Floor 9.0 percent violated (slide 17) versus floor held 84 percent (slide 19)", "Different evaluations. Slide 17: five outer walk-forward blocks with the adaptive rule (violation 9.0 percent for tomato). Slide 19: replay of the served engine on 165 days with one multiplier fitted on half of the window and frozen, the strictest view (16 percent violated, 84 percent held). Say: the floors are close to, not exactly at, their level, and slide 19 is the harshest test."),
        ("Gap closed 0.57 (slide 25) versus 62 percent (slide 17)", "Different windows and models: research evaluation over 963 test days versus the served engine over the last 330 days."),
        ("63,524 records versus 36,821 mandi-days", "Records are the cleaned rows from the exports; mandi-days are the cells of the aligned panel (one per mandi per crop per day) after combining the two export types and removing duplicates."),
        ("+27 to +62 percent skill versus our claim that nothing beats the random walk", "The +27 to +62 are what the published protocol reports; under the causal protocol the same models score -15 to -1 percent."),
        ("Potato: strong floors (92 percent held) but limited evidence", "The floor held often, but the advice's gain over the best simple rule cannot be separated from zero. The app serves potato prices only in the digest."),
        ("Rs 0 silence tax for Kolar versus 'not reliable'", "Kolar's price is below the silent fallback, so silence costs nothing on price. Surprise silence is shown beside the tax for that reason."),
        ("7 objectives met, but spillover 'null' counts as an objective", "A null result is a valid outcome: the engine correctly refuses to publish. We list it separately instead of counting it as met."),
        ("Why do positive Delta-regret numbers mean 'worse'?", "Delta regret is the change in regret. Regret is a loss; positive change means more loss."),
    ],
    "fixes": [
        "Slide 3: the citations [7], [8] for 'information frictions' should point to Jensen [3] and Aker [4] (or reorder the reference list).",
        "Slide 30: update '83 pages' and '40 IEEE-style entries' to the current thesis (about 113 pages, 63 references; check the PDF).",
        "Slide 34: the closing line says 'Full 40-entry list'; the thesis list now has 63 entries.",
        "Slide 26 and 34: check that the numbers of cited references match the list as above.",
        "If you change the data load date, the demo figures (Rs 1,824, Rs 1,316, 84 percent and so on) will change: re-check slide 11 and 12 on the day.",
    ],
    "qa": [
        ("DATA", "Is the data real?", "Yes. Real Agmarknet exports (63,524 records after cleaning). An earlier dataset turned out to be synthetic; we discarded it and re-ran everything. The two exports agree where they overlap (correlation 0.99996 on 3,307 tomato market-days)."),
        ("DATA", "Why only four crops?", "Garlic has one eligible mandi so there is no choice; tomato, onion, potato and ginger have 3 to 12."),
        ("DATA", "How do you handle missing prices?", "We do not fill them in. A silent cell is a real event: the label for a trip to a silent mandi is the fallback revenue. We keep a counter of how stale a forward-filled view is."),
        ("METHOD", "What is new compared with decision-focused learning?", "We apply the idea to a real reporting-gap problem and find that the benefit comes from the realised-revenue labels, not from the SPO+ loss. We also adapt conformal floors to actions whose outcome arrives later."),
        ("METHOD", "Why conformal and not a normal margin?", "Conformal needs no assumption about the error shape and adapts over time. The normal-margin floor was broken on 26 to 35 percent of days in three crops."),
        ("METHOD", "What does 'adaptive' mean in ACI?", "The tolerance level is adjusted every day: lowered after a miss, raised slightly after a hit, so the long-run miss rate stays near 10 percent."),
        ("METHOD", "Why train on realised revenue?", "Because that is what the farmer receives; it contains transport, fee, spoilage and the chance of a wasted trip, and it teaches the model about silent mandis."),
        ("RESULTS", "How much better is it?", "Tomato: Rs 2,156 versus Rs 1,600 for the nearest mandi (+Rs 556) and Rs 2,021 for the strongest simple rule; back-test gain over the strongest rule Rs 170 (tomato), Rs 202 (ginger), Rs 60 (onion), Rs 15 (potato, not significant)."),
        ("RESULTS", "Is the improvement statistically real?", "Yes for labels: Holm p below 0.002 in all four crops, with intervals that exclude zero. No for SPO+: intervals include zero."),
        ("RESULTS", "Why do the floors hold only 84 to 92 percent in the replay?", "It is the strictest view (one multiplier fitted on half the window). On the main evaluation they are 6 to 11 percent violated. We say floors are close to, not exactly at, their level."),
        ("RESULTS", "What does the leakage audit prove?", "That decomposing the whole series before splitting leaks the future: published-protocol skill +27 to +62 percent falls to -15 to -1 percent when done causally. We audited the protocol, not specific papers."),
        ("RESULTS", "Why no gain from the language model?", "The language layer is for explanation, not accuracy. Its quality is measured by grounding (every number traceable) and by an independent judge."),
        ("LIMITS", "What is the biggest weakness?", "No field trial: all results are offline. Also one region and one source, and assumed costs."),
        ("LIMITS", "Could the crowd result be wrong?", "It depends on an association (b = 0.115) that is not a proven cause. We present it as a scenario and show that with b = 0 all policies are equal."),
        ("LIMITS", "Why is the spillover empty?", "Zero shock episodes: the labelling stage did not mark any week as squeeze or glut. The engine refused to publish; diagnosing the labelling is future work."),
        ("SYSTEM", "How do you know the system works?", "669 backend tests, 11 web tests, a 60-check smoke test of every endpoint, a fresh-clone check and CI, and the demo from the repository."),
        ("SYSTEM", "Is it deployed?", "Docker and Render files exist but deployment is not verified live."),
        ("SYSTEM", "Does the bot use a live price feed?", "No. It is built from the stored Agmarknet exports and states the data age on its second line."),
        ("SYSTEM", "How is the language model prevented from inventing numbers?", "Fixed schema, every figure checked within 1 percent against evidence, cited keys must exist, only markets from the evidence may be named, and a deterministic fallback if the provider fails."),
        ("PLAN", "What caused the schedule slip?", "The first dataset was synthetic; data was reopened, pushing the critical path by about 3.3 weeks (14 percent)."),
        ("PLAN", "Who did what?", "Manohara: data and models and research (about 430 h); Srijan: application (360 h); Shreejith: management, documentation and verification (about 180 h)."),
        ("OTHER", "What would you change?", "Run a pilot; estimate costs from data; fix the spillover labelling; add more regions."),
    ],
}
