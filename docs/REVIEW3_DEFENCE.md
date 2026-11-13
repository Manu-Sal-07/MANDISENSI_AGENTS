# Review 3 defence kit

For the industry-expert review (five parameters, 4 marks each; the communication mark is per student). Use it as a script to rehearse, not
to read out. Every figure below is in [RESULTS](RESULTS.md), [DEPLOYMENT_AND_OPERATIONS](DEPLOYMENT_AND_OPERATIONS.md),
[PROBLEM_COMPLEXITY](PROBLEM_COMPLEXITY.md) or [PRODUCT_AND_IP](PRODUCT_AND_IP.md); if you cannot find a number there, do not say it.

## 1. The two-minute pitch (no jargon)

> A farmer near Kolar has a load of tomatoes and a choice of mandis. Prices are published, but most mandis are silent on most days, 62% of
> mandi-days in our data, and a farmer who drives to a silent mandi loses the trip and the price. Existing tools show today's price. We
> answer a different question: **where and on which day should I sell this load, and what is the least I can count on?**
>
> We trained on what farmers would actually have received, including the wasted trips, and that alone cut the average shortfall by ₹87 to
> ₹157 per quintal across four crops, checked on data the model never saw. We give a minimum-revenue figure that held at its stated rate,
> and we say plainly where we have no answer: price forecasts are barely better than "no change", so we use them for risk, not promises.
>
> It is live today. The app is free, answers in Kannada, Hindi and English, and runs at no cost. Here it is.

## 2. Live demo (about 5 minutes), with a fallback for each step

| Step | Show | If it fails |
|---|---|---|
| 1 | Open the live site on a phone (QR code on the slide); health page shows the data date | open the local copy (start both servers beforehand) |
| 2 | Farmer view: choose Tomato, Kolar, 20 quintals; read the recommendation, the revenue floor and the chance each mandi is open | screenshot of the same screen, said aloud as a fallback only |
| 3 | Switch to Kannada | skip, say the strings await native review |
| 4 | "Why this mandi?" and "What if transport costs more?" panels | skip to step 5 |
| 5 | Trader desk: one spread or the forecast audit page, and the "what did not work" evidence | |
| 6 | Telegram digest message (screenshot is acceptable here: it runs as a script, not on the host) | |

Before you start: the free API sleeps when idle and **takes about five minutes to wake** (measured), so request `https://mandisense-api.onrender.com/v1/health` at least ten minutes earlier and wait for HTTP 200, then keep it warm with a pinger; keep a local copy running as the real fallback.

## 3. Who says what (every member speaks; fill in names)

| Part | Speaker | Must be able to explain and take questions on |
|---|---|---|
| Problem, users and why it is hard | ______ | silence as information; the six difficulties; who adopts it |
| Data, models and results | ______ | realised-outcome training; the floor; the weak forecasts; negative results |
| Engineering, deployment and cost | ______ | architecture, tests and CI, the outage and its fix, how data is refreshed and why it is manual, cost and scale limits |
| Demo | rotate | all three can run it |

Evaluators may mark members differently. Each of you should have **written or changed something real** in the repository and be able to
open it. The commit history is public: it currently shows one author doing almost all of the work, so say honestly who did what, and let
each member own a component they can walk through (see [CONTRIBUTIONS](CONTRIBUTIONS.md)).

## 4. Hard questions and straight answers (concede the limit first)

**Your forecasts barely beat "no change". Why is this useful?**
You are right, skill is +0.7% at five days. We therefore do not sell forecasts. The value is the decision: which mandi, which day,
net of transport, fees and spoilage, with a floor. That beats "highest price yesterday" by ₹170 per quintal in tomato (interval +104 to
+255) and ₹202 in ginger; in potato we cannot tell it apart (+15, interval -38 to +60), and we say so.

**What does it cost to run, and what breaks first?**
₹0 today (free tiers). It uses 313 MB of the 512 MB on the free plan. Memory breaks first, then the language-model rate limit, which only
degrades explanations to rule-based wording, never the numbers. A small paid instance is the first step.

**What if Agmarknet changes format or the feed goes down?**
Rows that fail validation are rejected and counted; the refresh script fails loudly (and publishes nothing) if the feed is unreachable; the app keeps the last good store and
flags it stale after 30 hours. The farmer panels are still refreshed by a manual export, and we have not automated that yet.

**Your service was down. What happened?**
Yes, for about two weeks. A free Postgres we did not need was suspended and our start-up script treated that as fatal, so it crash-looped.
We made the database optional at every layer, added regression tests, and wrote the incident into the operations document. The lesson was
an external health check.

**What is actually novel? Could someone copy it?**
The methods are known (decision-focused learning, conformal prediction). What we contribute is training the sell decision on realised
outcomes including silent-mandi trips, a floor validated out of sample, and an honest audit of published hybrids. Copying code is easy;
the evaluated method, the cleaned panel and the field relationships are the moat. We are not claiming a patent; our code is public, which
affects patentability, and we are taking advice from the institute's IPR cell.

**Who would use it, and have you asked them?**
Small farmers, FPOs, traders. We have not run a field study yet; that is the next step, starting with a handful of farmer conversations.

**What if the language model is wrong?**
It cannot change a number. Code writes every figure and name; the model may only paraphrase, then an independent judge checks it and a
validator rejects any added digit. With and without the model, the recommendation and all figures were identical in 24 of 24 cases, and
the judge caught 9 of 9 corrupted rewrites. Kannada and Hindi wording still needs a native speaker.

**Is the revenue floor a guarantee?**
No. It describes how often a method's floor held in past tests: violations of 4.6 / 10.6 / 23.3% at stated risks of 5 / 10 / 20%. It is not
a promise on any one sale.

**Why not a bigger or more modern model?**
We ran neural networks and SPO+ losses on the same realised labels. They matched LightGBM (+₹14 per quintal, interval -8 to +39), so we kept
the faster, more explainable one.

**Why is your data only five crops and one region?**
It is what public Agmarknet reports cover for the Bengaluru–Kolar belt with enough history. We make no claim elsewhere.

## 5. Checklist for the day

- [ ] Request the health URL ten minutes before and wait for HTTP 200 (cold start is about five minutes); confirm the data date is current
- [ ] Local copy of both servers running as a backup
- [ ] Phone with mobile data and the QR code slide
- [ ] Every member has run the demo once
- [ ] Every member can answer the questions in section 4 in their own words
- [ ] Rotate any key that was ever pasted in chat, before the review
