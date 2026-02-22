"""
SymSolver — Local JSON storage for users, history, and settings.

Data is persisted in ``<project>/data/symsolver.json``.
"""

import hashlib
import json
import os
import time
from datetime import datetime
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
_DATA_FILE = os.path.join(_DATA_DIR, "symsolver.json")

# ── Default settings (used for guests and new accounts) ─────────────────
DEFAULT_SETTINGS = {
    "theme": "dark",
    "animation_speed": "normal",   # "slow", "normal", "fast", "instant"
    "auto_scroll": True,
    "show_verification": False,    # auto-expand verification section
    "show_graph": True,            # auto-expand graph section
}


def _ensure_dir() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)


def _load_db() -> dict:
    _ensure_dir()
    if os.path.exists(_DATA_FILE):
        try:
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"users": {}, "guest_settings": dict(DEFAULT_SETTINGS)}


def _save_db(db: dict) -> None:
    _ensure_dir()
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ── User management ─────────────────────────────────────────────────────

def register_user(username: str, password: str) -> tuple[bool, str]:
    """Create a new account. Returns (success, message)."""
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    db = _load_db()
    key = username.lower()
    if key in db["users"]:
        return False, "Username already taken."
    db["users"][key] = {
        "display_name": username,
        "password_hash": _hash_pw(password),
        "settings": dict(DEFAULT_SETTINGS),
        "history": [],
    }
    _save_db(db)
    return True, "Account created successfully!"


def login_user(username: str, password: str) -> tuple[bool, str]:
    """Validate credentials. Returns (success, message)."""
    db = _load_db()
    key = username.strip().lower()
    user = db["users"].get(key)
    if not user:
        return False, "User not found."
    if user["password_hash"] != _hash_pw(password):
        return False, "Incorrect password."
    return True, user["display_name"]


# ── Settings ─────────────────────────────────────────────────────────────

def get_settings(username: Optional[str] = None) -> dict:
    """Return settings dict. If *username* is None, return guest settings."""
    db = _load_db()
    if username:
        key = username.strip().lower()
        user = db["users"].get(key)
        if user:
            # Merge with defaults so new keys are always present
            merged = dict(DEFAULT_SETTINGS)
            merged.update(user.get("settings", {}))
            return merged
    return dict(db.get("guest_settings", DEFAULT_SETTINGS))


def save_settings(settings: dict, username: Optional[str] = None) -> None:
    """Persist settings for the given user (or guest)."""
    db = _load_db()
    if username:
        key = username.strip().lower()
        if key in db["users"]:
            db["users"][key]["settings"] = settings
    else:
        db["guest_settings"] = settings
    _save_db(db)


# ── History ──────────────────────────────────────────────────────────────

def add_history(username: str, equation: str, answer: str) -> None:
    """Append a solve record to the user's history."""
    db = _load_db()
    key = username.strip().lower()
    user = db["users"].get(key)
    if not user:
        return
    record = {
        "equation": equation,
        "answer": answer,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": time.time(),
    }
    user.setdefault("history", []).insert(0, record)  # newest first
    # Keep last 100 entries
    user["history"] = user["history"][:100]
    _save_db(db)


def get_history(username: str) -> list[dict]:
    """Return the user's history list (newest first)."""
    db = _load_db()
    key = username.strip().lower()
    user = db["users"].get(key)
    if not user:
        return []
    return user.get("history", [])


def clear_history(username: str) -> None:
    """Remove all history entries for a user."""
    db = _load_db()
    key = username.strip().lower()
    user = db["users"].get(key)
    if user:
        user["history"] = []
        _save_db(db)
