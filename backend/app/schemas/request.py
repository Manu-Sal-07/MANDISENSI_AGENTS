from pydantic import BaseModel
from typing import Optional

class PredictRequest(BaseModel):
    commodity: str
    mandi_id: str
    date: Optional[str] = None

class DecisionRequest(BaseModel):
    commodity: str
    mandi_id: str
    date: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
