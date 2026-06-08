try:
    from mandisense_ai.core.agents.external_factors_agent.config.settings import COMMODITIES
except ImportError:
    from mandisense_ai.config.settings import COMMODITIES

# Event keywords definition
KEYWORDS = {
    "EXPORT_BAN": ["ban", "export restriction"],
    "IMPORT_DUTY_REDUCTION": ["import duty reduced"],
    "CROP_DAMAGE": ["heavy rainfall", "flood"],
    "DROUGHT": ["drought", "low rainfall"],
    "MSP_INCREASE": ["msp increased"],
    "FUEL_HIKE": ["fuel prices rise"],
    "DEMAND_SURGE": ["demand rises", "demand surge"],
    "STOCK_LIMIT": ["stock limit", "anti-hoarding"]
}

def extract_events(news_list):
    events = []
    for news in news_list:
        text = f"{news.get('title', '')} {news.get('description', '')}".lower()
        
        # 1. COMMODITY DETECTION
        matched_commodity = None
        for c in COMMODITIES:
            if c in text:
                matched_commodity = c
                break
        
        if not matched_commodity:
            continue
            
        # 2. EVENT DETECTION
        matched_event = "OTHER_EVENT"
        confidence = 0.4
        
        for event_type, kw_list in KEYWORDS.items():
            matches = [kw for kw in kw_list if kw in text]
            counts = len(matches)
            
            # MATCH LOGIC
            if counts >= 2:
                current_conf = 0.85
            elif counts == 1:
                # 'exact phrase' match if keyword has whitespace or matches perfectly
                if " " in matches[0]:
                    current_conf = 0.9
                else:
                    current_conf = 0.7
            else:
                continue
                
            if current_conf > confidence:
                confidence = current_conf
                matched_event = event_type

        events.append({
            "commodity": matched_commodity,
            "event_type": matched_event,
            "confidence": confidence,
            "event_date": news.get("date")
        })
    return events
