import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from mandisense_ai.core.agents.training_pipeline_v2 import run_refinement_training

def main():
    """
    Offline Training Orchestrator.
    This script is the entry point for Section 2: Offline Training Infrastructure.
    It triggers commodity-specific training pipelines asynchronously from the terminal.
    """
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("MANDISENSE OFFLINE TRAINING INFRASTRUCTURE")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Phase 1 - Part 1: Initializing Pipelines...")
    
    try:
        run_refinement_training()
        print("\nSUCCESS: All models trained and persisted to /models/.")
        print("Model Lineage and Versioning (v2) recorded.")
    except Exception as e:
        print(f"\nFATAL ERROR during offline training: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
