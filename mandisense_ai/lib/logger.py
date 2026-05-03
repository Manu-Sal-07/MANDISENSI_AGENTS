import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from mandisense_ai.config.settings import settings
except Exception:
    settings = None


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineNo": record.lineno,
        }

        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            log_entry.update(extra)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logging_settings = getattr(settings, "logging", None)
    level_name = getattr(logging_settings, "level", "INFO")
    log_level = getattr(logging, level_name.upper(), logging.INFO)
    logger.setLevel(log_level)
    logger.propagate = False

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    try:
        log_path = Path(getattr(logging_settings, "file_path", "logs/mandisense.log"))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    except Exception:
        pass

    return logger


def log_event(
    commodity: str,
    source: str,
    latency_ms: float,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    logger = get_logger("mandi_data_service")
    payload: Dict[str, Any] = {
        "commodity": commodity,
        "source": source,
        "latency_ms": round(latency_ms, 2),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if error:
        payload["error"] = str(error)
    if metadata is not None:
        payload["metadata"] = metadata

    if source == "live":
        logger.info("mandi data retrieved", extra={"extra": payload})
    elif source == "cache":
        logger.info("mandi data served from cache", extra={"extra": payload})
    else:
        logger.warning("mandi data served from fallback", extra={"extra": payload})


def log_failure(
    component: str,
    error: str,
    commodity: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    logger = get_logger(component)
    payload: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error": str(error),
    }
    if commodity is not None:
        payload["commodity"] = commodity
    if metadata is not None:
        payload["metadata"] = metadata

    logger.warning("mandi service failure", extra={"extra": payload})
