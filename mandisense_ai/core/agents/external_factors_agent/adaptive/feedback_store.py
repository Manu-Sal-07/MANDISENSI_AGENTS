import os
import csv

FEEDBACK_FILE = "data/predictions/feedback.csv"

def store_feedback(aligned_records):
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
    file_exists = os.path.isfile(FEEDBACK_FILE)
    
    with open(FEEDBACK_FILE, "a", newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "commodity", "rule_score", "ml_score", "causal_score", "final_score", "actual_change", "error"])
            
        for r in aligned_records:
            final = float(r.get("final_score", 0.0))
            actual = float(r.get("actual_change", 0.0))
            error = final - actual
            
            writer.writerow([
                r.get("date"),
                r.get("commodity"),
                r.get("rule_score", 0.0),
                r.get("ml_score", 0.0),
                r.get("causal_score", 0.0),
                final,
                actual,
                error
            ])
            
def get_all_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        return []
    import pandas as pd
    return pd.read_csv(FEEDBACK_FILE).to_dict('records')
