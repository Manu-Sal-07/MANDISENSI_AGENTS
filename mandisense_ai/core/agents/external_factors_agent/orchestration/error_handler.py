import logging
import os

os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("orchestration")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("logs/system.log")
# Format securely strictly enforced according to Step 9
fh.setFormatter(logging.Formatter('%(asctime)s | %(name)s | %(message)s'))
logger.addHandler(fh)

def log_error(module, message, exc=None):
    if exc:
        msg = f"{message} - error: {str(exc)}"
        logger.error(msg)
    else:
        logger.error(message)

def log_info(module, message):
    # Pass module directly mapped to logger context via formatting natively
    l = logging.getLogger(module)
    l.setLevel(logging.INFO)
    has_handler = any(isinstance(h, logging.FileHandler) for h in l.handlers)
    if not has_handler:
        l.addHandler(fh)
    l.info(message)

def execute_with_fallback(func, args, kwargs, module_name, fallback_value=None):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_error(module_name, f"input: execution | output: fallback | status: FAILED", e)
        return fallback_value
