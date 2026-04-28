import re
from pathlib import Path
from typing import Union

# Why: Common helper functions prevent code duplication across data ingestion and processing layers.

def standardize_mandi_name(name: str) -> str:
    """
    Standardizes mandi names to lowercase and removes special characters.
    Handling messy Agmarknet data.
    """
    if not name:
        return ""
    name = name.lower().strip()
    return re.sub(r"[^a-z0-9]", "", name)

def normalize_commodity_name(name: str) -> str:
    """
    Normalizes commodity names (e.g., 'Onion (Big)' -> 'onion').
    """
    if not name:
        return ""
    name = name.lower().strip()
    # Remove contents in brackets which specify size/type variations in Agmarknet optionally
    name = re.sub(r"\(.*?\)", "", name).strip()
    return name

def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensures a directory exists, creating it if necessary.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
