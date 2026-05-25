import uvicorn
# from api.main import app
from orchestration.scheduler import schedule_jobs
from orchestration.error_handler import log_info

def start_system():
    log_info("System", "Booting Phase 5 Orchestration Layer...")
    
    # 1. Trigger isolated background orchestrators enforcing Tiering
    schedule_jobs()
    
    # 2. Bind FastAPI logic block on foreground thread
    log_info("System", "Serving API layer safely on port 8000 (Disabled in Agent Mode)...")
    # uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start_system()
