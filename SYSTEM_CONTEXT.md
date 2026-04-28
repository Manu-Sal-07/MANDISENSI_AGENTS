# SYSTEM_CONTEXT.md

# 🧠 1. SYSTEM OVERVIEW
* **What problem the system solves**: Predicts commodity prices by analyzing cyclical seasonality patterns, supply stress, and external macro factors.
* **Why a multi-agent approach is used**: Allows specialized components to handle distinct drivers of price (long-term cycles, short-term volume shocks, and unpredictable news events) independently before their insights are aggregated.
* **Overall working principle in simple technical terms**: The system uses a hybrid approach. It ingests historical market data and text-based news, applying a mix of statistical time-series methods, tree-based machine learning, and deterministic rule engines. Each specialized agent produces an independent prediction and confidence metric, which will eventually feed into a master orchestration layer.

---

# 🔄 2. OVERALL SYSTEM FLOW
* **How data enters the system**: Market data (prices, volumes) is pulled from local structured storage, while news and events are scraped and ingested as text feeds.
* **How it is processed**: The data is cleaned, missing values are interpolated, and rolling averages are calculated to smooth noise. News is parsed to extract key entities and events.
* **How different agents operate**: The Seasonality Agent isolates recurring patterns over time. The Arrival Volume Agent detects sudden changes in supply. The External Factors Agent translates text news into numerical impact scores. These operate asynchronously or in parallel.
* **How outputs are generated**: Each agent outputs its prediction along with an estimated confidence level and supporting explanations (metrics, regimes, and models used).

---

# 🤖 3. AGENT DESCRIPTIONS (DETAILED)

## 🔶 3.1 Seasonality Agent

### 🎯 Purpose
* Responsible for predicting the 30-day forward commodity price by analyzing historic cyclical patterns and long-term trends.

### 🧠 Core Approach
* **How seasonality is captured**: The agent breaks down historical prices into three components: a fundamental trend, a recurring seasonal pattern, and random noise. 
* **How trends are identified**: It looks at the recent gradient of the extracted trend to classify the current market cycle as ascending, descending, peaking, or troughing.
* **How festivals or cyclical patterns are handled**: It compares historical prices during known festival periods against non-festival days to calculate an expected percentage premium.
* **How structural changes are detected**: It continuously compares the seasonal pattern of the last three years against the entire historical baseline. If the recent pattern deviates significantly from the historical norm, it flags a structural drift warning.

### 📊 Data Used
* Historical daily prices and volumes.
* A calendar mapping specific dates to known festivals.

### ⚙️ Internal Processing (HIGH LEVEL)
* The agent ingests market data, calculates rolling averages and momentum, and performs statistical decomposition. It extracts a set of features, feeds them into a collection of predictive models, dynamically weighs their outputs based on their recent accuracy, and outputs a 30-day forecast.

### 📈 Models Used
* **Types of models used**: A mix of linear regression, tree-based ensembles, gradient boosting, and statistical forecasting models.
* **Why multiple models are used**: Different models excel under different conditions (e.g., linear models handle stable trends well, while tree-based models capture complex interactions). The ensemble approach mitigates the weakness of any single model.

### 📤 Output
* **What the agent outputs**: A predicted percentage change in price.
* **Prediction horizon**: 30 days.
* **Metrics included**: A confidence score (penalized if structural drift is detected), expected volatility, probability of a positive price increase, and the strength of the seasonal signal.

---

## 🔶 3.2 Arrival Volume Agent

### 🎯 Purpose
* Responsible for predicting short-term price movements specifically driven by sudden changes in supply and arrival volumes at the market.

### 🧠 Core Approach
* **How supply impacts price**: The agent models the relationship between the volume of goods arriving at the market and the resulting price changes.
* **How elasticity is used**: It continuously calculates price elasticity by measuring how responsive the price is to fluctuations in supply over a rolling window.
* **How supply shocks are identified**: It scores supply stress by evaluating deviations from the monthly average, year-over-year differences, and consecutive days of declining supply. If the deviation is extreme, a shock flag is triggered.

### 📊 Data Used
* Historical daily prices and arrival volumes.

### ⚙️ Internal Processing
* The agent calculates rolling metrics, lag features, and supply momentum. It determines the current supply regime (e.g., squeeze, oversupply). It then trains multiple models on these features, adjusts their influence based on the active regime, and generates a forecast.

### 📈 Models Used
* **Types of models used**: Linear regression, tree-based ensembles, and gradient boosting models.
* **Why multiple models are used**: To balance simple elasticity rules with the ability to handle non-linear supply shocks.

