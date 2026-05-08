# core/store.py
import json
import os
from pathlib import Path

_DEFAULT_DIR = Path(os.environ.get("APPDATA", Path.home())) / "OmniSnap"
_MAX_HISTORY = 30
_DEFAULT_SETTINGS: dict = {"theme": "dark", "dest_dir": "", "auto_open": False, "notifications": True}


class AppStore:
    def __init__(self, base_dir: Path | None = None):
        self._dir = Path(base_dir) if base_dir else _DEFAULT_DIR
        self._settings: dict | None = None
        self._history: list | None = None

    def get_settings(self) -> dict:
        if self._settings is None:
            raw = self._load_json(self._dir / "settings.json", {})
            self._settings = {**_DEFAULT_SETTINGS, **raw}
        return dict(self._settings)

    def save_settings(self, partial: dict) -> None:
        current = self.get_settings()
        current.update(partial)
        self._settings = current
        self._write_json(self._dir / "settings.json", current)

    def get_history(self) -> list:
        if self._history is None:
            self._history = self._load_json(self._dir / "history.json", [])
        return list(self._history)

    def add_entry(self, entry: dict) -> None:
        history = self.get_history()
        history.insert(0, entry)
        if len(history) > _MAX_HISTORY:
            history = history[:_MAX_HISTORY]
        self._history = history
        self._write_json(self._dir / "history.json", history)

    def delete_entry(self, entry_id: str) -> None:
        history = [e for e in self.get_history() if e.get("id") != entry_id]
        self._history = history
        self._write_json(self._dir / "history.json", history)

    def clear_history(self) -> None:
        self._history = []
        self._write_json(self._dir / "history.json", [])

    @staticmethod
    def _load_json(path: Path, default):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, type(default)) else default
        except Exception:
            return default

    def _write_json(self, path: Path, data) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
