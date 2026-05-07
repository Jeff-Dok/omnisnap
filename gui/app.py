# gui/app.py
import datetime
import os
import queue
import uuid
from pathlib import Path

import customtkinter as ctk

from core.runner import ScraperRunner
from core.store import AppStore
from gui import theme as T
from gui.history_view import HistoryView
from gui.scrape_view import ScrapeView
from gui.settings_view import SettingsView
from gui.sidebar import Sidebar
from gui.wizard import Wizard


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OmniSnap")
        self.geometry("900x600")
        self.resizable(False, False)
        self.configure(fg_color=T.BG_MAIN)
        self._store = AppStore()
        T.apply_theme(self._store.get_settings().get("theme", "dark"))
        self._runner: ScraperRunner | None = None
        self._last_url = self._store.get_settings().get("last_url", "")
        self._build()

    def _build(self):
        self._sidebar = Sidebar(
            self,
            on_new_scrape=self._show_wizard,
            on_history=self._show_history,
            on_settings=self._show_settings,
        )
        self._sidebar.pack(side="left", fill="y")

        self._main = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        self._main.pack(side="left", fill="both", expand=True)

        self._wizard = Wizard(self._main, on_launch=self._launch,
                               last_url=self._last_url)
        self._scrape_view = ScrapeView(self._main, on_new_scrape=self._show_wizard,
                                        on_done=self._on_scrape_done)
        self._history_view = HistoryView(
            self._main, store=self._store,
            on_relaunch=self._relaunch_direct,
            on_wizard_relaunch=self._relaunch_wizard,
        )
        self._settings_view = SettingsView(
            self._main, store=self._store,
            on_theme_change=T.apply_theme,
        )
        self._show_wizard()

    def _hide_all(self):
        for view in (self._wizard, self._scrape_view,
                     self._history_view, self._settings_view):
            view.pack_forget()

    def _show_wizard(self):
        self._hide_all()
        self._wizard.pack(fill="both", expand=True)
        self._wizard.reset(last_url=self._last_url)
        self._sidebar.set_active("scrape")

    def _show_scrape_view(self):
        self._hide_all()
        self._scrape_view.pack(fill="both", expand=True)

    def _show_history(self):
        self._hide_all()
        self._history_view.refresh()
        self._history_view.pack(fill="both", expand=True)
        self._sidebar.set_active("history")

    def _show_settings(self):
        self._hide_all()
        self._settings_view.refresh()
        self._settings_view.pack(fill="both", expand=True)
        self._sidebar.set_active("settings")

    def _launch(self, url: str, modes: list, depth: int, cookies_path: str | None):
        self._last_url = url
        self._store.save_settings({"last_url": url})
        dest_dir = self._store.get_settings().get("dest_dir", "")
        dest_base = Path(dest_dir) if dest_dir else None
        log_queue: queue.Queue = queue.Queue()
        self._runner = ScraperRunner(
            url=url, modes=modes, depth=depth,
            log_queue=log_queue, dest_base=dest_base,
            cookies_path=cookies_path,
        )
        self._show_scrape_view()
        self._scrape_view.start(url=url, modes=modes, depth=depth,
                                 log_queue=log_queue,
                                 runner_cancel_fn=self._runner.cancel)
        self._runner.start()

    def _on_scrape_done(self, result: dict):
        entry = {
            "id": str(uuid.uuid4()),
            "url": result["url"],
            "modes": result["modes"],
            "depth": result["depth"],
            "status": result["status"],
            "date": datetime.datetime.now().isoformat(timespec="seconds"),
            "pages": result.get("pages", 0),
            "file_count": result.get("file_count", 0),
            "size_mb": result.get("size_mb", 0.0),
            "dest_path": result.get("dest_path", ""),
            "error_msg": result.get("error_msg"),
        }
        self._store.add_entry(entry)
        if result["status"] == "done" and self._store.get_settings().get("auto_open"):
            dest = entry["dest_path"]
            if dest:
                try:
                    os.startfile(dest)
                except Exception:
                    pass

    def _relaunch_direct(self, url: str, modes: list, depth: int):
        self._launch(url=url, modes=modes, depth=depth, cookies_path=None)

    def _relaunch_wizard(self, entry: dict):
        self._last_url = entry["url"]
        self._show_wizard()
        self._wizard.prefill(url=entry["url"], modes=entry["modes"], depth=entry["depth"])
