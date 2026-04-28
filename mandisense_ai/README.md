# MandiSense AI (Path A)

An adaptive multi-agent intelligent system for agricultural mandi price forecasting.

## Path A Improved Architecture
Built using Clean Architecture principles, ensuring modularity, testability, and separation of concerns. The system is designed specifically to handle messy, incomplete, and delayed data from sources like Agmarknet.

### Path A Specifics
- **Meta-Ensemble Ready**: Introduces a unified `AgentOutput` schema ensuring all agents (Seasonality, ArrivalVolume, ExternalIntelligence) emit standard confidences and predictions safely before aggregation.
- **Strict Configuration**: Powered by `Pydantic v2` for rigorous type-safety and robust multi-factor models.

## Folder Structure & Purpose
- `api/` - Future FastAPI endpoints layer
- `config/` - Pydantic settings and YAML defaults (Unified schema configured here)
- `core/` - Core business logic
  - `agents/` - Home for individual forecasting agents
- `data/` - Data access layer (Repository pattern)
- `ensemble/` - Will contain the meta-ensemble architecture to receive `AgentOutput` list and determine dynamic weights
- `explainability/` - Model interpretability logic (SHAP/LIME)
- `frontend/` - Future Streamlit dashboard application
- `models/` - Serialized machine learning artifacts directory
- `tests/` - Pytest suites configuration
- `utils/` - Shared helpers, logging, and custom exceptions

## Setup Instructions

1. **Clone the repository and create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install project dependencies:**
   ```bash
   pip install -e .
   ```

3. **Configure the environment:**
   Copy `.env.example` to `.env`.
   ```bash
   cp .env.example .env
   ```

4. **Run the initial orchestration process:**
   ```bash
   python main.py
   ```

## Development Flow & Next Phases
Phase 0 currently implements the foundational structures. Future phases will introduce the distinct Multi-Agent modules into `core/agents/`, implement the dynamic weighting in `ensemble/`, and connect to production datasources via `data/`.
