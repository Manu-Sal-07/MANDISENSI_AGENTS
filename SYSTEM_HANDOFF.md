# SYSTEM_HANDOFF.md

# 🧠 1. SYSTEM OVERVIEW

* **What problem this system solves**: Agricultural commodity prices are highly volatile and influenced by a complex interplay of long-term cycles, sudden supply gluts, and unpredictable external events like weather or policy changes. This system aims to accurately predict short-term and medium-term price movements by untangling these distinct drivers.
* **Why a multi-agent approach was chosen**: Price movements are not caused by a single factor. By separating the system into specialized, autonomous agents, each component can focus entirely on one specific class of market driver (e.g., one agent only looks at long-term seasons, another only looks at daily supply shocks). This prevents noisy daily data from corrupting long-term trend analysis and makes the system modular, explainable, and easier to debug.
* **Why ML/statistical methods were used instead of LLMs**: Commodity pricing requires precise, deterministic, and mathematically sound forecasting based on structured time-series data. Traditional machine learning and advanced statistical models excel at finding mathematical correlations, calculating variance, and projecting numerical trends, whereas Large Language Models (LLMs) are prone to hallucinating numerical forecasts and lack the rigorous statistical bounds necessary for financial or agricultural prediction.
* **High-level flow of the system**: Raw historical market data and textual news feeds enter the system. This data is cleaned, structured, and routed to the appropriate specialized agents. Each agent independently analyzes the data, extracts relevant features, runs internal predictive models, and produces an isolated forecast along with a confidence metric. These outputs are standardized and readied for a final aggregation layer.

---

# 🤖 2. AGENT ARCHITECTURE OVERVIEW

* **Why the system is divided into 3 agents**: The primary drivers of commodity prices fall into three natural categories: predictable time-based cycles, physical market supply dynamics, and unpredictable external shocks. Assigning a dedicated agent to each category ensures that the mathematical modeling approach is perfectly tailored to the nature of the data it processes.
* **What responsibility each agent handles**:
  * **Seasonality Agent**: Analyzes deep historical data to identify long-term trends, recurring annual cycles, and festival-driven demand spikes.
  * **Arrival Volume Agent**: Focuses strictly on the immediate, physical supply of commodities arriving at the market to detect sudden gluts or shortages.
  * **External Factors Agent**: Monitors unstructured external data, such as news articles regarding government policy changes, export bans, or weather events, to quantify their immediate market impact.

---

# 🔶 3. SEASONALITY AGENT (DETAILED)

### 🎯 Purpose
* **What this agent is responsible for predicting**: It predicts the expected percentage change in commodity prices over a 30-day horizon, driven purely by historical cycles, overall market trends, and predictable calendar events.

### 🧠 Approach
* **How seasonal patterns are extracted**: The agent uses statistical time-series decomposition to break historical prices down into three parts: the fundamental underlying trend, the repeating seasonal wave, and random market noise. It mathematically determines whether the seasonal pattern is strong enough to rely on.
* **How trends are identified**: By isolating the fundamental trend from the daily noise, the agent calculates the recent gradient (slope) of the market. It uses this slope to classify the current market phase as actively ascending, actively descending, peaking, or troughing.
* **How festival effects are incorporated**: The agent cross-references historical dates with a known calendar of festivals. It calculates the exact historical percentage premium that prices typically experience during these festival windows compared to normal days, isolating this effect from general seasonality.
* **How structural changes (drift) are handled**: Markets evolve. The agent continuously compares the seasonal pattern of the last three years against the entire available historical baseline. If the recent pattern deviates drastically from the historical norm, the agent flags a structural drift warning and automatically lowers its confidence in the forecast.

### 🧪 Features Used
* **Time-based features**: The day of the week, the month, and boolean flags indicating whether a major festival is occurring.
* **Lag values**: Historical prices from 1, 7, and 14 days ago to capture immediate past behavior.
* **Rolling statistics**: The 7-day rolling average of prices to smooth out daily volatility.
* **Volatility indicators**: Proxies for recent market volatility and 7-day momentum to give the models context on how violently the market is currently moving.

