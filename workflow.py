"""
workflow.py

Defines a LangGraph-style workflow using langgraph_runtime.Graph and Node objects.
This file wires the Supervisor and the agent nodes.
"""

from langgraph_runtime import Graph, Node
from typing import Dict, Any, Tuple, Optional
from agents import (
    greeting, preference, recipe as recipe_agent,
    regular_chat, step_by_step, feedback as feedback_agent
)
from utils import scrub_pii, guardrail
from models import Preferences
from memory import push_recipe


def supervisor_action(ctx: Dict[str, Any], message: str) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """
    Supervisor returns a node key to execute (the next node).
    We implement a ReAct-style decision heuristic here; replace with LLM prompt if desired.
    """
    m = message.strip().lower()
    ok, reason = guardrail(message)
    if not ok:
        return reason, "regular_chat", {}

    # greeting
    if any(w in m for w in ["hi", "hello", "namaste", "hey"]):
        return "routing to greeting", "greeting", {}

    # preferences not collected or mid-flow
    if "preferences" not in ctx or ctx.get("_expecting_pref_answer", False):
        return "need preferences", "preference", {}

    # explicit recipe intent
    if any(w in m for w in ["recipe", "cook", "make", "i want to cook", "i want to make"]):
        return "user wants a recipe", "recipe", {}

    # yes/no after recipe offer to start step-by-step
    if m in ("yes", "y", "sure", "please") and ctx.get("last_recipe"):
        return "start step", "step_by_step", {}

    # during step-by-step navigation
    if ctx.get("_in_steps"):
        if m in ("next", "n", "repeat", "r", "slow", "s"):
            return "step nav", "step_by_step", {}
        if ctx.get("expecting_feedback"):
            return "collect feedback", "feedback", {}

    # fallback
    return "fallback to regular chat", "regular_chat", {}


def build_graph() -> Graph:
    g = Graph()

    # Supervisor Node
    g.add_node(Node("supervisor", supervisor_action))
    g.set_supervisor("supervisor")

    # Greeting Node
    def greeting_action(ctx: Dict[str, Any], message: str):
        name = ctx.get("user_name", "friend")
        text = greeting.greet(name)
        return text, None, {}

    g.add_node(Node("greeting", greeting_action))

    # Preference Node
    def preference_action(ctx: Dict[str, Any], message: str):
        # uses preference.ask_preferences() which returns interactive Qs
        # Flow: store answers until done, validate with Pydantic
        if "preferences" in ctx:
            return "Preferences already set.", None, {}
        questions = preference.ask_preferences()["questions"]
        stage = ctx.get("_pref_stage", 0)
        answers = ctx.get("_pref_answers", [])

        # If the supervisor routed here after an answer, collect the message
        if ctx.get("_expecting_pref_answer") and message.strip():
            answers.append(message.strip())
            stage += 1
            ctx["_pref_answers"] = answers
            ctx["_pref_stage"] = stage

        if stage < len(questions):
            q_text = questions[stage]["text"]
            ctx["_expecting_pref_answer"] = True
            return q_text, None, {}
        # validate
        raw = {}
        keys = [q['key'] for q in questions]
        for k, v in zip(keys, answers):
            raw[k] = v
        valid, prefs_or_err = preference.validate_preferences(raw)
        if not valid:
            # reset on error
            ctx.pop("_pref_stage", None)
            ctx.pop("_pref_answers", None)
            ctx.pop("_expecting_pref_answer", None)
            return f"Preference error: {prefs_or_err}", None, {}
        ctx["preferences"] = prefs_or_err.dict()
        ctx.pop("_pref_stage", None)
        ctx.pop("_pref_answers", None)
        ctx.pop("_expecting_pref_answer", None)
        return "Preferences saved. What would you like to cook?", None, {}

    g.add_node(Node("preference", preference_action))

    # Recipe Node
    def recipe_action(ctx: Dict[str, Any], message: str):
        prefs = ctx.get("preferences")
        if not prefs:
            return "I need your preferences first.", "preference", {}
        # convert to Pydantic object for LLM call
        try:
            prefs_obj = Preferences(**prefs)
        except Exception as e:
            return f"Preferences appear invalid: {e}", "preference", {}
        recipe_obj = recipe_agent.generate(prefs_obj)
        ctx["last_recipe"] = recipe_obj
        # persist recipe
        uid = ctx.get("user_id", "anonymous")
        try:
            push_recipe(uid, recipe_obj.get("title", "untitled"), recipe_obj)
        except Exception:
            pass
        # format output
        parts = []
        parts.append(f"{recipe_obj.get('title')}\n")
        parts.append(f"Cultural note: {recipe_obj.get('cultural_note')}\n")
        parts.append("Ingredients:")
        for i in recipe_obj.get("ingredients", []):
            parts.append(f"- {i}")
        parts.append("\nMethod:")
        for idx, s in enumerate(recipe_obj.get("steps", []), start=1):
            parts.append(f"{idx}. {s.get('text')}")
        parts.append("\nTips:")
        for t in recipe_obj.get("tips", []):
            parts.append(f"- {t}")
        parts.append("\nWould you like step-by-step guidance? (yes/no)")
        return "\n".join(parts), None, {"last_recipe": recipe_obj}

    g.add_node(Node("recipe", recipe_action))

    # Step-by-step Node
    def step_action(ctx: Dict[str, Any], message: str):
        recipe_obj = ctx.get("last_recipe")
        if not recipe_obj:
            return "No recipe to guide. Ask for a recipe first.", None, {}
        uid = ctx.get("user_id", "anonymous")
        res = step_by_step.start_step_by_step(uid, recipe_obj)
        # expected res: {'agent':'step','current_step':..., 'remaining':[...]}
        ctx["step_state"] = res
        ctx["_in_steps"] = True
        # return first step text
        return f"Starting step-by-step. Step: {res['current_step'].get('text')}", None, {}

    g.add_node(Node("step_by_step", step_action))

    # Feedback Node
    def feedback_action(ctx: Dict[str, Any], message: str):
        uid = ctx.get("user_id", "anonymous")
        try:
            parts = message.strip().split(None, 1)
            score = int(parts[0])
            comment = parts[1] if len(parts) > 1 else ""
            out = feedback_agent.collect_feedback(uid, score, comment)
            # clear context fields to end session
            ctx_keys = ["last_recipe", "step_state", "_in_steps", "expecting_feedback"]
            for k in ctx_keys:
                ctx.pop(k, None)
            return out.get("text", "Thanks for the feedback!"), None, {}
        except Exception:
            return "Please provide feedback starting with a number 1-5.", None, {}

    g.add_node(Node("feedback", feedback_action))

    # Regular Chat Node
    def regular_action(ctx: Dict[str, Any], message: str):
        return regular_chat.reply(message).get("text", "I can help with cooking topics."), None, {}

    g.add_node(Node("regular_chat", regular_action))

    return g
