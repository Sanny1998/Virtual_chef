from typing import Dict, Any
from models import Preferences
from pydantic import ValidationError

def ask_preferences():
    return {
        "agent": "preference",
        "questions": [
            {"key": "number_of_people", "text": "How many people are you cooking for? (1-20)"},
            {"key": "spice_level", "text": "Spice level (0=mild to 10=very spicy)"},
            {"key": "region_preference", "text": "Which region? (north/south/east/west)"},
            {"key": "preference_type", "text": "Preference type (dietary/cuisine/cooking_time/none)"},
            {"key": "allergies", "text": "Any allergies/dislikes? (comma-separated, optional)"}
        ]
    }

def validate_preferences(raw: Dict[str, Any]):
    try:
        prefs = Preferences(**raw)
        return True, prefs
    except ValidationError as e:
        return False, e