### 🤖 Models Used
* **Types of models used**: A diverse pool combining classical linear regressions, advanced tree-based ensembles (like Random Forests and Gradient Boosters), and traditional statistical forecasting models.
* **Why multiple models are used**: Different algorithms have different blind spots. Linear models capture steady, proportional trends beautifully but fail on sudden spikes. Tree-based models handle complex, non-linear interactions well but struggle to extrapolate beyond historical maximums.
* **How they differ in capturing patterns**: Some models are heavily regularized to ignore noise, others are designed to aggressively fit recent data, and some use purely auto-regressive logic (relying only on past prices). This diversity ensures that at least one model is well-suited to the current market condition.

### ⚙️ Internal Ensemble
* **How multiple models are combined**: The agent does not rely on a single model. It evaluates all models simultaneously using a rigorous cross-validation process that mimics real-world forecasting. 
* **What role each model plays**: Models that perform well on recent, similar historical periods are given higher authority, while models that perform poorly are actively ignored.
* **How final prediction is formed**: The agent calculates an inverse-error weight for each model (meaning lower error equals exponentially higher weight). Models contributing less than a minimum threshold are dropped entirely. The final prediction is a weighted sum of the surviving models' forecasts. Furthermore, these weights are dynamically adjusted based on the current market regime (e.g., boosting certain models if a festival is active).

### 📤 Output
* **What this agent outputs**: A structured response containing the prediction, a confidence score, and extensive explainable metadata.
* **Meaning of each output component**: 
  * *Prediction*: The expected fractional return (percentage change).
  * *Confidence*: A value penalized by the average error of the models and further reduced if structural drift is detected.
  * *Metadata*: Includes expected return standard deviation, the probability of a positive price movement, the strength of the seasonal signal, the current cycle phase, and a breakdown of which models contributed to the final number.
* **Prediction horizon**: 30 days.

### 🔁 End-to-End Flow
* **data → processing → modeling → output**: The agent ingests raw market data, interpolates missing values, and merges festival dates. It performs statistical decomposition to extract trend and seasonality, checking for structural drift. It engineers lag and rolling features. It then triggers its internal ensemble engine, which trains, evaluates, and dynamically weights all models. Finally, it projects 30 days into the future sequentially, calculates statistical return metrics, logs its internal state, and emits the final standardized output.

---

# 🔶 4. ARRIVAL VOLUME AGENT (DETAILED)

### 🎯 Purpose
* **What this agent is responsible for predicting**: It predicts short-term, 7-day price movements explicitly driven by the physical supply of commodities arriving at the market and the resulting supply stress.

### 🧠 Approach
* **How supply impacts price**: The core economic principle is that an oversupply of physical goods depresses prices, while a sudden shortage causes prices to spike.
* **How elasticity is calculated**: Not all commodities react to supply changes with the same intensity. The agent calculates a rolling price elasticity metric by performing a continuous linear regression between the logarithm of prices and the logarithm of arrival volumes, determining exactly how sensitive the price currently is to supply changes.
* **How supply regimes are identified**: The agent computes a composite "supply stress score" based on how far current arrivals deviate from the 30-day average, how they compare year-over-year, and the momentum of recent declines. This score categorizes the market into regimes: Squeeze, Tightening, Oversupply, or Normal.
* **How short-term shocks are captured**: If the deviation of daily arrivals from the expected norm exceeds a massive threshold, the agent flags an active supply shock, which can be used to dynamically alter how the models are weighted.

### 🧪 Features Used
* **Arrival deviations**: Percentage difference between today's arrivals and the 30-day moving average, as well as year-over-year comparisons.
* **Trends**: Rolling 7-day and 30-day mean arrival volumes.
* **Momentum**: The mathematical slope of arrivals over the last 14 days, and a count of consecutive days where supply has declined.
* **Lag relationships**: Historical arrival volumes and prices from 1 and 7 days ago, plus the dynamically calculated rolling elasticity.

### 🤖 Models Used
* **Types of models used**: A distinct pool of regression models, including advanced tree-based algorithms, regularized linear models, gradient boosters optimized for outlier robustness, and simple baselines.
* **Why multiple models are used**: Supply shocks often create extreme, non-linear price spikes. Tree-based models and gradient boosters handle these shocks well, while linear models provide stability during normal, elastic supply-demand periods.

### ⚙️ Internal Ensemble
* **How multiple models are combined**: Identical to the Seasonality Agent, it utilizes a rigorous walk-forward cross-validation process to evaluate every model in its pool.
* **How final prediction is formed**: It computes inverse-error weights, drops underperforming models, and applies dynamic regime-based adjustments (e.g., favoring gradient boosters during a detected supply shock). The final forecast is the weighted average of the active models.

