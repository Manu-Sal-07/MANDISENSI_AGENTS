import sys
try:
    from mandisense_ai.config.settings import settings
except ImportError:
    from mandisense_ai.config.settings import settings
from mandisense_ai.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Why: The main entry point handles bootstrapping the application, 
# loading configured dependencies, and orchestrating the high-level workflow.

def main():
    logger.info("Starting MandiSense AI Initialization...")
    
    try:
        # Initializing core agents and database connections placeholder
        logger.info({
            "event": "config_loaded",
            "app_name": settings.app.name,
            "environment": settings.app.environment,
            "commodities_tracked": settings.data.commodities,
            "ensemble_activation_threshold": settings.ensemble.activation_threshold
        })
        
        print(f"=== {settings.app.name} initialized successfully ===")
        print(f"Environment: {settings.app.environment}")
        print(f"Tracking {len(settings.data.commodities)} commodities across {len(settings.data.mandis)} mandis.")
        print(f"Logs are being written to: {settings.logging.file_path}")
        print("MandiSense AI Phase 0 initialized successfully")
        
    except Exception as e:
        logger.error("System Initialization failed", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