### 📤 Output
* **What predictions are generated**: An expected percentage change in price.
* **Time horizon**: 7 days.
* **Additional signals**: Supply stress score, active supply regime categorization, historical price-arrival correlation (lag peak), and an elasticity coefficient.

---

## 🔶 3.3 External Factors Agent

### 🎯 Purpose
* Responsible for quantifying the impact of external news, policy changes, and weather events on commodity prices.

### 🧠 Core Approach
* **How external data is processed**: Natural language processing is used to scan news articles for specific keywords related to the commodity.
* **How signals are extracted**: It matches text against predefined event categories (like export bans or droughts) and assigns a confidence level based on the exactness and frequency of the matches.
* **How impact is quantified**: Events are assigned a base score, mathematically decayed over time as the news ages, and verified against historical price changes to measure true causal impact.

### ⚙️ Processing Stages
* **Extraction**: Scanning raw text to identify the commodity, event type, and match confidence.
* **Normalization**: Standardizing the extracted event formats.
* **Scoring**: Mapping recognized events to predetermined impact weights.
* **Decay**: Applying an exponential mathematical decay so older events have less influence on the current score.
* **Aggregation**: Combining multiple active events for a single commodity into a final numerical score.

### 📈 Intelligence Layer
* **Role of rules**: Provide immediate, heuristic-based scoring for known high-impact events using predefined weights.
* **Role of ML**: Provides an alternative data-driven score by evaluating engineered features derived from the events.
* **Role of causal logic**: Verifies the true market impact by isolating the event date, estimating what the price should have been without the event, and measuring the actual deviation.

### 📤 Output
* **What score is produced**: A fused impact score combining rules, ML, and causal logic.
* **Range**: A normalized value between -1.0 (strong negative impact) and 1.0 (strong positive impact).
* **Meaning of confidence**: Represents the certainty of the signal based on the number of news sources, keyword match strength, and historical causal variance.
* **Explanation output**: A human-readable breakdown of the contributing events, the overall trend direction, and alert levels.

---

# 🧩 4. ENSEMBLE STRUCTURE
* **How outputs from agents are currently used**: Each agent operates as a standalone intelligence unit, outputting a structured response containing its prediction and confidence.
* **Whether they are combined or not**: Currently, the agent outputs are not mathematically combined.
* **Current state of ensemble layer**: The individual agents employ their own internal ensembles to select the best predictive models, but the overarching meta-ensemble layer designed to blend the final outputs of the three agents has not yet been implemented.

---

# 🧠 5. MODELING STRATEGY (HIGH LEVEL)
* **Type of ML approaches used**: Tree-based ensembles, linear regularized regression, and classical statistical forecasting.
* **Training approach**: Time-series cross-validation. The data is split chronologically, walking forward in time to simulate real-world forecasting. Models are ranked by their average error across these time splits.
* **Whether models retrain dynamically**: The models do retrain dynamically. Upon every execution, the agents perform cross-validation to reassess model performance and adjust the influence of each model before making the final prediction.

---

# 📊 6. CURRENT SYSTEM OUTPUT
* **What outputs are available today**: Independent predictions from the Seasonality and Arrival agents (expected price change and confidence), and an impact score from the External Factors agent.
* **Whether outputs are separate or combined**: The outputs are strictly separate.
* **How a user would interpret results**: A user would view the 30-day forecast to understand long-term cyclical trends, cross-reference it with the 7-day forecast to anticipate immediate supply-driven shocks, and monitor the external factors score for ongoing risks from news and policy.

---

# 🚧 7. CURRENT SYSTEM STATE
* **What parts are fully implemented**: The core logic, feature engineering, and internal ensembling for all three agents are fully implemented. The pipelines can ingest data, evaluate models, and produce comprehensive insights.
* **What parts are partially implemented**: The causal engine within the External Factors agent relies on an emulated price feed because it lacks a direct connection to the live price database.
* **What parts are not yet connected**: The meta-ensemble orchestrator, which is meant to combine the isolated agent outputs into a single definitive forecast, is missing entirely. Hyperparameter tuning frameworks for the models are also not yet connected.

---

# 📌 8. ASSUMPTIONS
* ⚠️ **Inferred**: It is assumed that all registered predictive models within the agents share a unified interface for training and predicting, allowing them to be seamlessly swapped and evaluated by the internal ensemble engines.
* ⚠️ **Inferred**: It is assumed that the External Factors pipeline operates entirely as an independent microservice, expecting downstream applications to actively query its API rather than pushing updates to a central system.
