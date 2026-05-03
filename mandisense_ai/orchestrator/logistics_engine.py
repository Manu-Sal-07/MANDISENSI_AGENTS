import math
import json

# --- CONFIGURATION & CONSTANTS ---
BASE_TRANSPORT_COST = 500  # Rs loading/unloading
COST_PER_KM_PER_TONNE = 20 # Rs per km per tonne
MAX_DISTANCE_THRESHOLD = 300 # km

# --- STEP 1: DISTANCE + TRAVEL COST ---
def calculate_transport_cost(distance_km, quantity_tonnes):
    if quantity_tonnes is None or quantity_tonnes <= 0:
        quantity_tonnes = 1.0 # Default fallback
    
    # Quantity factor: slight discount for larger loads per tonne, but total cost scales up
    quantity_factor = math.pow(quantity_tonnes, 0.9) 
    transport_cost = BASE_TRANSPORT_COST + (distance_km * COST_PER_KM_PER_TONNE * quantity_factor)
    return transport_cost

# --- MAIN LOGISTICS ENGINE ---
def optimize_mandi_selection(input_data: dict) -> dict:
    commodity = input_data["commodity"]
    quantity = input_data.get("quantity") or 1.0
    
    decision = input_data["decision"]
    meta_pred = input_data["meta_prediction_7d"]
    confidence = input_data["confidence"]
    risk = input_data["risk"]
    
    mandis = input_data.get("mandis", [])
    
    evaluated_mandis = []
    
    for mandi in mandis:
        name = mandi["name"]
        dist = mandi["distance_km"]
        current_price = mandi["current_price"] # Price per tonne (e.g. 15000 Rs)
        arrival_level = mandi["arrival_level"]
        liquidity = mandi["liquidity"]
        
        # STEP 1: Transport Cost
        transport_cost_total = calculate_transport_cost(dist, quantity)
        transport_cost_per_tonne = transport_cost_total / quantity
        
        # STEP 2: Effective Sell Price (Future adjusted)
        adjusted_price = current_price * (1 + (meta_pred / 100.0))
        
        # STEP 3: Arrival Pressure Penalty
        price_penalty = 0.0
        if arrival_level == "HIGH":
            price_penalty = -0.03
        elif arrival_level == "MEDIUM":
            price_penalty = -0.01
            
        adjusted_price *= (1 + price_penalty)
        
        # STEP 4: Liquidity Adjustment
        if liquidity == "LOW":
            liquidity_penalty = -0.02
        elif liquidity == "MEDIUM":
            liquidity_penalty = -0.01
        else:
            liquidity_penalty = 0.0
            
        adjusted_price *= (1 + liquidity_penalty)
        
        # STEP 5: Net Realization
        net_price_per_tonne = adjusted_price - transport_cost_per_tonne
        
        # STEP 6: Risk-Aware Scoring
        if risk == "HIGH":
            conf_adj = 0.8
        elif risk == "MEDIUM":
            conf_adj = 0.9
        else:
            conf_adj = 1.0
            
        score = net_price_per_tonne * conf_adj
        
        # STEP 7: Filter Unrealistic Options
        if dist > MAX_DISTANCE_THRESHOLD:
            continue
            
        # Reject if transport cost eats up more than 30% of the price (unrealistic haul)
        if transport_cost_per_tonne > (current_price * 0.3):
            continue
            
        evaluated_mandis.append({
            "name": name,
            "distance_km": dist,
            "current_price": current_price,
            "adjusted_price": round(adjusted_price, 2),
            "transport_cost_total": round(transport_cost_total, 2),
            "transport_cost_per_tonne": round(transport_cost_per_tonne, 2),
            "net_price_per_tonne": round(net_price_per_tonne, 2),
            "score": score,
            "arrival_level": arrival_level,
            "liquidity": liquidity
        })
        
    # STEP 8: Select Best Mandi & Fallback (STEP 9)
    if not evaluated_mandis:
        return {
            "decision": "WAIT",
            "recommended_mandi": "None (Sell Locally)",
            "distance_km": 0.0,
            "transport_cost": 0.0,
            "adjusted_price": 0.0,
            "net_price": 0.0,
            "timing": "WAIT",
            "strategy": "Wait. No profitable market within range.",
            "confidence": confidence * 0.5,
            "risk": "HIGH",
            "reason": "Transport costs negate any market advantage."
        }
        
    best_mandi = max(evaluated_mandis, key=lambda x: x["score"])
    
    # STEP 10: Timing Strategy
    if meta_pred < -2.0:
        timing = "SELL IMMEDIATELY"
        trend_text = f"drop by {abs(meta_pred):.1f}%"
    elif meta_pred > 2.0:
        timing = "WAIT OR SELL LATER"
        trend_text = f"rise by {meta_pred:.1f}%"
    else:
        timing = "SELL FLEXIBLY"
        trend_text = f"remain stable"
        
    # STEP 11: Quantity Strategy
    if quantity > 5.0:
        strategy = "Sell in staggered batches to avoid affecting market price."
    else:
        strategy = "Sell immediately in one batch."
        
    # Construct Reason
    reason = (
        f"Prices are expected to {trend_text} in the coming week. "
        f"{best_mandi['name']} offers the best net return after accounting for transport cost. "
        f"Arrival pressure is {best_mandi['arrival_level'].lower()}, and liquidity is {best_mandi['liquidity'].lower()}."
    )
    
    # STEP 12: Final Output
    return {
        "decision": decision,
        "recommended_mandi": best_mandi["name"],
        "distance_km": best_mandi["distance_km"],
        "transport_cost": best_mandi["transport_cost_total"],
        "adjusted_price": best_mandi["adjusted_price"],
        "net_price": best_mandi["net_price_per_tonne"],
        "timing": timing,
        "strategy": strategy,
        "confidence": round(confidence, 2),
        "risk": risk,
        "reason": reason
    }

