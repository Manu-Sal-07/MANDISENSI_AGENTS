import sys
from pathlib import Path

# Add project root to path to find mandisense_ai
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from mandisense_ai.core.orchestrator.inference_orchestrator import InferenceOrchestrator
from mandisense_ai.core.orchestrator.decision_orchestrator import DecisionOrchestrator
from mandisense_ai.core.orchestrator.query_orchestrator import QueryOrchestrator
from mandisense_ai.core.data.data_service import MandiDataService

class ModelLoader:
    _instance = None

    def __init__(self, version="v3"):
        self.version = version
        print(f"Initializing MandiSense AI Orchestrators (Version: {self.version})...")
        self.data_service = MandiDataService.get_instance()
        # Orchestrators currently don't take version but we pass it for future-proofing
        self.inference_orch = InferenceOrchestrator()
        self.decision_orch = DecisionOrchestrator()
        self.query_orch = QueryOrchestrator()
        
    async def warm_up(self):
        await self.data_service.warm_up()
        print(f"Backend Orchestration Layer ({self.version}) Ready.")

    @classmethod
    def get_instance(cls, version="v3"):
        if cls._instance is None:
            cls._instance = cls(version=version)
        return cls._instance

# Global engines instance
engines = None

async def init_engines(version="v3"):
    global engines
    engines = ModelLoader.get_instance(version=version)
    await engines.warm_up()
