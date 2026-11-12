# Product readiness, prior art and intellectual property

A plain assessment, not a sales pitch. Items marked **[verify]** come from secondary sources (law-firm commentary, summaries) or are my
inference, and must be checked against the primary text or with the institute's IPR cell before anyone relies on them. This is not legal
advice.

## 1. What exists and what remains

**Demonstrable today:** a live farmer app and trader desk (<https://mandisensi-agents.vercel.app>), a public API, a Telegram digest bot,
five crops across 16 mandis in the Bengaluru–Kolar belt, an automated daily data refresh, 678 passing backend tests, and every claim
traced to a held-out test ([RESULTS](RESULTS.md)). Operations, cost and failure modes: [DEPLOYMENT_AND_OPERATIONS](DEPLOYMENT_AND_OPERATIONS.md).

**Before a real release (not built):**

| Gap | Why it matters | Effort (assumption) |
|---|---|---|
| Native-speaker review of Kannada and Hindi text | trust; wrong wording on money is worse than English | days, needs 2 reviewers |
| Farmer panels fed daily (arrivals are missing from the free feed) | advice currently trained through 2026-10-26 | 1 to 2 weeks incl. re-validation |
| A delivery channel farmers actually use (WhatsApp or SMS) | most small farmers will not open a dashboard | weeks; recurring message cost |
| Field validation with real farmers and traders | no user study has been done | 3 to 5 conversations is a start |
| Coverage beyond five crops and one region | results are not claimed elsewhere | per-region re-validation |
| Paid hosting with more memory and no sleep | 313 MB of 512 MB used; cold starts | a small monthly fee, check current pricing |

## 2. Who would adopt it and how

* **Small and marginal farmers around Kolar, Chikkaballapur and Bengaluru Rural:** the primary users. Adoption route: a free Telegram or
  WhatsApp daily digest in Kannada, distributed through farmer groups.
* **FPOs and cooperatives:** aggregate loads and choose a mandi for many farmers, so a better "where to sell" decision is worth more per
  decision. Route: a pilot with one FPO, measuring realised price against what they would have chosen.
* **Traders and commission agents:** the trader desk (spreads, volatility, analogues, silence value). Route: a paid tier is plausible but is
  a hypothesis, not tested. **[verify]** with interviews before claiming demand.
* **Public bodies (agriculture department, state marketing board, KVKs):** as an advisory layer on public Agmarknet data.

None of these has been approached; the routes are plans, not commitments.

## 3. Existing products and prior art

| Product or work | What it does (from sources found) | What it does not do that we do |
|---|---|---|
| **e-NAM** (national online mandi platform) | pan-India trading platform networking APMC mandis; app since October 2016; live bidding, lot tracking, advance gate entry, price information, payments, 12 languages ([Wikipedia](https://en.wikipedia.org/wiki/E-NAM), [Plantix](https://plantix.net/en/blog/e-nam-trading-portal/), [PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2023/apr/doc2023414181301.pdf)) | a trading and price-discovery platform; the sources found describe no sell-where-and-when recommendation net of transport, fees and silence, and no revenue floor **[verify]** |
| **Agmarknet / data.gov.in feed** | the public daily price and arrival reports; our data source | raw reports, no decision support |
| **Private price aggregators** (for example [NaPanta](https://napanta.com/agri-commodity-prices/karnataka/mango/26-Mar-2025)) | daily mandi prices by commodity and district; no forecasting seen on the pages; one page showed a "price updated" date older than the page date | no forecast, no net-revenue advice, no uncertainty; shows stale data without warning in at least one case found |
| **Decision-focused learning**, *Smart "Predict, then Optimize"* (Elmachtoub and Grigas, [arXiv:1710.08005](https://arxiv.org/abs/1710.08005), Management Science 2022) | trains predictions against the downstream decision loss (SPO+) | general method, shortest-path and portfolio experiments; we tested it (SPO+) and it did **not** beat the plain loss here (RESULTS section 7) |
| **Adaptive conformal inference**, Gibbs and Candès ([NeurIPS 2021](https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html)) | prediction sets whose long-run coverage tracks a target under distribution shift | general method; we apply it to a farmer's revenue floor and report violation rates |
| **Decompose-then-forecast hybrids** (STL-VMD on chili, garlic, ginger and others, [Frontiers 2025](https://www.frontiersin.org/articles/10.3389/fsufs.2025.1568041/full); leakage in full-sample decomposition argued in an MDPI 2025 paper, [IDEAS](https://ideas.repec.org/a/gam/jagris/v15y2025i11p1127-d1662849.html)) | high reported skill from decomposing the series first | the excerpts I saw do not show whether the decomposition is fitted on training data only **[verify]**; our own re-run without look-ahead removes the skill (RESULTS section 6) |

The search covered a limited set of queries and sources. A real prior-art search (Indian Patent Office InPASS, Google Patents, Google Scholar)
has **not** been done and is required before any novelty claim is made.

## 4. What is novel, and what is not

**Not novel on their own:** gradient-boosted forecasting, decision-focused learning, conformal prediction, mandi price dashboards.

**The contribution we can defend with evidence** is the combination and its evaluation:

1. Training the sell-where-and-when decision on what the farmer **actually received**, including the discounted outcome of a trip to a
   silent mandi, instead of observed prices. Measured: ₹87 to ₹157 per quintal less regret across four crops, significant after Holm
   correction.
2. A revenue floor validated out of sample (4.6 / 10.6 / 23.3% violations at 5 / 10 / 20%), against a Gaussian floor that fails 27 to 35%.
3. A reproducible audit showing decompose-then-forecast hybrids lose their skill without look-ahead, on this data.
4. A negative-results record (SPO+, shock radar, agent council) that bounds what the data supports.

Whether (1) and (2) together are **non-obvious** to someone skilled in the field is a legal judgment, not something this repository can
settle **[verify]**.

## 5. Protection options (India)

| Route | Fit | Cost and effort | Caveat |
|---|---|---|---|
| **Copyright** in the code, documents and the curated panels | automatic on creation; registration is optional | low | protects expression, not the method |
| **Open-source licence** (MIT or Apache-2.0) | maximises adoption and academic credit | free | gives away commercial exclusivity; irreversible for versions already released |
| **Keep proprietary, license commercially** (no open licence, "all rights reserved") | preserves the option to sell or license | free now | currently the **default** (the repository has no licence file) |
| **Trade secret** for trained models and any non-public farmer data | fits models; needs access control | low | the repository is public and contains the models |
| **Patent** | only if a technical contribution can be framed | high, slow | see below |

**Patent position.** Section 3(k) of the Patents Act excludes a "computer programme per se"; the Delhi High Court in *Ferid Allani v Union of
India* held that programmes showing a technical effect or technical advancement are not excluded, and commentary describes technical
effect or contribution as the working test, now under the 2025 guidelines ([Managing IP](https://www.managingip.com/article/b1kqlt87g006c7/india-computer-related-inventions-to-be-tested-on-technical-contribution),
[Mondaq](https://www.mondaq.com/india/patent/897160/patentability-of-computer-programmes-with-technical-effect-contribution-in-light-of-feridallani-v-uoi),
[Bar & Bench](https://www.barandbench.com/law-firms/view-point/revised-cri-guidelines-2025)). **[verify]** against the Act and the current
guidelines; the sources I found disagree on details. Price advice by itself is likely to read as a business method or an algorithm. A claim
would have to rest on a concrete technical effect in a system, which is an open question and not something to assert in a review.

**Disclosure timing: this is the live risk.**

* The source code is in a **public GitHub repository** (verified 2026-11-12), and the thesis and three papers (IEEE Access, CICPS, KSCST) are
  drafted for publication.
* Section 31 of the Act exempts only specific disclosures if an application follows within 12 months (including publication before a
  "learned society", claimed on Form 31); private demonstrations, websites and public repositories generally fall outside it, and a
  mismatch between the inventors and the authors of the paper can defeat it. The Indian Patent Office's own student guidance is to publish or
  demonstrate only **after** filing ([IPO student guideline](https://ipindia.gov.in/storage/uploads/media/blog1-student_guideline.pdf),
  [Chambers](https://chambers.com/articles/grace-period-exemptions-on-scientific-publications-under-the-indian-patent-law),
  [Mondaq](https://mondaq.com/india/patent/1217864/do-scientific-publications-exempt-patent-applications-from-anticipation-the-indian-position))
  **[verify]**.
* Practical consequence: **assume patent novelty for what is already public is compromised**, and decide the route (patent a later,
  separable improvement, or rely on copyright, a licence choice and trade secret) with the guide and the institute's IPR cell before the
  next disclosure.

## 6. Recommended position

1. Do not claim a patent. Claim a **defensible, evidence-backed method and a deployed system**, and state that formal IP protection is
   being assessed with the institute's IPR cell.
2. Make the licence choice **deliberately**: keep "all rights reserved" if commercial exclusivity matters, or add MIT/Apache-2.0 if
   academic reach matters more. Do not add one by default.
3. Treat the moat as the evaluated methodology, the curated and cleaned panel, the trained models and field relationships, not a patent.
4. Run a real prior-art search and keep the results in this file.
5. Before approaching any adopter, run the field validation in section 1 and replace the plans in section 2 with evidence.
