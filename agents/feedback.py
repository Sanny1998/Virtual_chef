from memory import store_feedback

def collect_feedback(user_id: str, score: int, comment: str = ""):
    try:
        score_int = int(score)
    except Exception:
        return {"error":"score must be integer 1-5"}
    if score_int < 1 or score_int > 5:
        return {"error":"score must be 1-5"}
    store_feedback(user_id, score_int, comment)
    return {"agent":"feedback", "text":"Thanks for your feedback!"}
