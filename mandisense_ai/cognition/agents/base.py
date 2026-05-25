from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AgentSignal(BaseModel):
    agent_id: str
    commodity: str
    mandi_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Cognitive Outputs
    signal_type: str # e.g., "forecast", "volatility", "risk"
    value: Any
    confidence: float
    urgency: float # 0.0 to 1.0
    
    # Reasoning
    recommendation: str
    supporting_evidence: str
    uncertainty_flags: List[str] = []
    contradictions: List[str] = []
    
    # Metadata
    metadata: Dict[str, Any] = {}

class CognitiveAgent(ABC):
    """
    Base class for institutional cognitive agents.
    Each agent is a bounded cognitive system with its own purpose and memory.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    @abstractmethod
    async def perceive_and_reason(self, commodity: str, mandi_id: str, context: Dict[str, Any]) -> AgentSignal:
        """
        The core cognitive loop: Perceive context -> Reason -> Emit Signal.
        """
        pass

class AgentRegistry:
    """
    Manages the ecosystem of cognitive agents.
    """
    def __init__(self):
        self.agents: Dict[str, CognitiveAgent] = {}

    def register(self, agent: CognitiveAgent):
        self.agents[agent.agent_id] = agent
        
    def get_agent(self, agent_id: str) -> Optional[CognitiveAgent]:
        return self.agents.get(agent_id)

    def list_agents(self) -> List[str]:
        return list(self.agents.keys())
