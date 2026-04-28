import os
import csv
import random
from config.settings import COMMODITIES

def build_dataset():
    filename = "data/training/dataset.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "date", "commodity", "event_count_3d", "event_count_7d",
            "avg_confidence", "max_impact", "sum_impact", 
            "recent_event_flag", "days_since_last_event", "price_change"
        ])
        
        # Simulate historical simulation + price data
        random.seed(42)  # For reproducibility
        for i in range(100):
            for c in COMMODITIES:
                ev_count_7d = random.randint(0, 5)
                ev_count_3d = random.randint(0, min(3, ev_count_7d))
                avg_conf = random.uniform(0.4, 0.9) if ev_count_7d > 0 else 0.0
                max_imp = random.uniform(0.1, 0.8) if ev_count_7d > 0 else 0.0
                sum_imp = max_imp * random.uniform(1.0, 1.5) if ev_count_7d > 0 else 0.0
                recent = 1 if ev_count_3d > 0 else 0
                days_since = random.randint(0, 30) if ev_count_7d > 0 else 30
                
                # Target formulation
                price_change = sum_imp * random.uniform(0.01, 0.1) - 0.01
                
                writer.writerow([
                    f"2026-04-{random.randint(1, 28):02d}",
                    c,
                    ev_count_3d,
                    ev_count_7d,
                    avg_conf,
                    max_imp,
                    sum_imp,
                    recent,
                    days_since,
                    price_change
                ])
                
        # Inject bad rows to test skipping logic
        writer.writerow([
            "2026-04-20", "onion", 1, 1, 0.9, 0.1, 0.1, 1, 1, ""
        ])
