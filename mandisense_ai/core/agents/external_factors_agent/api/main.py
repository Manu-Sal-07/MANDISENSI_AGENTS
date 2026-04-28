from fastapi import FastAPI, HTTPException
from orchestration.cache_manager import cache_manager

app = FastAPI()

@app.get("/predict/{commodity}")
def predict_commodity(commodity: str):
    res = cache_manager.get_latest(commodity.lower())
    if res:
        return res
    raise HTTPException(status_code=404, detail="Cache miss / data unavailable")