# --- STEP 13: NATURAL RESPONSE BUILDER ---
def build_natural_response(result: dict, commodity: str) -> str:
    mandi = result['recommended_mandi']
    decision = result['decision'].capitalize()
    
    # Extract signals for better explainability
    reason = result.get('reason', '')
    strategy = result.get('strategy', '')
    
    # Build a more grounded response
    res = f"### {decision} Strategy for {commodity.capitalize()} in {mandi} Mandi\n\n"
    
    res += f"**Market Context:** {reason}\n\n"
    
    # Add specific logic for the requested output format if available
    if "arrival" in reason.lower() or "weather" in reason.lower():
        res += f"**Signal Analysis:** In {mandi} mandi, {reason.lower().replace('expected to ', '')}\n\n"
    
    res += f"**Execution Plan:** {strategy}\n\n"
    
    res += f"| Metric | Recommendation |\n"
    res += f"| :--- | :--- |\n"
    res += f"| **Net Realizable Price** | Rs. {result['net_price']:,.2f} / tonne |\n"
    res += f"| **Transport Economics** | Rs. {result['transport_cost']:,.2f} ({result['distance_km']} km) |\n"
    res += f"| **Confidence Level** | {result['confidence']*100:.1f}% |\n"
    res += f"| **Risk Rating** | {result['risk']} |\n\n"
    
    res += f"**Timing:** {result['timing']}"
    
    return res

if __name__ == "__main__":
    # MOCK INPUT
    test_input = {
      "commodity": "tomatoes",
      "user_location": { "lat": 13.1, "lon": 78.1 },
      "quantity": 8.5, # tonnes

      "decision": "SELL",
      "meta_prediction_7d": -4.8,
      "confidence": 0.85,
      "risk": "MEDIUM",

      "mandis": [
        {
          "name": "Kolar",
          "distance_km": 45.0,
          "current_price": 12000.0,
          "arrival_level": "MEDIUM",
          "liquidity": "HIGH"
        },
        {
          "name": "Bangalore",
          "distance_km": 120.0,
          "current_price": 13500.0, # Higher raw price
          "arrival_level": "HIGH",  # But high pressure
          "liquidity": "HIGH"
        },
        {
          "name": "Chintamani",
          "distance_km": 25.0,
          "current_price": 11500.0,
          "arrival_level": "LOW",
          "liquidity": "LOW"        # Bad liquidity
        }
      ]
    }
    
    print("--- MANDISENSE LOGISTICS & EXECUTION ENGINE ---\n")
    
    result = optimize_mandi_selection(test_input)
    print("--- RAW JSON OUTPUT ---")
    print(json.dumps(result, indent=2))
    
    print("\n--- NATURAL LANGUAGE RESPONSE ---")
    print(build_natural_response(result, test_input["commodity"]))
