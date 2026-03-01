import json
from pathlib import Path

from gui import storage


def _configure_tmp_db(monkeypatch, tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_file = data_dir / "dualsolver.json"
    monkeypatch.setattr(storage, "_DATA_DIR", str(data_dir))
    monkeypatch.setattr(storage, "_DATA_FILE", str(data_file))
    return data_file


def test_settings_get_and_save(monkeypatch, tmp_path: Path) -> None:
    _configure_tmp_db(monkeypatch, tmp_path)

    settings = storage.get_settings()
    assert settings["theme"] in {"dark", "light"}

    storage.save_settings({"theme": "light", "animation_speed": "fast"})
    assert storage.get_settings()["theme"] == "light"
    assert storage.get_settings()["animation_speed"] == "fast"


def test_history_add_get_clear_and_limit(monkeypatch, tmp_path: Path) -> None:
    _configure_tmp_db(monkeypatch, tmp_path)

    for i in range(205):
        storage.add_history(f"x + {i} = 0", f"x = {-i}")

    history = storage.get_history()
    assert len(history) == 200
    assert history[0]["equation"] == "x + 204 = 0"
    assert "id" in history[0]

    storage.clear_history()
    assert storage.get_history() == []


def test_history_pin_and_archive(monkeypatch, tmp_path: Path) -> None:
    _configure_tmp_db(monkeypatch, tmp_path)

    rid = storage.add_history("x = 1", "x = 1")

    # Pin
    new_state = storage.toggle_pin(rid)
    assert new_state is True
    history = storage.get_history()
    assert history[0]["pinned"] is True

    # Unpin
    new_state = storage.toggle_pin(rid)
    assert new_state is False

    # Archive
    new_state = storage.toggle_archive(rid)
    assert new_state is True
    # Archived items excluded by default
    assert storage.get_history(include_archived=False) == []
    # But included when requested
    assert len(storage.get_archived_history()) == 1

    # Unarchive
    storage.toggle_archive(rid)
    assert len(storage.get_history()) == 1


def test_delete_history_item(monkeypatch, tmp_path: Path) -> None:
    _configure_tmp_db(monkeypatch, tmp_path)

    rid1 = storage.add_history("x = 1", "x = 1")
    rid2 = storage.add_history("y = 2", "y = 2")

    storage.delete_history_item(rid1)
    history = storage.get_history()
    assert len(history) == 1
    assert history[0]["id"] == rid2


def test_clear_all_data(monkeypatch, tmp_path: Path) -> None:
    _configure_tmp_db(monkeypatch, tmp_path)

    storage.save_settings({"theme": "light", "animation_speed": "fast"})
    storage.add_history("x = 1", "x = 1")
    storage.clear_all_data()

    assert storage.get_settings()["theme"] == "dark"
    assert storage.get_history() == []


def test_load_db_handles_invalid_json(monkeypatch, tmp_path: Path) -> None:
    data_file = _configure_tmp_db(monkeypatch, tmp_path)
    data_file.parent.mkdir(parents=True, exist_ok=True)
    data_file.write_text("{not-json", encoding="utf-8")

    db = storage._load_db()
    assert "settings" in db
    assert "history" in db


def test_save_db_persists_content(monkeypatch, tmp_path: Path) -> None:
    data_file = _configure_tmp_db(monkeypatch, tmp_path)
    storage._save_db({"settings": {"theme": "dark"}, "history": []})
    content = json.loads(data_file.read_text(encoding="utf-8"))
    assert content["settings"]["theme"] == "dark"


def test_migrate_old_format(monkeypatch, tmp_path: Path) -> None:
    """Test that the old user-based format is migrated to the new flat format."""
    data_file = _configure_tmp_db(monkeypatch, tmp_path)
    data_file.parent.mkdir(parents=True, exist_ok=True)
    old_data = {
        "users": {"alice": {"settings": {"theme": "light"}, "history": []}},
        "guest_settings": {"theme": "dark", "animation_speed": "normal",
                           "show_verification": False, "show_graph": True},
    }
    data_file.write_text(json.dumps(old_data), encoding="utf-8")

    db = storage._load_db()
    assert "history" in db
    assert "settings" in db
    assert "users" not in db