### 📤 Output
* **What predictions are generated**: The expected percentage change in price over the next 7 days.
* **What additional signals are included**: A confidence score, the calculated supply stress score, the active supply regime, the elasticity coefficient, a flag indicating if a supply shock is occurring, and the historical lag time that shows the highest correlation between arrival changes and price changes.

### 🔁 End-to-End Flow
* **data → processing → modeling → output**: The agent ingests market data, calculates rolling elasticity, and engineers deviation and momentum features. It computes the target 7-day future price change for training. It evaluates its model pool via cross-validation, adjusts weights based on detected supply regimes, and generates a forecast for the current day. It then calculates confidence bounds and outputs a standardized response containing the prediction and detailed supply metrics.

---

# 🔶 5. EXTERNAL FACTORS AGENT (DETAILED)

### 🎯 Purpose
* **What this agent is responsible for predicting**: It quantifies the immediate, localized market impact of external unstructured events—such as government policy shifts, weather anomalies, or supply chain disruptions.

### 🧠 Pipeline Explanation
1. **Extracting information**: The agent scans incoming textual news feeds, looking for specific keywords associated with the target commodities and predefined event categories (like export bans, droughts, or duty reductions).
2. **Cleaning and normalizing**: It extracts the core entities and standardizes the event format, assigning a confidence score based on how strongly the text matched the predefined keywords or phrases.
3. **Removing duplicate signals**: It deduplicates identical events reported by multiple sources on the same day to prevent double-counting.
4. **Assigning impact scores using rules**: It uses a hardcoded heuristic rule engine to assign a baseline mathematical weight to specific types of events based on domain knowledge.
5. **Applying time decay**: News loses relevance over time. The agent applies an exponential mathematical decay function to the assigned impact score, meaning older events exert progressively less influence on the current market state until they are ignored completely.
6. **Aggregating into a final signal**: The decayed scores of all currently active events for a specific commodity are summed together to create an aggregate rule-based score.

### 🤖 Hybrid Intelligence
* **Rule-based scoring**: Provides an immediate, deterministic baseline score using known, pre-calibrated weights for specific events.
* **ML-based scoring**: An alternative, data-driven mechanism that attempts to predict the impact score by evaluating engineered features derived from the event metadata.
* **Causal reasoning**: A sophisticated layer that attempts to verify the true impact of an event by analyzing historical data. It isolates the event date, estimates what the price mathematically should have been without the event, and measures the actual variance to compute a verified causal impact score.
* **How these are combined**: The final intelligence layer adaptively blends the rule-based score, the ML-based score, and the causal reasoning score using predefined fractional weights. This provides a highly robust final metric that doesn't rely solely on hardcoded rules or black-box machine learning.

### 📤 Output
* **Final score**: A normalized numerical value bounded strictly between -1.0 (indicating a severe negative impact on price) and 1.0 (indicating a severe positive impact).
* **Confidence**: A metric representing the certainty of the signal, derived from the number of corroborating news sources, the strength of the text matches, and the variance observed in the causal analysis.
* **Reasoning**: A human-readable payload detailing exactly which events contributed to the score, the overarching market trend direction (e.g., bullish, bearish, neutral), and whether any high-severity alerts should be raised.

### ⚙️ How it runs
* **Continuous vs batch behavior**: Unlike the other agents, this agent operates asynchronously as a continuous background service, utilizing independent threads to constantly parse news and update its internal state.
* **How outputs are accessed**: Because it runs continuously, it stores its latest calculated intelligence in an internal cache and exposes it via a live API endpoint, allowing other systems or users to request the latest external factor score at any time.

---

# 🔄 6. HOW THE AGENTS WORK TOGETHER

* **How all three agents are used together**: Currently, the system is highly modular. The three agents operate as independent domain experts. The Seasonality and Arrival agents analyze numerical market data, while the External Factors agent analyzes textual news.
* **Whether they run in parallel or sequence**: They operate entirely in parallel. The Seasonality and Arrival agents are executed on-demand via orchestration scripts to process the latest daily data, while the External Factors agent runs continuously in the background.
* **How their outputs are currently used**: The outputs of the agents are generated independently. They each produce a standardized payload containing their distinct predictions, confidence metrics, and domain-specific explanations. These outputs are logged and available for review, serving as three separate pillars of market intelligence.

