from __future__ import annotations

import argparse
from datetime import datetime
from typing import Optional

from config.settings import settings
from data.repository import DataRepository
from core.agents.seasonality.training.train_seasonality import train_seasonality_models
from utils.logger import get_logger

logger = get_logger(__name__)


def train_seasonality_model(commodity: str, mandi: str, models_dir: Optional[str] = None) -> None:
    logger.info(f"Starting offline seasonality training for {commodity}/{mandi}")
    repo = DataRepository()
    df = repo.get_processed_data(commodity, mandi)
    if df.empty:
        raise ValueError(f"No processed historical data available for {commodity}/{mandi}")

    result_bundle = train_seasonality_models(df, commodity=commodity, mandi=mandi)
    metadata = result_bundle["metadata"]
    logger.info(
        "Completed seasonality training for %s/%s: confidence=%.4f",
        commodity,
        mandi,
        metadata["confidence"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline seasonality training utility for MandiSense.")
    parser.add_argument("--commodity", type=str, help="Commodity name to train for")
    parser.add_argument("--mandi", type=str, help="Mandi name to train for")
    parser.add_argument("--all", action="store_true", help="Train all configured commodity/mandi combinations")
    parser.add_argument("--models-dir", type=str, default=None, help="Optional override for the models directory")
    args = parser.parse_args()

    if not args.all and (not args.commodity or not args.mandi):
        parser.error("Either --all or both --commodity and --mandi must be provided")

    if args.all:
        for commodity in settings.data.commodities:
            for mandi in settings.data.mandis:
                train_seasonality_model(commodity, mandi, models_dir=args.models_dir)
    else:
        train_seasonality_model(args.commodity, args.mandi, models_dir=args.models_dir)

    logger.info("Seasonality offline training complete: %s", datetime.utcnow().isoformat())


if __name__ == "__main__":
    main()
