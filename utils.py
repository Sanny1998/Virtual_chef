import re
from typing import Tuple

def scrub_pii(text: str) -> str:
    # redact emails and phone numbers
    text = re.sub(r"\S+@\S+\.\S+", "[redacted_email]", text)
    text = re.sub(r"\+?\d[\d\-\s]{7,}\d", "[redacted_phone]", text)
    return text

def guardrail(text: str) -> Tuple[bool, str]:
    # simple forbidden word list + non-cooking topics
    forbidden = ["bomb", "weapon", "kill", "poison", "manufacture", "bombs"]
    non_cooking = ["law", "divorce", "tax", "stocks", "politics", "programming", "hack"]
    low = text.lower()
    for f in forbidden:
        if f in low:
            return False, f"Forbidden term detected: {f}"
    for n in non_cooking:
        if n in low:
            return False, f"I can help with cooking only; your query mentions {n}."
    return True, ""