---

# 🧩 7. CURRENT ENSEMBLE STATE

* **Whether agent outputs are combined or not**: The outputs of the three main agents are **not** currently combined into a single, unified mathematical prediction.
* **What exists today**: Within each agent, a highly robust internal ensemble already exists. The Seasonality and Arrival agents successfully evaluate, weight, and combine multiple predictive models internally to produce their single domain-specific forecast. Furthermore, all agents have been successfully refactored to emit a strictly standardized output schema, explicitly designed to prepare them for a higher-level aggregation.
* **How outputs are currently consumed**: The outputs are logged to internal feedback systems and the terminal. The foundational architecture for blending these outputs is prepared, but the overarching "Meta-Ensemble" layer itself is pending.

---

# 🧠 8. MODEL TRAINING & EXECUTION

* **How models are trained**: The system uses a dynamic, inference-time training approach utilizing time-series walk-forward cross-validation. The historical data is chronologically split into multiple folds. The models are trained on past data and tested on future data in a rolling fashion to simulate real-world forecasting accuracy without data leakage.
* **When training happens**: For the Seasonality and Arrival agents, this training and evaluation process occurs dynamically every single time the agent is executed. There are no static, pre-trained model weights saved to disk. The system constantly learns and adapts to the very latest market data upon execution.
* **How predictions are generated**: Once the cross-validation process ranks the models and assigns weights based on their recent accuracy, the top-performing models are refitted one final time on the entire available historical dataset. These fully refitted models then generate forecasts for the future horizon, which are combined using the calculated weights to form the final prediction.

---

# 📊 9. CURRENT SYSTEM OUTPUT

* **What outputs are available right now**: The system currently provides three distinct, high-quality outputs per commodity/market pair:
  1. A 30-day expected percentage price change with confidence and seasonal metrics.
  2. A 7-day expected percentage price change with confidence and supply stress metrics.
  3. A continuous, normalized impact score (-1 to 1) based on external news and events.
* **Whether outputs are per-agent or combined**: The outputs are strictly per-agent and isolated.
* **How they can be interpreted**: A user or analyst must review the outputs holistically. The Seasonality forecast provides the long-term expected trajectory. The Arrival forecast highlights immediate, short-term volatility risks based on physical supply. The External Factors score acts as an overlay, indicating whether sudden news or policy changes are likely to disrupt the mathematical trends predicted by the first two agents.

---

# 🚧 10. CURRENT SYSTEM STATE

* **What is fully implemented**: 
  * The core internal logic, data processing, and feature engineering for all three agents.
  * The robust internal cross-validation and ensembling engines within the Seasonality and Arrival agents.
  * The dynamic regime detection and weight adjustment mechanics.
  * The NLP extraction, heuristic scoring, and API serving layer for the External Factors agent.
  * The standardization of all agent output schemas.
* **What is partially implemented**: 
  * The causal inference engine within the External Factors agent is partially implemented; it currently relies on an emulated, mock price feed rather than querying a live historical price database to verify causal impact.
* **What is not yet implemented**: 
  * The overarching Meta-Ensemble layer, which is intended to algorithmically blend the predictions of the three independent agents into a single definitive forecast, does not yet exist.
  * Automated hyperparameter tuning frameworks for the predictive models have not been integrated.

---

# 📌 11. SUMMARY

* **What the system currently does end-to-end**: The system successfully ingests raw market data and textual news, routes them to three highly specialized analytical agents, and generates three distinct, mathematically rigorous insights: a 30-day cyclical forecast, a 7-day supply-driven forecast, and a real-time external event impact score.
* **What kind of intelligence it already has**: It possesses advanced statistical decomposition capabilities, elastic supply-and-demand modeling, robust internal cross-validation to prevent overfitting, dynamic regime awareness to adjust to market shocks, and natural language processing to quantify news events.
* **What stage the project is in**: The project is in the **late stages of core component development**. The individual agents are fully functional, sophisticated, and standardized. The architecture is solid and mathematically sound. The system is perfectly poised for the final development phase: implementing the Meta-Ensemble layer to fuse these three pillars of intelligence into a unified predictive product.
