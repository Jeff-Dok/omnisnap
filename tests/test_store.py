# tests/test_store.py
import pytest
from core.store import AppStore


def _make_entry(entry_id: str) -> dict:
    return {
        "id": entry_id, "url": "https://example.com", "modes": [1], "depth": 0,
        "status": "done", "date": "2026-01-01T00:00:00",
        "pages": 1, "file_count": 0, "size_mb": 0.0, "dest_path": "", "error_msg": None,
    }


@pytest.fixture
def store(tmp_path):
    return AppStore(base_dir=tmp_path)


def test_settings_defaults(store):
    s = store.get_settings()
    assert s["theme"] == "dark"
    assert s["dest_dir"] == ""
    assert s["auto_open"] is False


def test_save_and_get_settings(store):
    store.save_settings({"theme": "light"})
    assert store.get_settings()["theme"] == "light"


def test_save_settings_merge(store):
    store.save_settings({"theme": "light"})
    store.save_settings({"auto_open": True})
    s = store.get_settings()
    assert s["theme"] == "light"
    assert s["auto_open"] is True


def test_settings_persists_to_disk(tmp_path):
    AppStore(base_dir=tmp_path).save_settings({"theme": "system"})
    assert AppStore(base_dir=tmp_path).get_settings()["theme"] == "system"


def test_add_entry(store):
    store.add_entry(_make_entry("abc"))
    assert store.get_history()[0]["id"] == "abc"


def test_history_order(store):
    store.add_entry(_make_entry("id1"))
    store.add_entry(_make_entry("id2"))
    assert [e["id"] for e in store.get_history()] == ["id2", "id1"]


def test_history_max_30(store):
    for i in range(31):
        store.add_entry(_make_entry(f"id{i:02d}"))
    h = store.get_history()
    assert len(h) == 30
    assert h[0]["id"] == "id30"
    assert "id00" not in [e["id"] for e in h]


def test_delete_entry(store):
    store.add_entry(_make_entry("abc"))
    store.add_entry(_make_entry("xyz"))
    store.delete_entry("abc")
    ids = [e["id"] for e in store.get_history()]
    assert "abc" not in ids and "xyz" in ids


def test_clear_history(store):
    store.add_entry(_make_entry("abc"))
    store.clear_history()
    assert store.get_history() == []


def test_invalid_settings_json_fallback(tmp_path):
    (tmp_path / "settings.json").write_text("{{invalid", encoding="utf-8")
    assert AppStore(base_dir=tmp_path).get_settings()["theme"] == "dark"


def test_invalid_history_json_fallback(tmp_path):
    (tmp_path / "history.json").write_text("not json", encoding="utf-8")
    assert AppStore(base_dir=tmp_path).get_history() == []


def test_atomic_write_no_tmp_file(store, tmp_path):
    store.save_settings({"theme": "light"})
    assert not (tmp_path / "settings.tmp").exists()
