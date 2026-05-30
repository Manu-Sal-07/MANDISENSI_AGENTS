import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
import pyarrow.parquet as pq
from mandisense_ai.cognition.state_store import MarketMemoryStore
from mandisense_ai.cognition.replay import AnalogEngine

router = APIRouter()
memory_store = MarketMemoryStore()
analog_engine = AnalogEngine()

PROCESSED_DATA_OVERRIDES = {
    ('tomato', 'kolar_apmc'): 'tomato_kolar.parquet',
    ('onion', 'lasalgaon_apmc'): 'onion_lasalgaon.parquet',
    ('potato', 'agra_apmc'): 'potato_agra.parquet',
    ('garlic', 'neemuch_apmc'): 'garlic_neemuch.parquet',
    ('dry_chillis', 'guntur_apmc'): 'dry_chillies_guntur.parquet',
}


def _list_processed_market_options() -> List[Dict[str, str]]:
    processed_dir = Path(__file__).resolve().parent.parent / 'mandisense_ai' / 'data' / 'processed'
    markets = []
    for file_path in processed_dir.glob('*.parquet'):
        if file_path.name.endswith('_features.parquet'):
            continue

        parts = file_path.stem.split('_')
        if len(parts) < 2:
            continue

        mandi_suffix = parts[-1]
        commodity_name = '_'.join(parts[:-1])
        markets.append({
            'commodity': commodity_name,
            'mandi_id': f'{mandi_suffix}_apmc',
        })

    return sorted(markets, key=lambda item: (item['commodity'], item['mandi_id']))


def _resolve_processed_data_file(commodity: str, mandi_id: str) -> Optional[Path]:
    normalized_mandi = mandi_id.replace('_apmc', '')
    processed_dir = Path(__file__).resolve().parent.parent / 'mandisense_ai' / 'data' / 'processed'
    candidate = processed_dir / f'{commodity}_{normalized_mandi}.parquet'
    if candidate.exists():
        return candidate

    override_name = PROCESSED_DATA_OVERRIDES.get((commodity, mandi_id))
    if override_name:
        alternate = processed_dir / override_name
        if alternate.exists():
            return alternate

    commodity_matches = [
        p for p in processed_dir.glob(f'{commodity}_*.parquet')
        if not p.name.endswith('_features.parquet')
    ]
    if len(commodity_matches) == 1:
        return commodity_matches[0]

    return None


def _serialize_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)

@router.get("/state/{commodity}/{mandi_id}")
async def get_market_state(commodity: str, mandi_id: str):
    """
    Institutional endpoint for Evolving Market State.
    Includes freshness, confidence decay, and historical analogs.
    """
    state = memory_store.get_latest_state(commodity, mandi_id)
    if not state:
        raise HTTPException(
            status_code=404, 
            detail=f"Cognition not yet evolved for {commodity} @ {mandi_id}."
        )
        
    # Convert to dict for response
    state_dict = state.dict()
    
    # ── Institutional Intelligence Extension ──────────────────────────
    # We enrich the response with historical analogs
    analogs = analog_engine.find_analogs(state)
    state_dict["historical_analogs"] = analogs
    
    return state_dict

@router.get("/history/{commodity}/{mandi_id}")
async def get_market_history(commodity: str, mandi_id: str, limit: int = 50):
    """
    Retrieves the latest historical cognition snapshots for a specific commodity/mandi.
    """
    history_dir = memory_store.history_path / commodity / mandi_id
    if not history_dir.exists():
        raise HTTPException(status_code=404, detail=f"No historical market history found for {commodity} @ {mandi_id}.")

    history_files = sorted(history_dir.glob("*.json"))
    if not history_files:
        raise HTTPException(status_code=404, detail=f"No history files available for {commodity} @ {mandi_id}.")

    if limit < 1:
        limit = 1

    history_files = history_files[-limit:]
    history = []
    for hist_file in history_files:
        with open(hist_file, "r") as f:
            data = json.load(f)
        history.append(data)

    return {
        "commodity": commodity,
        "mandi_id": mandi_id,
        "history": history,
    }

@router.get('/market-data/processed')
async def get_processed_market_data_markets():
    """
    Enumerates processed market datasets that can be rendered as real historical time-series.
    """
    return {"markets": _list_processed_market_options()}

@router.get('/market-data/{commodity}/{mandi_id}')
async def get_market_data(commodity: str, mandi_id: str, limit: int = 365):
    """
    Returns processed market time-series data when available for a commodity/mandi.
    """
    data_file = _resolve_processed_data_file(commodity, mandi_id)
    if not data_file:
        raise HTTPException(
            status_code=404,
            detail=f'No processed market dataset found for {commodity} @ {mandi_id}.',
        )

    try:
        table = pq.read_table(str(data_file), columns=['date', 'modal_price', 'arrivals_tonnes'])
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to load market dataset for {commodity} @ {mandi_id}: {exc}',
        )

    dates = table.column('date').to_pylist()
    prices = table.column('modal_price').to_pylist()
    arrivals = table.column('arrivals_tonnes').to_pylist()
    history = []
    for idx, date_value in enumerate(dates):
        price_value = prices[idx] if idx < len(prices) else None
        arrival_value = arrivals[idx] if idx < len(arrivals) else None
        history.append({
            'timestamp': _serialize_timestamp(date_value),
            'modal_price': float(price_value if price_value is not None else 0),
            'arrivals_tonnes': float(arrival_value if arrival_value is not None else 0),
        })

    # Make sure history is chronological and apply limit to the most recent rows
    history = sorted(history, key=lambda item: item['timestamp'])
    if limit > 0 and len(history) > limit:
        history = history[-limit:]

    return {
        'commodity': commodity,
        'mandi_id': mandi_id,
        'source': 'processed',
        'history': history,
    }

@router.get("/directives")
async def get_all_directives():
    """
    Institutional summary of all evolving directives.
    """
    available = memory_store.list_available_intelligence()
    active_directives = []
    
    for commodity, mandis in available.items():
        for mandi in mandis:
            state = memory_store.get_latest_state(commodity, mandi)
            if state:
                active_directives.append({
                    "commodity": commodity,
                    "mandi_id": mandi,
                    "regime": state.regime,
                    "directive": state.directives.primary_directive,
                    "urgency": state.directives.urgency,
                    "confidence": round(state.confidence.score, 3),
                    "integrity": state.freshness.integrity_score,
                    "last_updated": state.freshness.last_computed
                })
                
    return {
        "count": len(active_directives),
        "directives": sorted(active_directives, key=lambda x: x["integrity"], reverse=True)
    }

@router.get("/available")
async def list_intelligence():
    return memory_store.list_available_intelligence()
