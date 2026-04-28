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
from ensemble.meta_ensemble import run_meta_ensemble
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    # Default values
    commodity = "tomato"
    mandi = "kolar"
    
    # Override with command-line arguments if provided
    if len(sys.argv) > 1:
        commodity = sys.argv[1]
    if len(sys.argv) > 2:
        mandi = sys.argv[2]
    
    print(f"\n{'='*60}")
    print(f"MandiSense AI - Agent Execution + Meta-Ensemble Fusion")
    print(f"{'='*60}")
    print(f"Commodity: {commodity}")
    print(f"Mandi: {mandi}")
    print(f"{'='*60}\n")
    
    try:
        # Run Seasonality Agent
        print("📊 Running Seasonality Agent...")
        seasonality_output = run_seasonality_agent(commodity, mandi)
        seasonality_json = seasonality_output.dict()
        
        # Run Arrival Volume Agent
        print("📦 Running Arrival Volume Agent...")
        arrival_output = run_arrival_volume_agent(commodity, mandi)
        arrival_json = arrival_output.dict()
        
        # Display individual results
        print(f"\n{'='*60}")
        print("SEASONALITY AGENT OUTPUT")
        print(f"{'='*60}\n")
        print(json.dumps(seasonality_json, indent=2, default=str))
        
        print(f"\n{'='*60}")
        print("ARRIVAL VOLUME AGENT OUTPUT")
        print(f"{'='*60}\n")
        print(json.dumps(arrival_json, indent=2, default=str))
        
        # ── Meta-Ensemble Fusion ──────────────────────────────────────
        print(f"\n{'='*60}")
        print("🔀 Running Meta-Ensemble Fusion...")
        print(f"{'='*60}\n")
        
        # External Factors agent is not yet fully integrated;
        # pass neutral defaults (zero impact, zero confidence).
        # When the External agent is production-ready, wire its
        # output here.
        meta_result = run_meta_ensemble(
            seasonality_output=seasonality_output,
            arrival_output=arrival_output,
            external_impact=0.0,
            external_confidence=0.0,
        )
        
        print(f"\n{'='*60}")
        print("META-ENSEMBLE FUSED OUTPUT")
        print(f"{'='*60}\n")
        print(json.dumps(meta_result.to_dict(), indent=2, default=str))
        
        # Show debug internals for transparency
        print(f"\n{'='*60}")
        print("META-ENSEMBLE DEBUG (internals)")
        print(f"{'='*60}\n")
        print(json.dumps(meta_result.debug, indent=2, default=str))
        
        print(f"\n{'='*60}")
        print("✅ Execution Complete")
        print(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()

