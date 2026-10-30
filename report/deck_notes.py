"""
Speaker notes for the Review-2 deck, written in plain words, and the demo run-of-show.

One source: build_deck.py writes `N` into the slides' notes pages and build_deck_script.py renders the same text, with the demo,
a glossary and the question bank, into the presenter's document.

Numbers are from the data loaded on 29 October 2026 (prices up to 26 October 2026). If the data are reloaded, run
`python report/build_insight_assets.py` and re-check every figure in NUMBERS TO QUOTE before presenting.
"""

N = {}


def add(key, minutes, tier, say, show="", quote=(), ask=(), nxt=""):
    N[key] = dict(minutes=minutes, tier=tier, say=say.strip(), show=show.strip(), quote=list(quote), ask=list(ask), nxt=nxt.strip())


CORE, OPT = "CORE", "SKIP IF SHORT"

STORY = [
    "Farmers pick a market and a day using only yesterday's price. That is a weak guide.",
    "Our system looks at what the farmer will really keep: price, minus transport, fees and spoilage.",
    "It tells the farmer where and when to sell, and a minimum amount they can count on.",
    "We tested it on days it had not seen. It beats the usual habits for tomato, onion and ginger.",
    "We also show why the advice is what it is, how it changes if costs change, and its real record.",
    "We say clearly what did not work. And a Telegram bot sends the farmer a message every morning.",
]

GLOSSARY = [
    ("floor / revenue floor", "the minimum amount a farmer can count on, on 9 days out of 10"),
    ("regret", "money lost compared with the best choice you could have made in hindsight"),
    ("oracle", "the best choice in hindsight; the ceiling nobody can reach"),
    ("realised revenue / label", "what the farmer really keeps after transport, fees and spoilage"),
    ("silent mandi", "a mandi that posts no price on that day (closed, or the data was not uploaded)"),
    ("walk-forward test", "we train only on the past and test only on days after it, like real life"),
    ("leakage", "the model secretly peeking at the future while it predicts"),
    ("conformal / ACI", "a safety margin that is learned from the model's own past mistakes"),
    ("SPO+", "a special way of training that aims at good decisions; it did not help us"),
    ("Holm, bootstrap, p-value", "checks that a difference is real and not luck; say 'the difference is real'"),
    ("model confidence set", "the list of methods that cannot be told apart from the best"),
    ("spillover", "does a shortage in one crop move the price of another crop"),
    ("null result", "we looked and found nothing; we report that honestly"),
    ("grounded brief", "an AI-written summary whose every number is checked against our data"),
    ("crowd / price flexibility", "if many farmers bring produce to one mandi, its price falls; flexibility says how fast"),
    ("coordinated split", "telling different farmers to go to different mandis so no one mandi is flooded"),
]

add("title", 0.5, CORE,
    """Good morning, respected panel. We are Srijan, Manohara and Shreejith. Our guide is Dr. Kalyan N.
Our project is called MandiSense AI.
It helps a farmer near Bengaluru and Kolar to decide two things: where to sell the crop, and whether to wait a day or two.
It also tells the farmer a minimum amount they can count on.
First we will explain the idea. Then the results, including what did not work. Then a live demo, and our plan.""",
    show="Title slide. Stand still. Say the project name once.",
    nxt="Go to the contents slide.")

add("toc", 0.3, CORE,
    """This is the plan of our talk. It follows the review checklist.
We will spend the most time on the results, the live demo, and the planning.""",
    show="Contents slide. Do not stay here long.")

add("intro", 1.5, CORE,
    """Look at this graph. It shows the tomato price at Kolar market for five years.
The price went from 100 rupees to over 9,000 rupees per quintal. That is a huge swing.
The red dots show days when the market posted no price at all. That happened on 189 days out of about 2,100.
Today a farmer decides using only yesterday's price. That is not enough.
So our problem is simple: which market, and which day, gives the farmer the most money in hand after transport, fees and spoilage?
Most earlier work only predicts prices. It does not check the real decision. It also ignores markets that post no price.
We used 63,000 real records from the government price website Agmarknet, for tomato, onion, potato and ginger.
We did not use garlic, because only one market has enough data, so there is no choice to make.""",
    show="Point at the red dots on the graph. Then point at the three number boxes.",
    quote=["63,524 real records; 36,821 market-days", "Tomato at Kolar: Rs 100 to Rs 9,330 per quintal", "189 days with no price out of 2,125", "Garlic left out: only one usable market"],
    ask=[("Why not just predict the price?", "A price prediction does not tell the farmer what to do. We teach the system to aim at what the farmer really keeps, and that works better."),
         ("Is the data real?", "Yes. It is from Agmarknet. Two separate downloads match almost perfectly. We found and removed an early fake dataset; it is in our risk list.")],
    nxt="Now our objectives and how each one went.")

add("obj", 1.5, CORE,
    """We set ten objectives. This table shows how each one went, including the ones that did not fully work.
Seven are fully done. These are: the data, the revenue model, the tests of what helps, the app, the check of other people's methods, the AI summaries, and the five new features.
One is partly done: the minimum amount we promise. For tomato and ginger it works as planned. For onion and potato it was more careful than needed.
One gave no result: whether a shortage in one crop moves another crop's price. Our method found nothing strong enough, so we published nothing, and we say so.
The last one is the morning message. It is built and tested. You will see it live in a few minutes.""",
    show="Run your finger down the Status column: green, one orange, one red, and the last row.",
    quote=["7 done, 1 partly, 1 no result, 1 built and tested", "669 tests for the system and 11 for the app, all passing"],
    ask=[("Why report something that gave no result?", "Because a number we cannot support is worse than no number. Our rule is to publish only when there is enough evidence."),
         ("Is objective 4 a failure?", "Partly. The minimum amount was met for two crops. For two crops it was safer than needed, which is the safe side.")],
    nxt="Next, how it works, in simple words.")

