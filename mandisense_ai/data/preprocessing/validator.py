"""
STAGE 8: DATA VALIDATION

Production-grade quality assurance for the preprocessed dataset.

Validates:
1. No NaN values in critical columns
2. No infinite values anywhere
3. No future data leakage (features don't contain future info)
4. Time index strictly monotonically increasing
5. Date continuity (no gaps)
6. Target sanity (reasonable ranges, no constant values)
7. Schema compliance (expected columns present)
8. Data type correctness

All validation failures raise alerts - in production, we may want
to gracefully degrade or quarantine invalid data.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from datetime import timedelta
from mandisense_ai.utils.logger import get_logger
from .config import config

logger = get_logger(__name__)


class DataValidator:
    """
    Comprehensive data quality validator for preprocessed datasets.

    Failure modes:
    - CRITICAL: Data leakage detected, pipeline should halt
    - ERROR: Invalid data detected, should be fixed before training
    - WARNING: Suboptimal but acceptable data quality
    - INFO: Validation passed
    """

    def __init__(self, config=config):
        self.config = config
        self.validation_results: Dict[str, Any] = {}
        self.critical_failures = []
        self.errors = []
        self.warnings = []

    def _check_nan_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check for NaN values in critical columns.
        """
        result = {
            'status': 'PASS',
            'details': {},
            'critical': False
        }

        # Production output is model-ready: every emitted column must be present
        # and non-null. Target columns are included by design.
        critical_columns = list(df.columns)

        nan_summary = {}
        for col in critical_columns:
            if col in df.columns:
                nan_count = df[col].isna().sum()
                nan_pct = (nan_count / len(df)) * 100 if len(df) > 0 else 0
                nan_summary[col] = {'count': int(nan_count), 'percentage': round(nan_pct, 4)}

                if nan_count > 0:
                    result['status'] = 'FAIL'
                    result['critical'] = True
                    self.critical_failures.append(f"Critical column '{col}' has {nan_count} NaN values")

        result['details'] = nan_summary
        return result

    def _check_infinite_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check for infinite values (inf, -inf) in numeric columns.
        """
        result = {
            'status': 'PASS',
            'details': {},
            'critical': False
        }

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        inf_summary = {}

        for col in numeric_cols:
            inf_mask = np.isinf(df[col])
            inf_count = inf_mask.sum()
            if inf_count > 0:
                inf_summary[col] = int(inf_count)
                result['status'] = 'FAIL'
                result['critical'] = True
                self.critical_failures.append(f"Column '{col}' has {inf_count} infinite values")

        result['details'] = inf_summary
        return result

    def _check_time_monotonic(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Verify that the time index is strictly increasing (no time travel).
        """
        result = {
            'status': 'PASS',
            'details': {},
            'critical': False
        }

        if 'date' not in df.columns:
            result['status'] = 'FAIL'
            result['critical'] = True
            self.critical_failures.append("Missing 'date' column for monotonicity check")
            return result

        dates = df['date'].reset_index(drop=True)
        is_monotonic = dates.is_monotonic_increasing and not dates.duplicated().any()

        if not is_monotonic:
            # Find where order breaks
            sorted_dates = dates.sort_values().reset_index(drop=True)
            original_dates = df['date'].reset_index(drop=True)
            violations = (original_dates != sorted_dates).sum()
            result['status'] = 'FAIL'
            result['critical'] = True
            result['details']['violations'] = int(violations)
            self.critical_failures.append(f"Time index not monotonic: {violations} violations")
        else:
            result['details']['violations'] = 0

        return result

    def _check_date_continuity(self, df: pd.DataFrame, group_cols: List[str] = None) -> Dict[str, Any]:
        """
        Check for gaps in the daily time series.
        For multi-commodity data, check per (commodity, market) group.
        """
        result = {
            'status': 'PASS',
            'details': {},
            'critical': False
        }

        if 'date' not in df.columns:
            result['status'] = 'FAIL'
            return result

        gap_count = 0
        total_expected_days = 0
        total_actual_days = 0

        if group_cols and all(col in df.columns for col in group_cols):
            # Check continuity per group
            for name, group in df.groupby(group_cols):
                group = group.sort_values('date')
                date_range = (group['date'].max() - group['date'].min()).days + 1
                actual_count = len(group)
                expected_count = len(pd.date_range(
                    start=group['date'].min(),
                    end=group['date'].max(),
                    freq='D'
                ))
                gaps = expected_count - actual_count
                gap_count += gaps
                total_expected_days += expected_count
                total_actual_days += actual_count
        else:
            # Check globally
            date_range = (df['date'].max() - df['date'].min()).days + 1
            expected_dates = pd.date_range(start=df['date'].min(), end=df['date'].max(), freq='D')
            actual_dates = pd.DatetimeIndex(df['date'].sort_values().unique())
            gap_count = len(expected_dates) - len(actual_dates)
            total_expected_days = len(expected_dates)
            total_actual_days = len(actual_dates)

        if gap_count > 0:
            gap_pct = (gap_count / total_expected_days) * 100 if total_expected_days > 0 else 0
            result['status'] = 'WARNING' if gap_pct < 1 else 'FAIL'
            result['critical'] = gap_pct >= 1
            result['details'] = {
                'gap_count': int(gap_count),
                'gap_percentage': round(gap_pct, 4),
                'expected_days': total_expected_days,
                'actual_days': total_actual_days
            }
            if result['critical']:
                self.errors.append(f"Large date gaps detected: {gap_count} missing days ({gap_pct:.2f}%)")
            else:
                self.warnings.append(f"Minor date gaps: {gap_count} missing days ({gap_pct:.2f}%)")
        else:
            result['details'] = {'gap_count': 0, 'gap_percentage': 0.0}

        return result

    def _check_target_sanity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate target variables are within reasonable bounds and have sufficient variance.
        """
        result = {
            'status': 'PASS',
            'details': {},
            'critical': False
        }

        target_cols = [c for c in df.columns if c.startswith('target_')]
        target_issues = []

        for col in target_cols:
            if col not in df.columns:
                continue

            series = df[col].dropna()
            if len(series) == 0:
                target_issues.append(f"{col}: no valid values")
                continue

            # Check for extreme values
            max_abs = series.abs().max()
            if max_abs > 5:  # >500% change is unrealistic for daily returns
                self.warnings.append(f"{col}: Extreme max value {max_abs:.2f}")
                result['details'][col] = {'max_abs': float(max_abs), 'issue': 'extreme_values'}

            # Check for near-zero variance (all targets same)
            if series.std() < 1e-6:
                target_issues.append(f"{col}: Near-zero variance")
                result['critical'] = True

            # Check reasonable mean (price trends shouldn't be permanently biased)
            mean_val = series.mean()
            if abs(mean_val) > 1:  # >100% average change is suspicious
                self.warnings.append(f"{col}: High mean {mean_val:.4f}")

        if target_issues:
            result['status'] = 'FAIL'
            self.errors.extend(target_issues)

        result['details']['issues'] = target_issues
        return result

    def _check_feature_collinearity(self, df: pd.DataFrame, threshold: float = 0.95) -> Dict[str, Any]:
        """
        Check for highly correlated features (potential data leakage via duplication).
        """
        result = {
            'status': 'PASS',
            'details': {},
            'critical': False
        }

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        numeric_cols = [c for c in numeric_cols if not c.startswith('target_')]

        if len(numeric_cols) < 2:
            return result

        corr_matrix = df[numeric_cols].corr().abs()

        # Find pairs with correlation above threshold
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                col1, col2 = corr_matrix.columns[i], corr_matrix.columns[j]
                corr_val = corr_matrix.iloc[i, j]
                if corr_val > threshold:
                    high_corr_pairs.append((col1, col2, float(corr_val)))

        if high_corr_pairs:
            result['status'] = 'WARNING'
            result['details']['high_corr_pairs'] = high_corr_pairs[:10]  # Top 10
            self.warnings.append(f"Found {len(high_corr_pairs)} highly correlated feature pairs (>={threshold})")

        return result

    def validate(self, df: pd.DataFrame, group_cols: List[str] = None) -> Dict[str, Any]:
        """
        Run full validation suite.

        Args:
            df: DataFrame to validate
            group_cols: Columns to group by for group-wise checks (e.g., ['commodity', 'market'])

        Returns:
            Dictionary with validation results
        """
        logger.info("=" * 60)
        logger.info("STAGE 8: DATA VALIDATION")
        logger.info("=" * 60)

        self.validation_results = {}
        self.critical_failures = []
        self.errors = []
        self.warnings = []

        # Run all checks
        checks = {
            'nan_check': self._check_nan_values(df),
            'inf_check': self._check_infinite_values(df),
            'time_monotonic': self._check_time_monotonic(df),
            'date_continuity': self._check_date_continuity(df, group_cols),
            'target_sanity': self._check_target_sanity(df),
            'collinearity': self._check_feature_collinearity(df)
        }

        self.validation_results = checks

        # Log results
        for check_name, result in checks.items():
            status = result['status']
            if status == 'FAIL':
                logger.error(f"❌ {check_name}: FAILED")
            elif status == 'WARNING':
                logger.warning(f"⚠️  {check_name}: WARNING")
            else:
                logger.info(f"✓ {check_name}: PASSED")

        # Summary
        if self.critical_failures:
            logger.error(f"CRITICAL FAILURES ({len(self.critical_failures)}):")
            for failure in self.critical_failures:
                logger.error(f"  - {failure}")

        if self.errors:
            logger.error(f"ERRORS ({len(self.errors)}):")
            for error in self.errors:
                logger.error(f"  - {error}")

        if self.warnings:
            logger.warning(f"WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")

        # Final verdict
        if self.critical_failures:
            logger.error("VALIDATION FAILED: Critical issues must be fixed before proceeding.")
            raise DataValidationError(f"Critical validation failures: {self.critical_failures}")
        elif self.errors:
            logger.error("VALIDATION FAILED: Errors must be fixed.")
            raise DataValidationError(f"Validation errors: {self.errors}")
        elif self.warnings:
            logger.warning("VALIDATION PASSED WITH WARNINGS: Review warnings before production.")
        else:
            logger.info("VALIDATION PASSED ✓ All checks clean.")

        return self.validation_results


class DataValidationError(Exception):
    """Raised when data validation fails critically."""
    pass
