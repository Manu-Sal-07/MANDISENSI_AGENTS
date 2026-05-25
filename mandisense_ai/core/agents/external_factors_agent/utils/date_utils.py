try:
    from mandisense_ai.core.agents.external_factors_agent.config.settings import CURRENT_DATE
except ImportError:
    from config.settings import CURRENT_DATE

def parse_date(date_string):
    if not isinstance(date_string, str):
        return CURRENT_DATE
    # Accept YYYY-MM-DD or YYYY/MM/DD
    d_str = date_string.replace("/", "-")
    parts = d_str.split("-")
    if len(parts) == 3 and len(parts[0]) == 4:
        return d_str
    # If invalid -> return CURRENT_DATE
    return CURRENT_DATE