add("meth", 2.0, CORE,
    """Here is the main idea in simple words.
Most systems predict the price at each market and pick the highest. But they forget that some markets post no price on some days. And they forget the cost of going there.
We do it differently. We teach the system to aim at what the farmer really keeps: the price, minus the market fee, minus the loss while waiting, minus transport. If the market turns out to be silent, we count that as a loss too.
The farmer's choices are: a market and a waiting time of 0 to 3 days, or sell at the farm gate.
For the answer we also give a safe minimum, learned from how wrong the system was in the past.
The picture shows how it is built. Government data is cleaned. Our engines work on it. One service gives the answers. The app and a Telegram bot show them to the farmer.""",
    show="Move your finger left to right along the boxes. Point at the orange box and the green Telegram box.",
    quote=["Five layers: data, models, service, AI summaries, app", "Only real data in every result"],
    ask=[("Why not a simple average for the safe minimum?", "A simple average is often wrong. Our check showed it failed up to 35 days in 100. Ours stays close to the target.")],
    nxt="A little more detail on the formula.")

add("form", 1.5, OPT,
    """Do not read the symbols. Say it like this.
The first box is how we count the money. Price, minus market fee, minus loss from waiting, minus transport, minus handling.
If the market is silent, the farmer gets only part of the day's usual price.
The second box is a special training method that aims at good decisions. We tested it. It did not help much.
The third box is the safe minimum. It is the expected money minus a safety margin that is learned from past mistakes.
The table on the right gives the cost numbers we assumed, such as 4 percent fee and 20 rupees handling.
These are assumptions, so the app lets the farmer change them.""",
    show="Point at the three boxes and the small table. Do not read the formulas.",
    quote=["Fee 4%; handling Rs 20; transport Rs 0.35 per quintal per km; spoilage 3% a day for tomato"],
    ask=[("Where do the cost numbers come from?", "They are our assumptions. The farmer can change them in the app, and we tested many different values.")],
    nxt="Two more parts: the AI summaries and the crop-to-crop effect.")

add("two", 1.5, OPT,
    """Two smaller parts.
On the left, the AI summary. A language model writes a short explanation. But a checker then compares every number in it with our data. If a number is wrong or missing, the summary is marked as not checked. We also tried deliberately wrong summaries. The checker caught all nine of them.
On the right, a question: if tomato becomes scarce, does the onion price move? We tested all 40 pairs. We needed at least eight clear shortage events for each pair. We found none. So we published nothing.
The same rule applies to both parts: say only what the evidence supports.""",
    show="Point at the left box, then the right box.",
    quote=["Wrong summaries caught: 9 of 9", "Crop-to-crop effect: 40 pairs tested, 0 published"],
    ask=[("Does the AI decide the advice?", "No. Our engines decide. The AI only writes it in words, and its numbers are checked.")],
    nxt="Now the five features that let anyone check the advice.")

add("insmeth", 1.5, CORE,
    """The advice must not be a black box. So we added five features.
One: a breakdown that shows where each rupee goes, and it always adds up exactly.
Two: a what-if tool. The farmer changes the costs, and the advice updates. It also shows the exact point where the advice would change.
Three: a track record. We replay the advice on past days it had not seen, and show how often it won.
Four: a silence tax. It shows how much money a trip loses when a market posts no price.
Five: a crowd test. If many farmers follow the same advice, that market's price falls. We show how much, and a better way to spread the farmers.
The crowd test uses one assumed number. We say clearly that it is a scenario, not a measurement.""",
    show="Point at the five boxes one by one. Do not read the formulas.",
    quote=["Crowd test uses a price sensitivity of 0.115, taken from past data; it is an assumption"],
    ask=[("Is the crowd result a real measurement?", "No. It is a scenario. With the sensitivity set to zero, nothing changes. A trial with real farmers is needed to measure it.")],
    nxt="Now how it is built, and then the live demo.")

add("impl", 1.5, CORE,
    """Everything is connected end to end.
One command runs the whole chain, from the raw data to the final tests. Each step can also be run alone.
What is still manual: we download the government data by hand, because we have no live feed. And we have not tested the online deployment.
We also found and fixed some problems. A software update broke the data tools. A fresh copy of the project was missing a file. And an old server gave wrong errors during testing.
The next two slides are the live demo.""",
    show="Point along the boxes. The small screenshots are only a reminder.",
    quote=["13 steps in one command; 669 + 11 tests; a 60-point check of every page and service"],
    nxt="A quick map of the demo, then we start it.")

add("overview", 1.0, CORE,
    """Before we open the browser, here is the map of what you will see.
Six things. Each answers one simple question.
Why this market? What if my costs are different? Has the advice really worked? What does an unreliable market cost? What if everyone follows the advice? And what does the farmer receive at seven in the morning?
Three are inside the farmer's tool. Two are for traders. And one is the Telegram message.""",
    show="Point at the six boxes. Read only the question on each.",
    nxt="Now the browser: demo part one.")

