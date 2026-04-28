# MandiSense AI - Agent Execution Guide

## Quick Start

### Option 1: Batch File (Windows) - **RECOMMENDED FOR SIMPLICITY**
```cmd
run_agents.bat tomato kolar
run_agents.bat onion lasalgaon
run_agents.bat potato agra
```

### Option 2: PowerShell Directly
```powershell
.\run_agents.ps1 tomato kolar
.\run_agents.ps1 onion lasalgaon
```

### Option 3: Python Script (Cross-Platform)
```bash
# From project root after activating venv
python run_agents.py tomato kolar
python run_agents.py onion lasalgaon
python run_agents.py potato agra
```

### Option 4: Manual Command (Advanced)
```powershell
# Activate venv first
.\.venv\Scripts\Activate.ps1

# Then run
python run_agents.py tomato kolar
```

---

## Available Commodities & Mandis

| Commodity | Mandi |
|-----------|-------|
| tomato | kolar |
| onion | lasalgaon |
| potato | agra |
| garlic | neemuch |
| chillies | guntur |

---

## What Gets Executed

Both agents run and output JSON:

1. **Seasonality Agent** - produces seasonal trends, festival adjustments, drift warnings
2. **Arrival Volume Agent** - produces supply stress, elasticity, price predictions

---

## Output Format

```json
{
  "SEASONALITY AGENT OUTPUT": {
    "agent": "Seasonality",
    "commodity": "tomato",
    "mandi": "kolar",
    "confidence": 0.75,
    "expected_30d_return": 3.45,
    "return_std": 2.1,
    "season_strength": 0.82,
    ...
  },
  "ARRIVAL VOLUME AGENT OUTPUT": {
    "agent": "ArrivalVolume",
    "commodity": "tomato", 
    "mandi": "kolar",
    "expected_7d_price_change_pct": 1.23,
    "supply_stress_score": 0.65,
    "supply_regime": "Normal",
    ...
  }
}
```

---

## Troubleshooting

### Error: "No processed data available"
- **Cause**: Missing parquet file in `data/processed/`
- **Fix**: Run Phase 1 data pipeline first to generate feature files
  ```bash
  python data/preprocessing/pipeline.py
  ```

### Error: "Virtual environment not found"
- **Cause**: `.venv` folder missing
- **Fix**: Create and activate venv
  ```bash
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

### ModuleNotFoundError
- **Fix**: Ensure you're in the project root directory
  ```bash
  cd d:\BMS COLL\PROJECT\Mandi-AI
  ```

---

## Running from Any Directory

If you want to run from anywhere, add to your PATH or use absolute path:
```powershell
& 'd:\BMS COLL\PROJECT\Mandi-AI\run_agents.bat' tomato kolar
```

---

## Next Steps

After getting JSON outputs:
1. Review `metadata` field for model confidence
2. Check `explainable_features` for feature contributions
3. Use outputs to feed into meta-ensemble (Phase 4)
4. Dashboard will visualize these outputs (Phase 5)
