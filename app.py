import streamlit as st
import uuid
import time
from dotenv import load_dotenv

load_dotenv()

from memory import init_db, fetch_due_timers
from workflow import build_graph

# init DB
init_db()

st.set_page_config(page_title="Chef Raghav — LangGraph Chef", layout="centered")

if "uid" not in st.session_state:
    st.session_state.uid = str(uuid.uuid4())

if "state" not in st.session_state:
    st.session_state.state = {"user_id": st.session_state.uid}

if "history" not in st.session_state:
    st.session_state.history = []

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

st.title("🍲 Chef Raghav — LangGraph Multi-Agent Chef")

# sidebar for profile
with st.sidebar:
    st.header("Profile")
    name = st.text_input("Name", value=st.session_state.state.get("user_name",""))
    if st.button("Save name"):
        st.session_state.state["user_name"] = name
        from memory import save_user_profile
        save_user_profile(st.session_state.uid, {"name": name})
        st.success("Saved")

# Chat history display
for who, text in st.session_state.history:
    if who == "you":
        st.markdown(f"**You:** {text}")
    else:
        st.markdown(f"**Chef Raghav:** {text}")

col1, col2 = st.columns([8,1])
user_input = col1.text_input("You:", key="input_text")
if col2.button("Send"):
    user_msg = user_input.strip()
    if user_msg:
        # run graph once
        out_text, new_ctx = st.session_state.graph.run_once(st.session_state.state, user_msg)
        # ensure user_id remains
        new_ctx["user_id"] = st.session_state.uid
        st.session_state.state = new_ctx
        st.session_state.history.append(("you", user_msg))
        st.session_state.history.append(("chef", out_text))
        # clear
        st.session_state.input_text = ""
        st.experimental_rerun()

# Poll timers every few seconds (frontend poll)
if "last_timer_poll" not in st.session_state:
    st.session_state["last_timer_poll"] = 0

if time.time() - st.session_state["last_timer_poll"] > 3:
    due = fetch_due_timers(int(time.time()))
    if due:
        for tid, label in due:
            st.session_state.history.append(("chef", f"⏰ Timer finished: {label}. Continue with next step!"))
        st.experimental_rerun()
    st.session_state["last_timer_poll"] = time.time()