add("demo1", 4.0, CORE,
    """(Open the browser, farmer app. Follow the steps on the slide. The full clicks are in the demo script.)
This is the farmer's screen. The farmer is in Kolar with 10 quintals of tomato.
The advice is: sell at Ramanagara, tomorrow. It is about 103 kilometres away.
The farmer keeps about 1,824 rupees per quintal after transport and fees. And can count on at least 1,316 rupees on 9 days out of 10.
Open Why this mandi. The long green bar is what the farmer keeps. The small coloured parts are fee, loss while waiting, transport and handling. They add up exactly. The nearest market, Kolar, would give only 1,233.
Open What if my costs differ. Move the transport slider to the maximum. Even then, the advice does not change. So the advice is safe against truck cost.
Now move the spoilage slider up. At 5 percent a day, the advice changes to selling today. So the crop's shelf life matters.
Open Has this advice worked. On past days it had not seen, it beat the nearest market 93 days out of 100. The minimum amount held on 84 days out of 100. We aim for 90. We show the real score, not a promise.""",
    show="Browser: http://localhost:3000/tools, then Best Place and Day to Sell. The exact clicks and values are in the run-of-show.",
    quote=["Ramanagara, tomorrow, 103 km", "Keeps Rs 1,824; at least Rs 1,316; for 10 quintals Rs 18,238 and Rs 13,165", "Nearest market Kolar: Rs 1,233; advice earns Rs 592 more per quintal", "Transport at Rs 3.00: same advice, keeps Rs 1,515", "Spoilage 5% a day: sell at Ramanagara today, Rs 1,789", "Beat the nearest market 93%; minimum held 84%"],
    ask=[("Why not the nearest market?", "Because the price at Ramanagara is about 776 rupees higher. That is more than the extra transport of 94 and the extra loss of 60. The breakdown shows it.")],
    nxt="Demo part two: the trader screens and the phone.")

add("demo2", 4.0, CORE,
    """(Now the trader screens, and then the phone.)
First, the Silence Tax. Each row is a tomato market. The small week strip shows the days it posts prices: green is reliable, red means closed.
Kanakapura loses a trip about 313 rupees per quintal, because it often posts no price. Chikkaballapur posted nothing on any Thursday last year. So the farmer is warned not to bring a Thursday load there.
Look at Kolar. It shows zero. That does not mean it is reliable. It means its prices are usually lower anyway. That is why we also show how often a market goes silent.
Second, the Crowd Test. One farmer alone gets 1,824 per quintal. If 200 farmers all follow the best advice, that market is flooded, its price drops by about one third, and each farmer gets only about 1,194.
If we send different farmers to different markets, each gets about 1,436. That is 241 rupees more per quintal.
Move the slider to one farmer, and everything becomes equal. Move the sensitivity to zero, and again equal. So the result depends on that assumption, and we say it.
Now the phone. Open the Telegram bot and send slash today. This is the morning message. Every price has its date. Advice appears only where our evidence is strong. Type onion Chintamani, and it answers for that crop and place. Every morning at seven a scheduled script sends it.""",
    show="Browser tabs: Silence Tax and Crowd Simulator. Then the phone with the bot chat open.",
    quote=["Kanakapura loses Rs 313 per quintal per trip (16.5% of price)", "Chikkaballapur: no price on any Thursday last year", "200 farmers: alone Rs 1,824; all follow best Rs 1,194; split Rs 1,436", "Gain Rs 241 per quintal, about Rs 4.8 lakh for the group", "The best market normally gets about 68 quintals a day"],
    ask=[("Do farmers use Telegram?", "Few today. Telegram is free and lets us show the whole flow now. The same message can go by SMS or WhatsApp later."),
         ("Where does the message data come from?", "From the downloaded government data. There is no live feed, so the message says how old the data is.")],
    nxt="Back to the slides: tools and quality.")

add("tools", 1.0, OPT,
    """These are the tools we used, and why.
Python for the data and models. Standard tools like LightGBM that work well on tables of numbers. FastAPI and Next.js to build the service and the app. Pinned versions, so anyone can repeat our work.
Our checks: 669 tests for the system, 11 for the app, and a 60-point check that opens every page and service. All pass.
The project is easy to repeat. One command rebuilds everything. Our report tables are produced by code, not typed by hand.""",
    show="Table of tools. Point at the Tested line.",
    quote=["669 system tests + 11 app tests pass", "60-point check of every page and service passed"],
    ask=[("Who wrote the code?", "The project history is in our report, with the split of work. We show it openly.")],
    nxt="How we tested it.")

add("setup", 1.2, CORE,
    """How we tested it, in simple words.
We trained the system only on older data, and tested it only on later days. That is how it works in real life. We did this five times, for different time periods, from 2024 to October 2026.
We tested on about 500 to 960 days per crop.
Every method got the same tuning effort. We compared against what farmers really do: the nearest market, and yesterday's highest price. We also compared with standard prediction models.
We measured: money actually kept, money lost compared with the best choice in hindsight, and how often the minimum amount held.
We fixed what to compare before looking at the results, so we could not pick favourites.""",
    show="Dataset table on the left; the bullet points on top.",
    quote=["Test days: tomato 963, onion 511, potato 569, ginger 776", "5 tests over time, from 2024 to October 2026"],
    nxt="The results.")

add("res", 1.2, CORE,
    """Here are the results. Each group of bars is one crop. The bars show the average money the farmer keeps per quintal.
The two blue bars are our method. They are the highest in every crop. The last grey bar is the best choice in hindsight, the ceiling.
For tomato: our method gives 2,156 rupees. Yesterday's highest price gives 2,021. The nearest market gives only 1,600.
Why does ours do better? Older methods sent 12 to 43 trips out of 100 to a market that posted no price that day. Ours cuts that to 5 to 21.""",
    show="Point at the blue bars, then at the three boxes on the right.",
    quote=["Tomato: Rs 2,156 vs Rs 2,021 vs Rs 1,600; best in hindsight Rs 2,570", "Trips to a silent market: from 12-43 in 100 down to 5-21"],
    nxt="Is the improvement real?")

