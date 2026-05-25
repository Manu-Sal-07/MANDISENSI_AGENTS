#!/usr/bin/env python
"""
MandiSense AI - Agent Runner (with Meta-Ensemble Fusion)
Simple entry point to run Seasonality, Arrival Volume agents and fuse via Meta-Ensemble.
Usage: python run_agents.py [commodity] [mandi]
Example: python run_agents.py tomato kolar
         python run_agents.py onion lasalgaon
"""

import sys
import json
from core.agents.seasonality_agent import run_seasonality_agent
from core.agents.arrival_volume_agent import run_arrival_volume_agent
from core.agents.external_factors_agent import run_external_factors_agent
from ensemble.meta_ensemble import run_meta_ensemble
from utils.logger import get_logger
from utils.event_bus import event_bus

logger = get_logger(__name__)

def run_pipeline(commodity: str, mandi: str) -> dict:
    """
    Executes the full MandiSense AI pipeline for a given commodity and mandi.
    Returns a dictionary containing results from all agents and the meta-ensemble.
    """
    try:
        event_bus.sync_emit("query_received", data={"commodity": commodity, "mandi": mandi})
        
        # Run Seasonality Agent
        event_bus.sync_emit("seasonality_started")
        seasonality_output = run_seasonality_agent(commodity, mandi)
        seasonality_json = seasonality_output.dict()
        event_bus.sync_emit("seasonality_completed", data=seasonality_json)
        
        # Run Arrival Volume Agent
        event_bus.sync_emit("arrival_started")
        arrival_output = run_arrival_volume_agent(commodity, mandi)
        arrival_json = arrival_output.dict()
        event_bus.sync_emit("arrival_completed", data=arrival_json)

        # Run External Factors Agent
        event_bus.sync_emit("external_started")
        external_output = run_external_factors_agent(commodity, mandi)
        external_impact = external_output["impact_score"]
        external_confidence = external_output["confidence"]
        external_json = external_output
        event_bus.sync_emit("external_completed", data=external_json)

        # Meta-Ensemble Fusion
        event_bus.sync_emit("ensemble_started")
        meta_result = run_meta_ensemble(
            seasonality_output=seasonality_output,
            arrival_output=arrival_output,
            external_impact=external_impact,
            external_confidence=external_confidence,
        )
        
        # Optional: Emit specific ensemble details if needed
        event_bus.sync_emit("ensemble_weights_computed", data=meta_result.to_dict().get("weights"))
        
        event_bus.sync_emit("meta_ensemble_started")
        # (Fusion already happened above, but we can separate the steps for visual impact)
        event_bus.sync_emit("meta_ensemble_completed", data=meta_result.to_dict())

        final_result = {
            "status": "success",
            "commodity": commodity,
            "mandi": mandi,
            "results": {
                "seasonality": seasonality_json,
                "arrival_volume": arrival_json,
                "external_factors": external_json,
                "meta_ensemble": meta_result.to_dict(),
            },
            "debug": meta_result.debug
        }
        
        event_bus.sync_emit("final_output", data=final_result)
        return final_result

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        event_bus.sync_emit("error", data={"message": str(e)})
        return {
            "status": "error",
            "message": str(e)
        }

def main():
    # Default values
    commodity = "tomato"
    mandi = "kolar"
    
    # Override with command-line arguments if provided
    if len(sys.argv) > 1:
        commodity = sys.argv[1]
    if len(sys.argv) > 2:
        mandi = sys.argv[2]
    
    # Return the dictionary as requested
    return run_pipeline(commodity, mandi)

if __name__ == "__main__":
    # When run via CLI, we still want to see the output
    result = main()
    
    if result["status"] == "success":
        print(f"\n{'='*60}")
        print(f"MandiSense AI - Execution Results")
        print(f"{'='*60}")
        print(f"Commodity: {result['commodity']}")
        print(f"Mandi: {result['mandi']}")
        print(f"{'='*60}\n")
        
        print("FUSED PREDICTION:")
        print(json.dumps(result["results"]["meta_ensemble"], indent=2, default=str))
        
        print(f"\n{'='*60}")
        print("✅ Execution Complete")
        print(f"{'='*60}\n")
    else:
        print(f"\n❌ Error: {result['message']}\n")
        sys.exit(1)

