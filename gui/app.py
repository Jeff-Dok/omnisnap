# gui/app.py
import datetime
import os
import queue as stdlib_queue
import uuid
from pathlib import Path

import customtkinter as ctk

from core.runner import ScraperRunner
from core.store import AppStore
from core.notifier import notify
from core.queue import QueueManager, QueuedTask
from gui import theme as T
from gui.history_view import HistoryView
from gui.queue_view import QueueView
from gui.scrape_view import ScrapeView
from gui.settings_view import SettingsView
from gui.sidebar import Sidebar
from gui.wizard import Wizard


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OmniSnap")
        self.geometry("900x600")
        self.resizable(True, True)
        self.minsize(900, 600)
        self.configure(fg_color=T.BG_MAIN)
        self._store = AppStore()
        T.apply_theme(self._store.get_settings().get("theme", "dark"))
        self._runner: ScraperRunner | None = None
        self._last_url = self._store.get_settings().get("last_url", "")
        self._queue: QueueManager = QueueManager()
        self._build()

    def _build(self):
        self._sidebar = Sidebar(
            self,
            on_new_scrape=self._show_wizard,
            on_history=self._show_history,
            on_settings=self._show_settings,
            on_badge_click=self._show_queue_view,
            on_recent_click=self._on_recent_click,
        )
        self._sidebar.pack(side="left", fill="y")

        self._main = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        self._main.pack(side="left", fill="both", expand=True)

        self._wizard = Wizard(
            self._main, on_launch=self._launch,
            on_enqueue=self._enqueue,
            last_url=self._last_url,
        )
        self._scrape_view = ScrapeView(
            self._main, on_new_scrape=self._show_wizard,
            on_done=self._on_scrape_done,
            on_add_task=self._show_wizard_enqueue,
        )
        self._history_view = HistoryView(
            self._main, store=self._store,
            on_relaunch=self._relaunch_direct,
            on_wizard_relaunch=self._relaunch_wizard,
        )
        self._settings_view = SettingsView(
            self._main, store=self._store,
            on_theme_change=T.apply_theme,
        )
        self._queue_view = QueueView(
            self._main,
            on_close=self._show_scrape_view,
            on_edit=self._on_queue_edit,
            on_remove=self._on_queue_remove,
            on_add=self._show_wizard_enqueue,
            on_clear=self._on_queue_clear,
        )
        self._show_wizard()

    def _hide_all(self):
        for view in (self._wizard, self._scrape_view,
                     self._history_view, self._settings_view, self._queue_view):
            view.pack_forget()

    def _show_wizard(self):
        self._hide_all()
        self._wizard.pack(fill="both", expand=True)
        self._wizard.reset(last_url=self._last_url)
        self._sidebar.set_active("scrape")
        self._refresh_badge(show_see_list=False)

    def _show_scrape_view(self):
        self._hide_all()
        self._scrape_view.pack(fill="both", expand=True)
        self._refresh_badge(show_see_list=True)

    def _show_history(self):
        self._hide_all()
        self._history_view.refresh()
        self._history_view.pack(fill="both", expand=True)
        self._sidebar.set_active("history")
        self._refresh_badge(show_see_list=False)
        self._update_recent()

    def _show_settings(self):
        self._hide_all()
        self._settings_view.refresh()
        self._settings_view.pack(fill="both", expand=True)
        self._sidebar.set_active("settings")
        self._refresh_badge(show_see_list=False)

    def _show_queue_view(self):
        self._hide_all()
        self._queue_view.refresh(self._queue.all())
        self._queue_view.pack(fill="both", expand=True)
        self._refresh_badge(show_see_list=False)

    def _show_wizard_enqueue(self):
        self._hide_all()
        self._wizard.pack(fill="both", expand=True)
        self._wizard.reset(last_url=self._last_url)
        self._wizard.set_enqueue_mode(True)
        self._sidebar.set_active("scrape")
        self._refresh_badge(show_see_list=False)

    def _refresh_badge(self, show_see_list: bool = False) -> None:
        self._sidebar.update_badge(self._queue.count(), show_see_list=show_see_list)

    def _enqueue(self, url: str, modes: list, depth: int, cookies_path: str | None,
                 respect_robots: bool = False, url_filter: str = ""):
        task = QueuedTask(url=url, modes=modes, depth=depth, cookies_path=cookies_path,
                          respect_robots=respect_robots, url_filter=url_filter)
        self._queue.add(task)
        self._show_scrape_view()

    def _launch_queued(self, task: QueuedTask) -> None:
        self._launch(url=task.url, modes=task.modes, depth=task.depth,
                     cookies_path=task.cookies_path, respect_robots=task.respect_robots,
                     url_filter=task.url_filter)

    def _on_queue_remove(self, task_id: str) -> None:
        self._queue.remove(task_id)
        if self._queue.count() == 0:
            self._show_scrape_view()
        else:
            self._queue_view.refresh(self._queue.all())
            self._refresh_badge(show_see_list=False)

    def _on_queue_edit(self, task_id: str) -> None:
        task = next((t for t in self._queue.all() if t.id == task_id), None)
        if task:
            self._queue.remove(task.id)
            self._show_wizard_enqueue()
            self._wizard.prefill(url=task.url, modes=task.modes, depth=task.depth)

    def _on_queue_clear(self) -> None:
        self._queue.clear()
        self._show_scrape_view()

    def _launch(self, url: str, modes: list, depth: int, cookies_path: str | None,
                respect_robots: bool = False, url_filter: str = ""):
        self._last_url = url
        self._store.save_settings({"last_url": url})
        dest_dir = self._store.get_settings().get("dest_dir", "")
        dest_base = Path(dest_dir) if dest_dir else None
        log_queue: stdlib_queue.Queue = stdlib_queue.Queue()
        self._runner = ScraperRunner(
            url=url, modes=modes, depth=depth,
            log_queue=log_queue, dest_base=dest_base,
            cookies_path=cookies_path,
            respect_robots=respect_robots,
            url_filter=url_filter,
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
        self._update_recent()
        settings = self._store.get_settings()
        if settings.get("notifications", True) and result["status"] in ("done", "error"):
            notify(result["status"], result["url"], result)
        if result["status"] == "done" and settings.get("auto_open"):
            dest = entry["dest_path"]
            if dest:
                try:
                    os.startfile(dest)
                except Exception:
                    pass
        next_task = self._queue.next()
        if next_task:
            self._launch_queued(next_task)

    def _relaunch_direct(self, url: str, modes: list, depth: int):
        self._launch(url=url, modes=modes, depth=depth, cookies_path=None)

    def _relaunch_wizard(self, entry: dict):
        self._last_url = entry["url"]
        self._show_wizard()
        self._wizard.prefill(url=entry["url"], modes=entry["modes"], depth=entry["depth"])

    def _update_recent(self) -> None:
        """Met à jour la section Récent de la sidebar avec les 3 dernières entrées."""
        self._sidebar.update_recent(self._store.get_history()[:3])

    def _on_recent_click(self, entry_id: str) -> None:
        """Navigue vers l'historique et sélectionne l'entrée cliquée."""
        self._show_history()
        self._history_view._select_entry(entry_id)