add("val", 1.0, CORE,
    """Is the improvement real, or just luck? We checked.
On the left: changing what we teach the system to aim at, from the posted price to what the farmer really keeps. That saved 87 to 157 rupees per quintal in all four crops. The difference is real, not luck.
On the right: a special training method that many research papers like. On our data it made no real difference.
So the gain comes from aiming at the right thing, not from a fancier method.""",
    show="Point at the left block, then the right block, then the three cards.",
    quote=["Gain from the right target: Rs 140, 157, 87, 149 per quintal", "Special training method: no reliable gain"],
    ask=[("So the special method failed?", "On our problem it added nothing once the target was right. We planned this comparison in advance and report it as it is.")],
    nxt="The minimum amount, and the back-test of the served system.")

add("floor", 1.2, CORE,
    """Now the safe minimum. We aim for it to fail on about 10 days in 100.
In our test it fails about 6 to 10 days in 100. A simpler method fails on up to 35 days in 100. So our safety margin really works.
On the right, the system as served, tested on the last 330 days, using only what was known each day.
It beats the highest-price-yesterday habit by 170 rupees for tomato, 60 for onion, and 202 for ginger. These gains are real.
For potato, the gain is only 15 rupees and could be luck. So the app does not give selling advice for potato. It shows prices only.""",
    show="Left table, then the bar chart on the right.",
    quote=["Minimum fails on 9.0, 6.3, 6.9, 10.5 days in 100 (target 10)", "Simple method fails on up to 34.5 days in 100", "Gain over yesterday's best market: Rs 170, 60, 202; potato 15 (not reliable)"],
    nxt="Now the new features, starting with why this market.")

add("why", 1.2, CORE,
    """These are the first two panels you saw in the demo.
On the left: the breakdown. Price 2,081, minus fee 83, minus loss while waiting 60, minus transport 94, minus handling 20, equals 1,824. The nearest market keeps only 1,232.
The advice wins because its price is 776 rupees higher. That is far more than the extra transport and extra loss.
On the right: what if. Even if transport costs 4 times more, the advice stays the same. But if spoilage reaches 5 percent a day, or the farmer cannot wait, the advice changes to selling today.
So the farmer sees what the advice depends on.""",
    show="Left picture: Why this mandi. Right picture: What if. Then the bullets.",
    quote=["2,081 - 83 - 60 - 94 - 20 = 1,824", "Nearest market Rs 1,232 (the screen shows 1,233 after rounding)", "Advice changes at 5% spoilage a day"],
    nxt="Has the advice really worked?")

add("track", 1.2, CORE,
    """Has the advice really worked? We replayed it over 165 past days it had not seen.
Against the nearest market, it did better on 93 days out of 100 for tomato, 82 for onion, 63 for potato, and 90 for ginger.
Against yesterday's highest-price market, many days are the same, because both give the same advice. When they differ, ours wins more often for tomato and onion.
Now the honest part. The minimum amount held on 84 days out of 100 for tomato, not 90. For onion 89, potato 92, ginger 86.
This replay is a strict test. In the larger test earlier, the minimum failed on 10 to 12 days out of 100. We show the farmer the real score.""",
    show="Table and line graph. Point at the Floor held column.",
    quote=["165 days, 12 May to 23 Oct 2026", "Better than nearest market: 93, 82, 63, 90 days in 100", "Minimum held: 84, 89, 92, 86 days in 100 (target 90)"],
    ask=[("Is 84 percent a failure?", "It is a little below our 90 percent target in a short, strict replay. The longer test was closer. The app shows the real score, not a promise.")],
    nxt="What does an unreliable market cost?")

add("silence", 1.0, CORE,
    """Some markets post no price on some days. That wastes the farmer's trip. We put a rupee figure on it.
Across 13 tomato markets, a trip loses about 78 rupees per quintal on average. Kanakapura loses 313, which is 16.5 percent of its price.
The colour picture shows each market by weekday. Red means the market is usually silent that day, like Sundays at several markets, and Thursdays at Chikkaballapur.
Two warnings. A silent day may mean the market is closed or the data was not uploaded. We cannot tell. And a zero for a cheap market such as Kolar does not mean it is reliable, so we show the silence rate too.""",
    show="The colour picture, then the table.",
    quote=["13 tomato markets; average loss Rs 78 per quintal per trip", "Kanakapura Rs 313 (16.5%)", "Chikkaballapur: no price on any Thursday"],
    nxt="What if everyone follows the advice?")

add("crowd", 1.2, CORE,
    """Here is the question an examiner should ask: what if everyone follows your advice?
One farmer alone gets 1,824 rupees per quintal.
If 200 farmers all go to the best market, it gets flooded. Its price drops by about one third. Each farmer gets only about 1,194. That is no better than going to the nearest market.
If we send different farmers to different markets, each gets about 1,436. That is 241 rupees more per quintal, about 4.8 lakh for the group.
The more farmers there are, the worse the flooding, and the more the split helps.
This uses an assumed price sensitivity taken from past data. It is a scenario, not a measurement. With zero sensitivity, nothing changes.""",
    show="The line graph, then the three boxes, then the grey caution note.",
    quote=["200 farmers, 10 quintals each", "Alone Rs 1,824; all follow best Rs 1,194; nearest Rs 1,207; split Rs 1,436", "Price drop 32.5%; gain Rs 241 per quintal; Rs 4,82,705 in total"],
    ask=[("How would you measure the real effect?", "By a trial: some farmers get the advice, some do not, at the same market. Then compare prices. This is our first future task.")],
    nxt="The morning message.")

