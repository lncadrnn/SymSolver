import json
from pathlib import Path

from gui import storage


def _configure_tmp_db(monkeypatch, tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_file = data_dir / "symsolver.json"
    monkeypatch.setattr(storage, "_DATA_DIR", str(data_dir))
    monkeypatch.setattr(storage, "_DATA_FILE", str(data_file))
    return data_file


def test_hash_password_deterministic() -> None:
    assert storage._hash_pw("pass123") == storage._hash_pw("pass123")


def test_register_and_login_validation_rules(monkeypatch, tmp_path: Path) -> None:
    _configure_tmp_db(monkeypatch, tmp_path)

    ok, msg = storage.register_user("", "abcd")
    assert ok is False and "cannot be empty" in msg.lower()

    ok, msg = storage.register_user("ab", "abcd")
    assert ok is False and "at least 3" in msg.lower()

    ok, msg = storage.register_user("alice", "123")
    assert ok is False and "at least 4" in msg.lower()

    ok, msg = storage.register_user("alice", "1234")
    assert ok is True

    ok, msg = storage.register_user("Alice", "1234")
    assert ok is False and "already" in msg.lower()

    ok, msg = storage.login_user("alice", "bad")
    assert ok is False and "incorrect" in msg.lower()

    ok, display = storage.login_user("alice", "1234")
    assert ok is True and display == "alice"


def test_settings_get_and_save(monkeypatch, tmp_path: Path) -> None:
    _configure_tmp_db(monkeypatch, tmp_path)
    storage.register_user("user1", "abcd")

    guest = storage.get_settings()
    assert guest["theme"] in {"dark", "light"}

    storage.save_settings({"theme": "light", "animation_speed": "fast"})
    assert storage.get_settings()["theme"] == "light"

    storage.save_settings({"theme": "light", "animation_speed": "instant"}, username="user1")
    user_settings = storage.get_settings("user1")
    assert user_settings["theme"] == "light"
    assert user_settings["animation_speed"] == "instant"


def test_history_add_get_clear_and_limit(monkeypatch, tmp_path: Path) -> None:
    _configure_tmp_db(monkeypatch, tmp_path)
    storage.register_user("bob", "abcd")

    for i in range(105):
        storage.add_history("bob", f"x + {i} = 0", f"x = {-i}")

    history = storage.get_history("bob")
    assert len(history) == 100
    assert history[0]["equation"] == "x + 104 = 0"

    storage.clear_history("bob")
    assert storage.get_history("bob") == []


def test_load_db_handles_invalid_json(monkeypatch, tmp_path: Path) -> None:
    data_file = _configure_tmp_db(monkeypatch, tmp_path)
    data_file.parent.mkdir(parents=True, exist_ok=True)
    data_file.write_text("{not-json", encoding="utf-8")

    db = storage._load_db()
    assert "users" in db
    assert "guest_settings" in db


def test_save_db_persists_content(monkeypatch, tmp_path: Path) -> None:
    data_file = _configure_tmp_db(monkeypatch, tmp_path)
    storage._save_db({"users": {}, "guest_settings": {"theme": "dark"}})
    content = json.loads(data_file.read_text(encoding="utf-8"))
    assert content["guest_settings"]["theme"] == "dark"
