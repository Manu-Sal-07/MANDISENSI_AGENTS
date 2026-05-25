"""
Feedback Store for Ensemble Predictions.

Stores prediction history, actuals, and computes rolling performance
to enable dynamic EMA weighting of models.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    from mandisense_ai.config.settings import settings
except ImportError:
    from config.settings import settings
try:
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackStore:
    """Stores and retrieves historical model performance for dynamic weighting."""

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            # Fallback to data/ensemble if settings doesn't have it
            try:
                base = Path(settings.paths.data)
            except Exception:
                base = Path("data")
            self.storage_dir = base / "ensemble"
        else:
            self.storage_dir = storage_dir

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.storage_dir / "prediction_history.jsonl"

    def log_prediction(
        self,
        agent_type: str,
        commodity: str,
        mandi: str,
        model_name: str,
        target_date: str,
        prediction: float,
        actual: Optional[float] = None
    ):
        """Log a new prediction. If actual is provided, error is computed immediately."""
        error = None
        if actual is not None and actual != 0:
            error = abs(prediction - actual) / abs(actual)

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_date": target_date,
            "agent_type": agent_type,
            "commodity": commodity,
            "mandi": mandi,
            "model_name": model_name,
            "prediction": prediction,
            "actual": actual,
            "error": error
        }

        with open(self.file_path, "a") as f:
            f.write(json.dumps(record) + "\n")

    def update_actuals(
        self,
        agent_type: str,
        commodity: str,
        mandi: str,
        target_date: str,
        actual: float
    ):
        """Update historical records with actuals once they become available."""
        if not self.file_path.exists():
            return

        updated_records = []
        with open(self.file_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if (record["agent_type"] == agent_type and
                    record["commodity"] == commodity and
                    record["mandi"] == mandi and
                    record["target_date"] == target_date and
                    record["actual"] is None):
                    
                    record["actual"] = actual
                    if actual != 0:
                        record["error"] = abs(record["prediction"] - actual) / abs(actual)
                
                updated_records.append(record)

        with open(self.file_path, "w") as f:
            for r in updated_records:
                f.write(json.dumps(r) + "\n")

    def get_rolling_mape(
        self,
        agent_type: str,
        commodity: str,
        mandi: str,
        model_name: str,
        n_days: int = 30
    ) -> Optional[float]:
        """Compute rolling MAPE for a specific model over the last N days."""
        if not self.file_path.exists():
            return None

        cutoff_date = (datetime.utcnow() - timedelta(days=n_days)).isoformat()
        errors = []

        with open(self.file_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if (record["agent_type"] == agent_type and
                    record["commodity"] == commodity and
                    record["mandi"] == mandi and
                    record["model_name"] == model_name and
                    record["error"] is not None and
                    record["timestamp"] >= cutoff_date):
                    
                    errors.append(record["error"])

        if not errors:
            return None

        return float(np.mean(errors))