add("digest", 1.0, CORE,
    """This is the morning message exactly as the bot sends it.
The first lines say the date of the latest prices, and how old the data is, because we have no live feed.
Each crop shows the latest price with its date, and the change from last week.
Advice appears only where our evidence is strong: tomato, onion, ginger. For potato we show prices only.
It is free, it works in English, Kannada and Hindi, and the farmer can ask by typing, for example, tomato Kolar.
Every message sent is recorded, and it has already been delivered to a real phone. What we have not done: a trial with farmers, or a live price feed.""",
    show="The message picture on the left, then the bullets on the right.",
    quote=["Bot name: @MandiAis_BOT", "8 tests; every price carries its date", "Sent every morning at 7 by a scheduled script"],
    ask=[("Why Telegram and not SMS?", "SMS in India needs registration and a paid service. Telegram is free, so we could build and show the full flow now. The same message can go by SMS later."),
         ("What about privacy?", "We store only the chat id, first name, language, district and crops. The farmer can stop at any time.")],
    nxt="Back to the research results: a check on other people's method.")

add("leak", 1.2, CORE,
    """Many papers say they predict prices very accurately by splitting the price into parts first. They report gains of 27 to 62 percent.
We tested this. We found that their way of splitting secretly uses future prices. It is like the model peeking at tomorrow.
When we split the series using only the past, as in real life, the gains vanish. The result is minus 15 to minus 1 percent. The red bars are the claimed gain. The blue bars are the honest result.
A modern ready-made forecasting model also did not beat a simple rule on this daily tomato series.
We checked the method that these papers describe, not each specific paper.""",
    show="Bar chart: red is the claimed gain, blue is the honest result.",
    quote=["Claimed gain +27 to +62%; honest result -15 to -1%"],
    nxt="Things that did not make the cut.")

add("null", 1.2, OPT,
    """We also tried other ideas. They did not work, and we say so.
A team of four small forecasting models did not beat one model. So we do not use it.
A study of supply shocks found no strong effects out of 30 tests, and only five weak hints.
The crop-to-crop effect: none published.
Forecasts for 3, 5 and 7 days do beat the simple rule, so we serve them, with honest ranges. One-day forecasts do not, so we do not serve them.
The AI summaries keep most sentences; fewer in Kannada and Hindi, so those need a native speaker to check.
Zero crop-to-crop events also tells us something about our own method: it needs labels that our data does not yet have.""",
    show="Table. Read down the Verdict column.",
    quote=["Team of models: no better than one", "Shocks: 0 strong, 5 weak hints out of 30", "Crop-to-crop: 0 of 40 pairs published"],
    ask=[("What would you do next about crop-to-crop effects?", "Define the shortage events directly from market arrivals, then test all 40 pairs again.")],
    nxt="Comparison with other methods.")

add("bench", 0.8, OPT,
    """This compares everything on the same days and the same measure.
No other published study judges market choice this way, so we compare with what farmers really do, and with standard prediction methods.
We win in all four crops against every habit and every standard method.
Where we do not clearly win: for potato, the gain is not reliable. And the special training method did not beat the ordinary one.""",
    show="Table. The two blue rows are ours.",
    quote=["Share of the possible gain captured: tomato 0.57, onion 0.48, potato 0.31, ginger 0.76"],
    nxt="What is new in our work.")

add("nov", 1.0, OPT,
    """What is new here, in one sentence? We teach the system to aim at what the farmer really keeps, even when markets are silent. We give a tested minimum. And we showed that a popular price-prediction trick secretly uses the future.
What already existed: price forecasting, the special training method, and the safety-margin idea.
What is new: we use the money the farmer really keeps, on real market data. Our minimum is learned from past mistakes. We measured the false gain in other methods. And we added checks that let anyone inspect the advice.
Some parts are ours, some are adapted from earlier work. The right-hand card lists which.""",
    show="Three cards, left to right.",
    ask=[("What exactly is new?", "The combination, and the check of other methods. The training idea and the safety-margin idea are adapted from earlier work. We did not find earlier work on the crowd effect for market choice.")],
    nxt="What we tried to improve.")

add("opt", 1.0, OPT,
    """Each row changes one thing and checks whether it helps.
The special training method: no real difference.
Adding a part that guesses whether a market will post a price: it made things worse.
Adding signals from neighbouring markets: no real difference.
Tuning for forecast accuracy instead of decisions: no change.
We chose the lighter model for serving, because it gives the same decisions, and is cheaper to run and easier to explain.
We keep the failures in the report. They are part of the result.""",
    show="Table, then the note below it.",
    quote=["Reporting part: 23 rupees worse, a real difference"],
    nxt="Planning.")

add("wbs", 1.5, CORE,
    """Our plan. The work is in five packages, about 970 hours in total: management and documents, data, models and research, the application, and testing.
Every task has one owner. Manohara has data and research. Srijan has the application. Shreejith has the report and test plan. The hours are our estimates, not a timesheet.
The picture shows the tasks in order. The red path is the one that sets the total time: 24 weeks. A delay on the red path delays the whole project.
The blue tasks have spare time. For example, the web app has 5 weeks of spare time, the AI summaries have 7.
Worked example for the web app: it must finish by week 16, it takes 5 weeks, so it must start by week 11. It can start at week 6. The difference is 5 weeks of spare time.""",
    show="Table on the left, picture on the right. Point at the red path, then the blue boxes, then the worked example.",
    quote=["About 970 hours; Manohara 430, Srijan 360, Shreejith 180", "Red path 24 weeks; spare time: web app 5, AI summaries 7, backend 5"],
    ask=[("The code history shows mostly one author.", "Yes, and our report says so plainly. The history does not show work done on other computers. The split of work is our agreement. We do not hide it.")],
    nxt="How the schedule went, and risks.")

