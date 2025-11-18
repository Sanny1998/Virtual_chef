import time
from memory import add_timer
from typing import Dict, Any

def start_step_by_step(user_id: str, recipe: Dict[str,Any]):
    """
    Prepare step state, register timers for steps that include timer_sec, and return
    the first step alongside remaining steps. This returns a dict:
    {'agent':'step', 'current_step': {...}, 'remaining': [...]}
    """
    steps = recipe.get("steps", [])
    if not steps:
        return {"agent":"step", "current_step": {}, "remaining": []}
    now = int(time.time())
    # register timers for any steps that include timer_sec
    for s in steps:
        if "timer_sec" in s:
            add_timer(user_id, s.get("timer_label", "timer"), now + int(s["timer_sec"]))
    current = steps[0]
    remaining = steps[1:]
    return {"agent":"step", "current_step": current, "remaining": remaining}
