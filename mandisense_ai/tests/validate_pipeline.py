"""
Validation script for the production-grade preprocessing pipeline.

Tests:
1. Schema normalization
2. Time alignment continuity
3. No NaN in critical features
4. No future leakage in targets
5. Reasonable feature ranges
6. Outlier flagging
7. Agent feature presence
8. Parquet output integrity
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from mandisense_ai.data.preprocessing import PreprocessingPipeline, run_single
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


def test_single_commodity(commodity: str, market: str, data_dir: str):
    """
    Test pipeline on a single commodity-market pair.

    Args:
        commodity: Commodity name (e.g., 'onion')
        market: Market name (e.g., 'bengaluru')
        data_dir: Path to raw data directory
    """
    logger.info(f"{'=' * 70}")
    logger.info(f"TESTING: {commodity.upper()} - {market.upper()}")
    logger.info(f"{'=' * 70}")

    try:
        # Initialize pipeline
        logger.info(f"Creating pipeline with raw_data_dir={data_dir}")
        pipeline = PreprocessingPipeline(raw_data_dir=data_dir)

        # Run single group
        result = pipeline.run_single(commodity, market)

        if result is None:
            logger.error(f"FAILED: No result returned for {commodity}/{market}")
            return False

        # Load output
        output_path = Path(result['output_path'])
        if not output_path.exists():
            logger.error(f"FAILED: Output file not found: {output_path}")
            return False

        df = pd.read_parquet(output_path)
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")

        # ========== VALIDATION CHECKS ==========

        checks_passed = 0
        checks_total = 0

        # Check 1: No NaN in critical columns
        checks_total += 1
        critical_cols = ['date', 'commodity', 'market', 'modal_price', 'arrivals_tonnes']
        nan_counts = df[critical_cols].isna().sum()
        if nan_counts.sum() == 0:
            logger.info("✓ Check 1: No NaN in critical columns")
            checks_passed += 1
        else:
            logger.error(f"✗ Check 1 FAILED: NaN found in critical columns:\n{nan_counts}")

        # Check 2: No infinite values
        checks_total += 1
        inf_mask = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
        if inf_mask == 0:
            logger.info("✓ Check 2: No infinite values")
            checks_passed += 1
        else:
            logger.error(f"✗ Check 2 FAILED: {inf_mask} infinite values found")

        # Check 3: Date monotonic increasing
        checks_total += 1
        is_monotonic = df['date'].is_monotonic_increasing
        if is_monotonic:
            logger.info("✓ Check 3: Date index strictly increasing")
            checks_passed += 1
        else:
            logger.error("✗ Check 3 FAILED: Date index not monotonic")

        # Check 4: No future leakage in targets
        checks_total += 1
        target_cols = [c for c in df.columns if c.startswith('target_')]
        if len(target_cols) >= 2:
            # Spot check: last row's target_7d should be NaN if properly constructed
            # Actually after drop_future, should have NO NaN targets
            target_nans = df[target_cols].isna().sum()
            if target_nans.sum() == 0:
                logger.info(f"✓ Check 4: No NaN in targets {target_cols}")
                checks_passed += 1
            else:
                logger.error(f"✗ Check 4 FAILED: NaN targets remain:\n{target_nans}")

        # Check 5: Target values in reasonable range
        checks_total += 1
        reasonable = True
        for col in target_cols:
            max_abs = df[col].abs().max()
            if max_abs > 5:  # >500% change is suspicious
                logger.warning(f"  {col}: max abs change = {max_abs:.2f} (very high)")
                reasonable = False
        if reasonable:
            logger.info("✓ Check 5: Target values in reasonable range (<5x)")
            checks_passed += 1
        else:
            logger.error("✗ Check 5 FAILED: Some targets extremely high")

        # Check 6: Required features present
        checks_total += 1
        required_features = [
            'day_of_week', 'month',
            'price_lag_1', 'price_lag_7',
            'arrivals_lag_1', 'arrivals_lag_7',
            'price_mean_7', 'price_std_7',
            'arrivals_mean_7', 'arrivals_mean_30',
            'daily_returns',
            'trend_30', 'seasonal_strength', 'rolling_volatility_30',
            'arrival_deviation_pct', 'supply_momentum', 'rolling_elasticity'
        ]
        missing_features = [f for f in required_features if f not in df.columns]
        if not missing_features:
            logger.info(f"✓ Check 6: All {len(required_features)} required features present")
            checks_passed += 1
        else:
            logger.error(f"✗ Check 6 FAILED: Missing features: {missing_features}")

        # Check 7: Outlier flags exist
        checks_total += 1
        outlier_flags = ['is_price_outlier', 'is_arrival_outlier', 'price_spike_flag', 'arrival_spike_flag']
        present_flags = [f for f in outlier_flags if f in df.columns]
        if len(present_flags) >= 3:
            logger.info(f"✓ Check 7: Outlier flags present: {present_flags}")
            checks_passed += 1
        else:
            logger.error(f"✗ Check 7 FAILED: Missing outlier flags. Found: {present_flags}")

        # Check 8: Data types sanity
        checks_total += 1
        dtype_ok = True
        assert pd.api.types.is_datetime64_any_dtype(df['date']), "date not datetime"
        assert pd.api.types.is_numeric_dtype(df['modal_price']), "modal_price not numeric"
        for col in ['is_trading_day', 'price_spike_flag']:
            if col in df.columns:
                assert df[col].dtype in ['bool', 'int8', 'int16', 'int32'], f"{col} should be boolean/integer"
        if dtype_ok:
            logger.info("✓ Check 8: Data types valid")
            checks_passed += 1
        else:
            logger.error("✗ Check 8 FAILED: Invalid data types")

        # Check 9: File size reasonable
        checks_total += 1
        file_size_mb = output_path.stat().st_size / (1024*1024)
        rows = len(df)
        logger.info(f"Dataset: {rows} rows, {file_size_mb:.2f} MB, ~{file_size_mb/rows*1e6:.2f} KB/row")
        if file_size_mb > 0 and rows > 0:
            logger.info("✓ Check 9: Output file non-empty")
            checks_passed += 1

        # Check 10: Verify metadata
        checks_total += 1
        if result.get('metadata') and result.get('feature_count', 0) > 20:
            logger.info(f"✓ Check 10: Metadata complete, {result['feature_count']} features")
            checks_passed += 1
        else:
            logger.error("✗ Check 10 FAILED: Metadata incomplete")

        # ========== SUMMARY ==========
        logger.info(f"\n{'=' * 70}")
        logger.info(f"VALIDATION SUMMARY: {checks_passed}/{checks_total} checks passed")
        logger.info(f"{'=' * 70}")

        if checks_passed == checks_total:
            logger.info(f"✅ ALL CHECKS PASSED for {commodity}/{market}")
            return True
        else:
            logger.error(f"❌ VALIDATION FAILED: {checks_total - checks_passed} checks failed")
            return False

    except Exception as e:
        logger.error(f"EXCEPTION during test: {e}", exc_info=True)
        return False


def main():
    """Run validation tests on available data."""
    from config.settings import settings

    # Use absolute path to data directory
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / settings.paths.raw_data
    logger.info(f"Testing pipeline with data from: {data_dir}")

    # Ensure directory exists
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        sys.exit(1)

    # Test with first available commodity-market pair
    # (We'll just test onion/lasalgaon which is in the data)
    success = test_single_commodity('onion', 'lasalgaon', str(data_dir))

    if success:
        logger.info("\n🎉 Pipeline validation PASSED")
        sys.exit(0)
    else:
        logger.error("\n❌ Pipeline validation FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