add("risk", 1.5, CORE,
    """Planned against actual. We planned 24 weeks and took about 27. That is a delay of about three weeks, or 14 percent.
The main cause was the data. Our first dataset turned out to be fake. We replaced it with the real government data and ran every experiment again. That delayed the tasks on the red path.
The orange bars are the actual time. The blue bars are the plan. The plan was rebuilt from our earlier roadmap, and the actual dates come from our work history.
The risk table shows what could go wrong. Six risks really happened, including the fake data, a hidden problem where the model peeked at the future, and a software update that broke the tools. We caught and fixed each.
Three are still open: team workload balance, testing the online version, and no trial with farmers.""",
    show="Chart on the left, risk table on the right. Point at the orange bars.",
    quote=["Planned 24 weeks; actual about 27 (+3.3 weeks, 14%)"],
    nxt="The report.")

add("rep", 0.8, CORE,
    """Our report follows the college template. It has seven chapters, six appendices, and the references.
Every table is produced by code from our results, so nothing is typed by hand.
It now includes the new features and the morning message.
Still to do: the official plagiarism report. We have not run it yet, so we quote no percentage. Also the table of course outcomes from the course file, and our guide's corrections.""",
    show="The status table, and the box on plagiarism.",
    ask=[("What is the similarity score?", "We have not run the official check yet. We will add it to Appendix F. We will not quote a number we have not measured.")],
    nxt="The goals for society.")

add("sdg", 1.0, CORE,
    """These are the United Nations goals our work touches, with the exact target numbers.
Target 2.3, helping small farmers earn more through better market information. In our test the advice earned 60 to 202 rupees per quintal more than the best simple habit in three crops. That is a test result, not real income yet.
Target 1.4, access to services: a free tool in three languages. Not measured.
Target 12.3, less food loss: we count spoilage in the advice. We did not measure kilograms saved.
Target 9.c, access to technology: our open code, built on public data.
The morning message puts this on a free channel. Whether farmers use it, we do not know yet.""",
    show="Table. Point at the Status column.",
    nxt="Our research papers.")

add("paper", 0.8, OPT,
    """We have two papers written. The main one is for the journal IEEE Access. It has 14 pages. It covers training for what the farmer keeps, the safe minimum, and the check of other methods.
The second is for a conference, 12 pages.
Neither has been submitted yet, so we have no acknowledgement to show. We say that plainly. Our next step is to submit the journal paper.""",
    show="Table of papers and status.",
    nxt="Conclusion.")

add("conc", 1.2, CORE,
    """To conclude. The system tells a farmer where and when to sell, and a minimum they can count on. In our tests it earns 170 rupees per quintal more than the best simple habit for tomato, and 202 more for ginger.
Now the advice can also be inspected. Why it is what it is. What happens if costs change. How it did on days it had not seen.
Of our ten objectives, seven are fully met, one is partly met, one gave no result, and one is built and tested.
Our limits: one region, one data source, and no trial with real farmers. The crowd test is a scenario. The minimum held on 84 to 92 days out of 100.
Our next steps follow from those limits: a trial with farmers through the bot, a better way to find shortage events, and testing the online version.""",
    show="Left card, then right card.",
    quote=["Rs 170 more for tomato; Rs 202 more for ginger", "7 done, 1 partly, 1 no result, 1 built and tested"],
    nxt="References, then thank you.")

add("ref", 0.2, OPT, """The references are in the standard format, in the order we cite them. The full list of 40 is in the report.""", show="Do not read.")

add("thanks", 0.2, CORE,
    """Thank you. We are happy to answer your questions, and to show any part of the system again.""",
    show="Keep the browser and the phone ready for follow-up questions.")

DEMO_SETUP = [
    ("1 hour before", "Charge the laptop and the phone. Close other programs. Use a steady internet connection (only the Telegram bot needs the internet)."),
    ("45 min before", "Window 1: open the project folder and start the service: `ms_env\\Scripts\\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000`. Wait until it says 'Application startup complete'. If something old is already running on port 8000, stop it first, otherwise new pages show 'not found'."),
    ("40 min before", "Window 2: `cd frontend`, then `npm run dev`. Open http://localhost:3000/tools once to warm it up."),
    ("35 min before", "Window 3: start the bot: `ms_env\\Scripts\\python.exe scripts/telegram_bot.py`. It must print 'MandiSense bot @MandiAis_BOT is running'."),
    ("30 min before", "Phone: open https://t.me/MandiAis_BOT, press Start, choose English, Kolar, tomato and onion, then Done. You should get a message within seconds. This signs up the phone so the demo works."),
    ("25 min before", "Quick check: `ms_env\\Scripts\\python.exe scripts/smoke_ui.py --only market-choice` must end with ALL PASSED. Then again with `--only trader-tools/`."),
    ("20 min before", "Open these browser tabs in order: (1) http://localhost:3000/tools, (2) /trader-tools/reporting-value, (3) /trader-tools/crowd-simulator, (4) /trader-tools/market-choice, (5) http://localhost:8000/docs. Set the farmer app to English (language button at top right). You will switch to Kannada during the demo."),
    ("15 min before", "Open the slides in Presenter View so you can see the notes. Press F5 from slide 1. Keep the report PDF open in another window."),
    ("10 min before", "Practise the three clicks that matter: the Best Place tool, the spoilage slider, the farmers slider. Reset with 'Back to standard costs'."),
    ("5 min before", "Silence phone notifications. Raise the phone brightness. The slides contain screenshots of every screen, as a backup."),
]

