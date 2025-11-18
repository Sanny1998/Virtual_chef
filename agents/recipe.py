import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
client = OpenAI(api_key=API_KEY)

SYSTEM_PROMPT = """
You are Chef Raghav — a seasoned Indian chef with 30+ years across India and Italy.
When user asks, produce JSON only with keys:
title, cultural_note, ingredients (list), steps (list of {text, optional timer_sec, optional timer_label}), tips (list).
- At least one step must include timer_sec (an integer, seconds).
- Respect allergies/dislikes.
- Adapt spice_level and number_of_people in ingredient quantities.
- Keep steps short and actionable.
"""

def _build_user_prompt(prefs):
    # prefs is Pydantic Preferences or dict
    if hasattr(prefs, "dict"):
        p = prefs.dict()
    else:
        p = prefs
    return f"""Generate a recipe personalized to:
number_of_people={p.get('number_of_people')}, spice_level={p.get('spice_level')}, region={p.get('region_preference')},
preference_type={p.get('preference_type')}, allergies={p.get('allergies')}, dislikes={p.get('dislikes')}.
Return ONLY valid JSON matching the schema. Keep text natural and chef-like.
"""

def generate(prefs):
    """
    Calls OpenAI Chat Completions (chat.completions.create) via the OpenAI client.
    Expects returned message content to be raw JSON.
    """
    prompt = _build_user_prompt(prefs)
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.8,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )
    content = resp.choices[0].message.content
    # Clean up if assistant wrapped in markdown
    content = content.strip()
    # attempt to find first JSON object in content
    try:
        # if the assistant returns markdown/code fences, strip them
        if content.startswith("```"):
            # remove code fence
            parts = content.split("```")
            # choose the middle portion if present
            for part in parts:
                part = part.strip()
                if part.startswith("{"):
                    content = part
                    break
        recipe = json.loads(content)
        # minimal schema checks
        recipe.setdefault("tips", [])
        recipe.setdefault("ingredients", [])
        recipe.setdefault("steps", [])
        return recipe
    except Exception as e:
        # fallback: create a simple templated recipe (should rarely happen)
        fallback = {
            "title": "Simple Tomato Curry",
            "cultural_note": "A quick fallback recipe blended from Indian and Italian ideas.",
            "ingredients": ["Tomatoes 500g", "Onion 1", "Salt", "Oil 2 tbsp"],
            "steps": [
                {"text": "Chop vegetables."},
                {"text": "Sauté onion.", "timer_sec": 60, "timer_label": "saute onion"},
                {"text": "Add tomatoes and simmer.", "timer_sec": 300, "timer_label": "simmer tomatoes"}
            ],
            "tips": ["Use ripe tomatoes", "Add a pinch of sugar to balance acidity"]
        }
        return fallback
