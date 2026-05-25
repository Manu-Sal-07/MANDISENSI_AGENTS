import requests
import time

def test_circuit_breaker():
    print("\n--- [PHASE 5B: CIRCUIT BREAKER VALIDATION] ---")
    url = "http://localhost:8000/v1/health"
    
    # We expect failures initially if DB is down
    for i in range(5):
        try:
            resp = requests.get(url, timeout=5)
            data = resp.json()
            db_status = data["services"]["db"]["status"]
            db_reachable = data["services"]["db"]["reachable"]
            print(f"Ping {i+1} | DB Status: {db_status} | Reachable: {db_reachable}")
            
            if db_status == "OPEN":
                print("SUCCESS: Circuit Breaker OPENED as expected.")
                break
        except Exception as e:
            print(f"Ping {i+1} | Request failed: {e}")
        time.sleep(1)

if __name__ == "__main__":
    test_circuit_breaker()
