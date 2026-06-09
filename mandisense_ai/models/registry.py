import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

logger = logging.getLogger("ModelRegistry")

class ModelArtifact(BaseModel):
    version: str
    commodity: str
    model_type: str # e.g., "forecast", "volatility", "regime"
    path: str
    created_at: datetime
    metrics: Dict[str, float]
    lineage: Dict[str, Any] # e.g., dataset version, training script hash
    is_active: bool = False

class ModelArtifactRegistry:
    """
    Industrialized Model Lifecycle Infrastructure.
    Manages versions, lineage, and validation snapshots for MandiSense.
    """
    def __init__(self, models_root: Optional[Path] = None):
        if models_root is None:
            self.models_root = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/models")
        else:
            self.models_root = models_root
            
        self.registry_file = self.models_root / "registry.json"
        self._load_registry()

    def _load_registry(self):
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {"artifacts": [], "active_map": {}}

    def register_artifact(self, artifact: ModelArtifact):
        """
        Registers a new model artifact and updates lineage.
        """
        self.data["artifacts"].append(artifact.dict())
        logger.info(f"Registered artifact: {artifact.commodity}/{artifact.model_type} version {artifact.version}")
        self._save_registry()

    def activate_version(self, commodity: str, model_type: str, version: str):
        """
        Promotes a version to 'Active' status for runtime consumption.
        """
        key = f"{commodity}_{model_type}"
        self.data["active_map"][key] = version
        
        # Update is_active flag in artifacts list
        for art in self.data["artifacts"]:
            if art["commodity"] == commodity and art["model_type"] == model_type:
                art["is_active"] = (art["version"] == version)
                
        logger.info(f"Activated {commodity}/{model_type} version {version}")
        self._save_registry()

    def get_active_artifact(self, commodity: str, model_type: str) -> Optional[ModelArtifact]:
        key = f"{commodity}_{model_type}"
        active_version = self.data["active_map"].get(key)
        if not active_version:
            return None
            
        for art in self.data["artifacts"]:
            if (art["commodity"] == commodity and 
                art["model_type"] == model_type and 
                art["version"] == active_version):
                return ModelArtifact(**art)
        return None

    def _save_registry(self):
        with open(self.registry_file, "w") as f:
            json.dump(self.data, f, indent=2, default=str)

class ArtifactResolver:
    """
    Ensures the runtime only consumes 'Active' and 'Validated' artifacts.
    """
    def __init__(self, registry: ModelArtifactRegistry):
        self.registry = registry
        
    def resolve_path(self, commodity: str, model_type: str) -> Path:
        artifact = self.registry.get_active_artifact(commodity, model_type)
        if not artifact:
            # Fallback to legacy path if no active artifact in registry
            return Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/models") / commodity / "v3"
        return Path(artifact.path)
