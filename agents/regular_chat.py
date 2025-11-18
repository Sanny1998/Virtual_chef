from utils import guardrail, scrub_pii

def reply(user_text: str):
    ok, reason = guardrail(user_text)
    if not ok:
        return {"agent": "regular", "text": f"I can help only with cooking topics: {reason}"}
    text = scrub_pii(user_text)
    # light chit-chat style
    return {"agent": "regular", "text": f"Ah! About '{text}', here's a short chef tip — taste as you go and balance salt and acid."}
