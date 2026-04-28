import time
import uuid

class JobManager:
    def __init__(self):
        self.active_jobs = {}
        
    def start_job(self, commodity):
        if commodity in self.active_jobs and self.active_jobs[commodity]["status"] == "running":
            return None # Prevent duplicate
            
        job_id = str(uuid.uuid4())
        self.active_jobs[commodity] = {
            "job_id": job_id,
            "status": "running",
            "timestamp": time.time(),
            "duration": 0
        }
        return job_id
        
    def end_job(self, commodity, job_id, success=True):
        if commodity in self.active_jobs and self.active_jobs[commodity]["job_id"] == job_id:
            job = self.active_jobs[commodity]
            job["status"] = "success" if success else "failed"
            job["duration"] = time.time() - job["timestamp"]

job_manager = JobManager()
