import json
import os
import queue
from pathlib import Path

import customtkinter as ctk

from gui import theme as T
from gui.sidebar import Sidebar
from gui.wizard import Wizard
from gui.scrape_view import ScrapeView
from core.runner import ScraperRunner

PREFS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "OmniSnap"
PREFS_FILE = PREFS_DIR / "prefs.json"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OmniSnap")
        self.geometry("900x600")
        self.resizable(False, False)
        self.configure(fg_color=T.BG_MAIN)
        self._runner: ScraperRunner | None = None
        self._last_url = self._load_prefs().get("last_url", "")
        self._build()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self):
        self._sidebar = Sidebar(self, on_new_scrape=self._show_wizard)
        self._sidebar.pack(side="left", fill="y")

        self._main = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        self._main.pack(side="left", fill="both", expand=True)

        self._wizard = Wizard(self._main, on_launch=self._launch,
                               last_url=self._last_url)
        self._scrape_view = ScrapeView(self._main, on_new_scrape=self._show_wizard)

        self._show_wizard()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _show_wizard(self):
        self._scrape_view.pack_forget()
        self._wizard.pack(fill="both", expand=True)
        self._wizard.reset(last_url=self._last_url)
        self._sidebar.set_active("scrape")

    def _show_scrape_view(self):
        self._wizard.pack_forget()
        self._scrape_view.pack(fill="both", expand=True)

    # ── Lancement scraping ────────────────────────────────────────────────────

    def _launch(self, url: str, modes: list[int], depth: int,
                cookies_path: str | None):
        self._last_url = url
        self._save_prefs({"last_url": url})

        log_queue: queue.Queue = queue.Queue()
        self._runner = ScraperRunner(
            url=url,
            modes=modes,
            depth=depth,
            log_queue=log_queue,
            cookies_path=cookies_path,
        )
        self._show_scrape_view()
        self._scrape_view.start(
            url=url,
            modes=modes,
            depth=depth,
            log_queue=log_queue,
            runner_cancel_fn=self._runner.cancel,
        )
        self._runner.start()

    # ── Persistance ───────────────────────────────────────────────────────────

    def _load_prefs(self) -> dict:
        try:
            return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_prefs(self, data: dict):
        try:
            PREFS_DIR.mkdir(parents=True, exist_ok=True)
            PREFS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
