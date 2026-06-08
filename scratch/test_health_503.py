import asyncio
import time
from fastapi import Response
from api.main import app, db_breaker, health_check

async def test_health_503():
    print("[TEST] Overriding database circuit breaker to OPEN state...")
    db_breaker.failures = 3
    db_breaker.state = "OPEN"
    db_breaker.last_failure_time = time.time()
    
    # Create a mock FastAPI response object
    response = Response()
    
    # Call health check
    result = await health_check(response=response)
    
    print(f"[TEST] Health status returned: {result['status']}")
    print(f"[TEST] HTTP Response Status Code: {response.status_code}")
    
    assert response.status_code == 503, "Status code should be 503 when breaker is OPEN"
    print("[TEST] Success! Health check returns 503 when subsystem is unhealthy.")

if __name__ == "__main__":
    asyncio.run(test_health_503())
