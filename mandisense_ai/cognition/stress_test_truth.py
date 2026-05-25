import asyncio
import logging
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.getcwd())

from mandisense_ai.cognition.engine import CognitionEngine
from mandisense_ai.cognition.ontology import CognitionStatus

async def stress_test_integrity():
    logging.basicConfig(level=logging.INFO)
    engine = CognitionEngine()
    
    print("\n--- [TRUTH STRESS TEST] ---")
    
    # 1. Simulate Telemetry Degradation
    print("\n[SCENARIO 1] Simulating Stale Telemetry (1 week old)...")
    stale_time = datetime.now() - timedelta(days=7)
    for src in engine.reality_sync.sources.values():
        src.last_sync = stale_time
    
    print("Triggering Cognition Pulse...")
    state = await engine.generate_cognition("tomato", "kolar_apmc")
    
    print(f"RESULT: Integrity Status = {state.integrity_status}")
    print(f"RESULT: Final Confidence = {state.confidence.score * 100:.1f}%")
    
    if state.integrity_status == CognitionStatus.TELEMETRY_DEGRADED:
        print("SUCCESS: Machine honestly reported Telemetry Degradation.")
    else:
        print(f"FAILURE: Machine reported {state.integrity_status}")

    # 2. Verify Orchestration Suppression
    print("\n[SCENARIO 2] Verifying Orchestration Safety Gate...")
    plan_id = state.metadata.get("active_execution_plan", {}).get("id", "NONE")
    plan_status = state.metadata.get("active_execution_plan", {}).get("overall_status", "NONE")
    
    print(f"PLAN ID: {plan_id}")
    print(f"PLAN STATUS: {plan_status}")
    
    if "SAFE" in plan_id or plan_status == "ABORTED":
        print("SUCCESS: Orchestration was safely suppressed.")
    else:
        print("FAILURE: System attempted orchestration during integrity failure.")

if __name__ == "__main__":
    asyncio.run(stress_test_integrity())
