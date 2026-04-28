import re

def normalize_text(text):
    if not isinstance(text, str):
        return ""
    # 1. lowercase
    text = text.lower()
    # 2. remove punctuation: . , ! ? : ; ' " ( )
    text = re.sub(r'[\.\,\!\?\:\;\'\"\(\)]', '', text)
    # 3. replace multiple spaces -> single
    text = re.sub(r'\s+', ' ', text)
    # 4. strip
    return text.strip()
