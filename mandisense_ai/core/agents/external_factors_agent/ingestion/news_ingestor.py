from utils.text_utils import normalize_text
from utils.date_utils import parse_date

FALLBACK_DATA = [
 {"title":"India bans onion export","description":"Export restriction imposed","date":"2026-04-20"},
 {"title":"Import duty reduced on pulses","description":"Imports expected to rise","date":"2026-04-18"},
 {"title":"Heavy rainfall damages tomato crops","description":"Flood conditions","date":"2026-04-21"},
 {"title":"Drought in Karnataka affects rice","description":"Low rainfall impact","date":"2026-04-17"},
 {"title":"MSP increased for wheat","description":"Government policy","date":"2026-04-19"},
 {"title":"Fuel prices rise","description":"Transport costs increase","date":"2026-04-22"},
 {"title":"Export demand rises for rice","description":"Global demand surge","date":"2026-04-16"},
 {"title":"Stock limit imposed on onions","description":"Anti-hoarding step","date":"2026-04-21"}
]

def fetch_news():
    # Logic:
    # 1. Try NewsAPI
    # 2. If fails -> try GNews
    # 3. If fails -> use fallback dataset
    # MOCK implementation using fallback as requested for deterministic pipeline
    
    processed_data = []
    for item in FALLBACK_DATA:
        processed_data.append({
            "title": normalize_text(item["title"]),
            "description": normalize_text(item["description"]),
            "date": parse_date(item["date"])
        })
    return processed_data