DEMO_STEPS = [
    ("A1", "Farmer app, 3.5 min", "Tab 1: /tools. Tap 'Best Place & Day to Sell'.",
     "Place: Kolar. Crop: tomato. Quantity: 10 quintals. Vehicle: Tempo. Confidence 90%.",
     "Advice card: **Ramanagara, Wednesday 28 Oct, in 1 day, 103.2 km**. Farmer keeps about **Rs 1,824** per quintal; can count on at least **Rs 1,316**. For 10 quintals: Rs 18,238 and Rs 13,165. Chance the market posts a price: 97%. Line: Rs 592 more per quintal than the nearest market (Kolar).",
     "Say: 'The advice is not the nearest market. The next panels show why.'"),
    ("A2", "", "Tap 'Why this mandi?'.", "",
     "Four rows. Our advice Rs 1,824. Nearest market, today, Kolar Rs 1,233. Highest price yesterday, Ramanagara today Rs 1,789. Farm gate Rs 1,235. Green is what the farmer keeps; the other colours are fee, loss while waiting, transport, handling, and the trader's cut at the farm gate.",
     "Say: 'Price 2,081, minus fee 83, minus waiting loss 60, minus transport 94, minus handling 20, equals 1,824. It always adds up.'"),
    ("A3", "", "Tap 'What if my costs are different?'. Drag the first slider (transport) fully to the right.", "",
     "Transport shows Rs 3.00. The green box still says **SAME ADVICE AS BEFORE**, Ramanagara in 1 day, Rs 1,515 per quintal, minimum Rs 1,008. A line says that up to Rs 3 per quintal per km this stays the best choice.",
     "Say: 'Even at four times the normal truck cost, the advice does not change.'"),
    ("A4", "", "Tap 'Back to standard costs'. Drag the spoilage slider to about 5%.", "",
     "At 5.0% the box turns amber: **THE ADVICE CHANGES**, Ramanagara today, Rs 1,789. A line says the advice changes when spoilage passes 5.0% a day.",
     "Say: 'So the advice is safe against truck cost, but sensitive to how fast the crop spoils.' Then drag the third slider ('Most days I can wait') to 0 to show 'today' again, and tap 'Back to standard costs'."),
    ("A5", "", "Tap 'Has this advice worked?'.", "",
     "Text: 'Days we had not seen when the advice was made, over 165 days'. Beat the nearest market: **93% better, 7% worse**. Beat yesterday's highest-priced market: **24% better, 68% same, 8% worse**. Days the minimum held: **84%**, and the line 'We aim for 9 days in 10. This is the actual score, not a promise.' The running-gain line rises to about Rs 532 per quintal.",
     "Say: 'We show the real score, even though 84 is below our target of 90.'"),
    ("A6", "", "Switch the language button (top right) to Kannada, then back to English.", "",
     "The tool shows in Kannada: 'ಈ ಮಂಡಿ ಯಾಕೆ?', 'ನನ್ನ ವೆಚ್ಚ ಬೇರೆ ಆದರೆ?', 'ಈ ಸಲಹೆ ಕೆಲಸ ಮಾಡಿದೆಯೇ?'.",
     "Say: 'Everything exists in English, Kannada and Hindi.' Close the tool (X)."),
    ("B1", "Trader screens, 3.5 min", "Tab 2: /trader-tools/reporting-value (crop: Tomato).", "",
     "Period 26 Oct 2025 to 26 Oct 2026; average loss **Rs 78** per quintal per trip. First row **Kanakapura**: reports on 44% of days, closed Sundays, worst other day Friday (50% silent), **Rs 313 (16.5%)**. Next: Binny Mill Rs 206, Doddaballapur Rs 135. Chikkaballapur: Thursday cell red, 'Known closed: Thursday'. Kolar: Rs 0.",
     "Say: 'Green days are reliable, red are closed. Kolar shows zero but that does not mean reliable; its prices are simply lower. That is why we show the silence rate next to it.' Optional: change the crop to Ginger: Doddaballapur Rs 1,410 (15.6%)."),
    ("B2", "", "Tab 3: /trader-tools/crowd-simulator (Tomato, Kolar). Leave 200 farmers, 10 quintals, flexibility 0.115.", "",
     "Bars: One farmer alone **Rs 1,824**; Everyone follows the best action **Rs 1,194**; Everyone goes to the nearest mandi **Rs 1,207**; Coordinated split **Rs 1,436**. Boxes: price drop **-32.5%**; gain per quintal **Rs 241**; group gain **Rs 4,82,705**. Text: 'that yard usually receives about 68 quintals a day, the crowd brings 2,000 quintals'.",
     "Say: 'If 200 farmers all follow our advice, we spoil our own advice. Spreading them out recovers 241 rupees per quintal.'"),
    ("B3", "", "Drag 'Farmers following the advice' to 1: all four bars are almost equal. Drag to 2000: the red bar falls more, the split stays higher. Set 'Price flexibility b' to 0: all four equal. Then restore 200 and 0.115.", "",
     "With 1 farmer: alone 1,824, everyone-follows-best about 1,793. With flexibility 0: every policy equals the alone figure.",
     "Say: 'This is a scenario, not a measurement. With zero sensitivity there is no problem. We state the assumption and give you the slider.'"),
    ("C1", "Telegram, 2.5 min", "Phone: open the chat with @MandiAis_BOT. Send /today.", "",
     "Message: 'MandiSense market update for Kolar'; 'Prices reported up to 26-Oct-2026'; 'Data is 3 days old'. Tomato: Kolar Rs 1,330 per quintal [26-Oct], +9% vs 7-day average; Best place to sell Ramanagara (103 km), wait 1 day; about Rs 1,824; at least Rs 1,316 on 9 days in 10; Rs 592 more than the nearest mandi. Onion: Bangarpet Rs 4,250 [26-Oct], sell on the next market day, about Rs 3,955. Footer: advice, not a promise.",
     "Say: 'Every price has its date. We have no live feed, so we say how old the data is.'"),
    ("C2", "", "Send: onion chintamani. Then send: ಟೊಮೆಟೊ ಕೋಲಾರ.", "",
     "The bot replies with the message for that crop and place.", "Say: 'Farmers can type in their own language.'"),
    ("C3", "", "Window 4: `ms_env\\Scripts\\python.exe scripts/send_daily_digest.py` (the 7 am job). Show the phone buzzing, then open data\\farmer\\telegram_outbox.jsonl.", "",
     "The window prints `{'subscribers': 1, 'sent': 1, 'failed': 0}`; the phone gets the message; the log line shows kind daily, status sent.",
     "Say: 'Windows Task Scheduler runs this every day at 7.'"),
    ("D1", "Optional, 30 s", "Tab 5: http://localhost:8000/docs.", "",
     "The list shows the five new services under market-choice, and the notification services.", "Say: 'Everything you saw is available as a service. The app and the bot are two users of it.'"),
]

