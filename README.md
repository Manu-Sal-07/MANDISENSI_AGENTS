# MandiSense AI 🧠🌾

Adaptive multi-agent intelligent system for agricultural mandi price forecasting.

## Overview
MandiSense AI uses a multi-agent approach to predict commodity prices by analyzing seasonality, arrival volumes, and external factors (news/weather). The system fuses these insights using a Meta-Ensemble layer.

## Quick Start (Docker)

### 1. Build and Start
```bash
docker-compose up -d --build
```

### 2. Check Health
```bash
curl http://localhost:8000/v1/health
```

### 3. Get Prediction
```bash
curl -X POST http://localhost:8000/v1/predict \
     -H "Content-Type: application/json" \
     -d '{"commodity": "tomato", "mandi": "kolar"}'
```

## Project Structure
- `api/`: FastAPI service layer.
- `mandisense_ai/`: Core ML agents and logic.
- `models/`: Trained model artifacts.
- `run_agents.py`: CLI entry point.
