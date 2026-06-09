import os
import json
import pickle
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

MODELS_ROOT = r"d:\BMS COLL\PROJECT\MS-AI\MS-AI\mandisense_ai\models"
AGENTS = ["seasonality", "arrival"]
COMMODITIES = ["tomato", "onion", "potato", "dry_chillis", "garlic"]

def validate_bundle(path, agent_type):
    try:
        with open(path, 'rb') as f:
            bundle = pickle.load(f)
            
        # Common checks
        if "version" not in bundle or bundle["version"] != "v1":
            return False, "Missing or invalid bundle version (expected v1)"
        
        if "models" not in bundle:
            return False, "Missing 'models' key in bundle"
        
        # Agent specific checks
        if agent_type == "seasonality":
            if "stl_components" not in bundle:
                return False, "Missing 'stl_components' for seasonality"
        else:
            if "weights" not in bundle:
                return False, "Missing 'weights' for arrival ensemble"
                
        return True, "Valid"
    except Exception as e:
        return False, f"Load Error: {str(e)}"

def validate_mandi_models():
    results = []
    
    for commodity in COMMODITIES:
        commodity_status = {
            "commodity": commodity,
            "status": "VALID",
            "issues": []
        }
        
        for agent in AGENTS:
            agent_dir = os.path.join(MODELS_ROOT, agent, commodity)
            bundle_path = os.path.join(agent_dir, "bundle.pkl")
            meta_path = os.path.join(agent_dir, "metadata.json" if agent == "seasonality" else "metrics.json")
            
            # 1. Check directory existence
            if not os.path.exists(agent_dir):
                commodity_status["status"] = "INVALID"
                commodity_status["issues"].append(f"Agent {agent}: Directory missing")
                continue
                
            # 2. Check Bundle
            if not os.path.exists(bundle_path):
                commodity_status["status"] = "INVALID"
                commodity_status["issues"].append(f"Agent {agent}: bundle.pkl missing")
            else:
                ok, msg = validate_bundle(bundle_path, agent)
                if not ok:
                    commodity_status["status"] = "INVALID"
                    commodity_status["issues"].append(f"Agent {agent}: {msg}")
            
            # 3. Check Metadata/Metrics
            if not os.path.exists(meta_path):
                commodity_status["status"] = "INVALID"
                commodity_status["issues"].append(f"Agent {agent}: JSON configuration missing")
                
        results.append(commodity_status)
        
    return results

if __name__ == "__main__":
    print("--- MANDISENSE MODEL VALIDATOR (v1) ---")
    validation_results = validate_mandi_models()
    print(json.dumps(validation_results, indent=2))
    
    overall_valid = all(r["status"] == "VALID" for r in validation_results)
    if overall_valid:
        print("\n✅ ALL MODELS COMPLIANT")
    else:
        print("\n❌ NON-COMPLIANT MODELS DETECTED")
