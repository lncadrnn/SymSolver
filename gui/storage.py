"""
DualSolver — Local JSON storage for history and settings.

Data is persisted in ``<project>/data/dualsolver.json``.
All data is local — no user accounts required.
"""

import json
import os
import time
import uuid
from datetime import datetime

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
_DATA_FILE = os.path.join(_DATA_DIR, "dualsolver.json")

# ── Default settings ────────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "theme": "dark",
    "animation_speed": "normal",   # "slow", "normal", "fast", "instant"
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
                data = json.load(f)
                # Migrate old format if needed
                if "users" in data and "history" not in data:
                    data = {
                        "settings": data.get("guest_settings", dict(DEFAULT_SETTINGS)),
                        "history": [],
                    }
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"settings": dict(DEFAULT_SETTINGS), "history": []}


def _save_db(db: dict) -> None:
    _ensure_dir()
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


# ── Settings ─────────────────────────────────────────────────────────────

def get_settings() -> dict:
    """Return the settings dict."""
    db = _load_db()
    merged = dict(DEFAULT_SETTINGS)
    merged.update(db.get("settings", {}))
    return merged


def save_settings(settings: dict) -> None:
    """Persist settings."""
    db = _load_db()
    db["settings"] = settings
    _save_db(db)


# ── History ──────────────────────────────────────────────────────────────

def add_history(equation: str, answer: str) -> str:
    """Append a solve record to history. Returns the new record's ID."""
    db = _load_db()
    record_id = uuid.uuid4().hex[:12]
    record = {
        "id": record_id,
        "equation": equation,
        "answer": answer,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": time.time(),
        "pinned": False,
        "archived": False,
    }
    db.setdefault("history", []).insert(0, record)  # newest first
    # Keep last 200 entries
    db["history"] = db["history"][:200]
    _save_db(db)
    return record_id


def get_history(include_archived: bool = False) -> list[dict]:
    """Return history list (newest first). Excludes archived by default."""
    db = _load_db()
    history = db.get("history", [])
    if not include_archived:
        history = [r for r in history if not r.get("archived", False)]
    return history


def get_archived_history() -> list[dict]:
    """Return only archived history entries."""
    db = _load_db()
    return [r for r in db.get("history", []) if r.get("archived", False)]


def delete_history_item(record_id: str) -> None:
    """Delete a single history entry by ID."""
    db = _load_db()
    db["history"] = [r for r in db.get("history", []) if r.get("id") != record_id]
    _save_db(db)


def toggle_pin(record_id: str) -> bool:
    """Toggle the pinned state of a history entry. Returns new pinned state."""
    db = _load_db()
    for r in db.get("history", []):
        if r.get("id") == record_id:
            r["pinned"] = not r.get("pinned", False)
            _save_db(db)
            return r["pinned"]
    return False


def toggle_archive(record_id: str) -> bool:
    """Toggle the archived state of a history entry. Returns new archived state."""
    db = _load_db()
    for r in db.get("history", []):
        if r.get("id") == record_id:
            r["archived"] = not r.get("archived", False)
            _save_db(db)
            return r["archived"]
    return False


def clear_history() -> None:
    """Remove all history entries."""
    db = _load_db()
    db["history"] = []
    _save_db(db)


def clear_all_data() -> None:
    """Reset everything — settings and history."""
    db = {"settings": dict(DEFAULT_SETTINGS), "history": []}
    _save_db(db)
