import logging
import sys
import json
from datetime import datetime
from pathlib import Path

# Why: A structured JSON logger is essential for production observability.
# It allows us to easily filter logs by trace_id, level, or component in tools like ELK/Datadog.

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineNo": record.lineno,
        }
        
        # Inject correlation_id or trace_id if present
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
            
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

def get_logger(name: str) -> logging.Logger:
    """
    Retrieves a configured structured JSON logger instance.
    Why: Provides a consistent logging interface across all modules without having to pass the logger object around.
    """
    from config.settings import settings
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if get_logger is called multiple times
    if not logger.handlers:
        logger.setLevel(settings.logging.level)
        logger.propagate = False
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        logger.addHandler(console_handler)
        
        # File Handler
        try:
            log_path = Path(settings.logging.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback if there are issues creating the log file
            print(f"Warning: Could not create file handler for logger: {e}", file=sys.stderr)
            
    return logger