CONTINGENCY = [
    ("The bot does not answer", "Check that Window 3 is still running and the internet works. Restart `scripts/telegram_bot.py`. If the internet is down, show slide 22 (the message picture) and say the message builder also works offline: `python scripts/send_daily_digest.py --dry-run` prints what would be sent."),
    ("A page shows an error or 'not found' for the new services", "An old service is still running on port 8000. Stop it (`netstat -ano | findstr :8000`, then stop that process) and start ours again. Check with `curl http://127.0.0.1:8000/v1/market-choice/track-record/tomato`."),
    ("The numbers on screen differ from the notes", "The notes use the data loaded on 29 Oct 2026 (prices to 26 Oct). If the data was reloaded, run `python report/build_insight_assets.py`, read the new figures from report/generated/deck_data.json, and say 'as of the latest data'."),
    ("The farmer tool is slow the first time", "The engine loads on first use. Open the tool once before the demo."),
    ("The AI service is not available", "The demo does not depend on it. The text falls back to plain rule-based wording. Say so."),
    ("The live demo cannot run at all", "Use the screenshots on slides 10 to 22. They are real screens from the running system. Do not say they are live."),
]

QA = [
    ("Why did the minimum hold on only 84 days out of 100 for tomato?", "That replay is a strict test on a short period. In the longer test, the minimum failed on about 10 days in 100, close to the target. We show the farmer the real score, not a promise."),
    ("What is your main contribution?", "We teach the system to aim at what the farmer really keeps. That saves 87 to 157 rupees per quintal in all four crops. We also give a tested minimum, and we showed that a popular prediction method secretly uses the future. The extra features let anyone check the advice."),
    ("Why did the special training method not help?", "Once the target was right, the method made no real difference. Other research also says its value depends on the problem."),
    ("Is the crowd result real?", "It is a scenario, based on how price moved with arrivals in past data. It is not proven cause and effect. With zero sensitivity there is no effect. A trial with farmers is needed."),
    ("Why is there no live data?", "We download the government data by hand. We had no live feed. The message says how old its data is, and reloading takes one command."),
    ("Is the Telegram bot safe and private?", "The secret key is kept outside the code and never printed. We store only the chat id, first name, language, district and crops. The farmer can stop at any time."),
    ("What about farmers who do not use Telegram?", "Agreed. Telegram is the free way we could show the idea now. The same message can go by SMS or WhatsApp later. Our survey asks farmers which channel they prefer."),
    ("Why no selling advice for potato?", "Our test could not show that the advice beats the simple habit for potato, so we do not claim it. The app shows prices only. Garlic has only one market, so there is no choice to make."),
    ("What does a silent market mean?", "A market that posted no price that day. It may be closed, or the data was not uploaded. The government site does not say which."),
    ("Is your crop-to-crop method broken?", "No. It ran correctly and found nothing strong enough, so it published nothing. Its way of finding shortage events needs labels that our data does not have yet. That is our next task."),
    ("How do you stop the model from peeking at the future?", "We train only on the past and test only on later days. We keep a gap between them. Our tests check that changing future data never changes the inputs. And a result is used only after its sale date has passed."),
    ("Who did what?", "Manohara: data, engines, research, pipeline. Srijan: the service, the farmer and trader apps, the AI part and the new features in our agreed split. Shreejith: the literature study, requirements, tests and the report. The project history is in the report, as it is."),
    ("What did it cost?", "No cash. We used free tools and public data. Our time, counted at 200 rupees an hour for 970 hours, is about 1.94 lakh rupees."),
    ("What would you do with more time?", "A trial with real farmers through the bot, better detection of shortage events, measuring the cost numbers from data instead of assuming them, and testing the online version."),
]

SHORT_PATH = ["title", "intro", "obj", "meth", "insmeth", "impl", "demo1", "demo2", "setup", "res", "val", "floor", "track", "crowd", "leak", "wbs", "risk", "sdg", "conc", "thanks"]


def render(key: str) -> str:
    n = N[key]
    out = [f"[{n['tier']} · about {n['minutes']:g} min]", "", "SAY (in these simple words)", n["say"]]
    if n["show"]:
        out += ["", "SHOW / CLICK", n["show"]]
    if n["quote"]:
        out += ["", "NUMBERS TO QUOTE"] + [f"- {q}" for q in n["quote"]]
    if n["ask"]:
        out += ["", "IF ASKED"] + [f"Q: {q}\nA: {a}" for q, a in n["ask"]]
    if n["nxt"]:
        out += ["", "TRANSITION", n["nxt"]]
    return "\n".join(out)
