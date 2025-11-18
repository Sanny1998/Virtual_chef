"""
Simple SQLite storage for profiles, recipes, feedback, timers.
"""

import sqlite3
from pathlib import Path
import json
import time
from typing import Dict, Any, List, Tuple

DB = Path(__file__).parent / "chef_langgraph.db"

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        profile JSON
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        title TEXT,
        payload JSON
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        score INTEGER,
        comment TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS timers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        label TEXT,
        wake_at INTEGER,
        fired INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()

def save_user_profile(user_id: str, profile: Dict[str, Any]):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("REPLACE INTO users(user_id, profile) VALUES (?,?)", (user_id, json.dumps(profile)))
    conn.commit()
    conn.close()

def load_user_profile(user_id: str):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT profile FROM users WHERE user_id=?", (user_id,))
    r = cur.fetchone()
    conn.close()
    return json.loads(r[0]) if r else None

def push_recipe(user_id: str, title: str, payload: Dict[str, Any]):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO recipes(user_id,title,payload) VALUES (?,?,?)", (user_id, title, json.dumps(payload)))
    conn.commit()
    conn.close()

def store_feedback(user_id: str, score: int, comment: str):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO feedback(user_id,score,comment) VALUES (?,?,?)", (user_id, score, comment))
    conn.commit()
    conn.close()

def add_timer(user_id: str, label: str, wake_at: int):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO timers(user_id,label,wake_at,fired) VALUES (?,?,?,0)", (user_id, label, wake_at))
    conn.commit()
    conn.close()

def fetch_due_timers(now_ts: int) -> List[Tuple[int, str]]:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id,label FROM timers WHERE fired=0 AND wake_at<=?", (now_ts,))
    rows = cur.fetchall()
    ids = [r[0] for r in rows]
    if ids:
        q = "UPDATE timers SET fired=1 WHERE id IN ({})".format(",".join("?"*len(ids)))
        cur.execute(q, ids)
    conn.commit()
    conn.close()
    # return list of (id,label)
    return [(r[0], r[1]) for r in rows]
