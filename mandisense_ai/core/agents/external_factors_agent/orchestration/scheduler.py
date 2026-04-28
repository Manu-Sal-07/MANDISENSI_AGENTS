import time
import threading
from orchestration.pipeline_runner import run_pipeline
from orchestration.config_manager import config
from orchestration.error_handler import log_info

def run_batch_mode():
    while True:
        log_info("Scheduler", "Executing Batch mode")
        run_pipeline(mode="full")
        time.sleep(config.scheduler_frequency["batch"])
        
def run_fast_mode():
    while True:
        log_info("Scheduler", "Executing Fast mode")
        run_pipeline(mode="fast")
        time.sleep(config.scheduler_frequency["fast"])

def schedule_jobs():
    t1 = threading.Thread(target=run_batch_mode, daemon=True)
    t2 = threading.Thread(target=run_fast_mode, daemon=True)
    
    t1.start()
    t2.start()
