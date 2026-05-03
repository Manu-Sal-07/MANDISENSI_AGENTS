"""
Production-Grade Preprocessing Pipeline for MandiSense AI.

This module provides a comprehensive, leak-proof data preprocessing pipeline
for agricultural price forecasting. It transforms raw Agmarknet CSVs into
model-ready datasets with rich feature sets.

Pipeline Stages:
1. Schema Normalization - Standardize columns, enforce types, deduplicate
2. Data Cleaning - Missing value imputation, continuous daily index
3. Outlier Handling - Winsorization + anomaly flags
4. Base Feature Engineering - Temporal, lag, rolling, return features
5. Agent-Specific Features - Specialized indicators for Seasonality & Arrival agents
6. Target Engineering - Forward-looking targets (7d, 30d) with NO LEAKAGE
7. Data Validation - Comprehensive quality checks
8. Storage - Parquet format with schema preservation

Usage:
    from data.preprocessing import PreprocessingPipeline

    pipeline = PreprocessingPipeline()
    results = pipeline.run()

    # Or process a single commodity-market pair
    result = pipeline.run_single('onion', 'bengaluru')
"""

from .pipeline import (
    PreprocessingPipeline,
    run_pipeline,
    run_single,
    PipelineStage,
    DataValidationError
)

from .schema_normalizer import SchemaNormalizer
from .enhanced_cleaner import DataCleaner
from .outlier_handler import OutlierHandler
from .feature_engineering import BaseFeatureEngineer
from .agent_features import AgentFeatureGenerator
from .target_engineer import TargetEngineer
from .validator import DataValidator, DataValidationError
from .config import PreprocessingConfig, config

__all__ = [
    # Main pipeline
    'PreprocessingPipeline',
    'run_pipeline',
    'run_single',
    'PipelineStage',
    'DataValidationError',

    # Individual components
    'SchemaNormalizer',
    'DataCleaner',
    'OutlierHandler',
    'BaseFeatureEngineer',
    'AgentFeatureGenerator',
    'TargetEngineer',
    'DataValidator',

    # Configuration
    'PreprocessingConfig',
    'config'
]

__version__ = '1.0.0'
