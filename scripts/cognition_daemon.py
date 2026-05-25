import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from mandisense_ai.cognition.engine import CognitionEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("CognitionDaemon")

async def main():
    logger.info("MANDISENSE COGNITION DAEMON: ACTIVATING")
    engine = CognitionEngine()
    
    cycle_interval = 60 # 1 minute cycles for demonstration/war-room
    
    try:
        while True:
            logger.info("Initiating global cognition refresh cycle...")
            await engine.run_full_refresh()
            logger.info(f"Cycle complete. Hibernating for {cycle_interval}s.")
            await asyncio.sleep(cycle_interval)
    except asyncio.CancelledError:
        logger.info("Cognition Daemon shutdown requested.")
    except Exception as e:
        logger.error(f"Cognition Daemon CRASHED: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
