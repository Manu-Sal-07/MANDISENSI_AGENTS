from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, List
import yaml
import os
from pathlib import Path

# Why: Using Pydantic for configuration gives us type safety, validation, 
# and easy integration with environment variables.

BASE_DIR = Path(__file__).resolve().parent.parent


def resolve_path(path_str: str) -> str:
    path_obj = Path(path_str)
    if path_obj.is_absolute():
        return str(path_obj)
    package_path = BASE_DIR / path_obj
    return str(package_path) if package_path.exists() else str(path_obj)


class AppConfig(BaseModel):
    name: str = "MandiSense AI"
    environment: str = "development"
    debug: bool = False

class DataConfig(BaseModel):
    commodities: list[str] = ["onion", "tomato"]
    mandis: list[str] = ["bengaluru", "mumbai", "delhi"]
    missing_value_tolerance: float = 0.2

class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "json"
    file_path: str = "logs/mandisense.log"

class PathsConfig(BaseModel):
    data_dir: str = "data"
    raw_data: str = "data/raw"
    processed_data: str = "data/processed"
    models_dir: str = "models"

    def resolve(self) -> "PathsConfig":
        return PathsConfig(
            data_dir=resolve_path(self.data_dir),
            raw_data=resolve_path(self.raw_data),
            processed_data=resolve_path(self.processed_data),
            models_dir=resolve_path(self.models_dir),
        )


class EnsembleConfig(BaseModel):
    # Meta-ensemble readiness config
    activation_threshold: float = 0.5
    default_weight: float = 0.33

class ModelBreakdown(BaseModel):
    prediction: float
    weight: float

# unified agent output schema
class AgentOutput(BaseModel):
    """Standardized AgentOutput for Meta-Ensemble integration."""
    agent_name: str
    prediction: float
    confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    model_breakdown: Dict[str, ModelBreakdown] = Field(default_factory=dict)

class Settings(BaseSettings):
    app: AppConfig = AppConfig()
    data: DataConfig = DataConfig()
    logging: LoggingConfig = LoggingConfig()
    paths: PathsConfig = PathsConfig()
    ensemble: EnsembleConfig = EnsembleConfig()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @classmethod
    def load_config(cls, config_path: str = "config/config.yaml") -> "Settings":
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                yaml_data = yaml.safe_load(f) or {}
            settings = cls(**yaml_data)
        else:
            settings = cls()
        settings.paths = settings.paths.resolve()
        return settings

settings = Settings.load_config()
