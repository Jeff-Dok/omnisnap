import os
import queue
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from gui import theme as T


class ScrapeView(ctk.CTkFrame):
    """Vue split : résumé en haut + log en bas. Gère les états en cours / terminé / erreur."""

    def __init__(self, master, on_new_scrape, **kwargs):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0, **kwargs)
        self._on_new_scrape = on_new_scrape
        self._log_queue: queue.Queue | None = None
        self._dest: str = ""
        self._poll_job = None
        self._cancel_fn = None
        self._page_count = 0
        self._file_count = 0
        self._build()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self):
        self._top = ctk.CTkFrame(self, fg_color=T.BG_SURFACE,
                                  corner_radius=0, height=120)
        self._top.pack(fill="x")
        self._top.pack_propagate(False)

        top_inner = ctk.CTkFrame(self._top, fg_color="transparent")
        top_inner.pack(fill="both", expand=True, padx=14, pady=10)

        row1 = ctk.CTkFrame(top_inner, fg_color="transparent")
        row1.pack(fill="x")
        self._lbl_url = ctk.CTkLabel(row1, text="", font=T.FONT_SMALL,
                                      text_color=T.TEXT_DIM, anchor="w")
        self._lbl_url.pack(side="left", fill="x", expand=True)
        self._lbl_status = ctk.CTkLabel(row1, text="● En cours",
                                         font=T.FONT_SMALL, text_color=T.WARNING)
        self._lbl_status.pack(side="left", padx=(8, 12))
        self._btn_action = ctk.CTkButton(
            row1, text="⏹ Annuler", width=110, height=30,
            font=T.FONT_SMALL, corner_radius=5,
            fg_color="#c0392b", hover_color="#a93226", text_color="#ffffff",
            command=self._cancel,
        )
        self._btn_action.pack(side="right")

        self._modes_row = ctk.CTkFrame(top_inner, fg_color="transparent")
        self._modes_row.pack(fill="x", pady=(4, 0))

        self._lbl_counter = ctk.CTkLabel(top_inner, text="",
                                          font=T.FONT_SMALL, text_color=T.TEXT_DIM,
                                          anchor="w")
        self._lbl_counter.pack(fill="x", pady=(6, 2))
        self._progress = ctk.CTkProgressBar(top_inner, fg_color=T.BG_MAIN,
                                             progress_color=T.WARNING, height=4,
                                             corner_radius=2)
        self._progress.pack(fill="x")
        self._progress.configure(mode="indeterminate")
        self._progress.start()

        bottom = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        bottom.pack(fill="both", expand=True, padx=14, pady=(8, 0))

        ctk.CTkLabel(bottom, text="Journal", font=T.FONT_SMALL,
                     text_color=T.TEXT_DIM).pack(anchor="w", pady=(0, 4))

        self._log_box = ctk.CTkTextbox(
            bottom, fg_color=T.LOG_BG, text_color=T.TEXT_DIM,
            font=T.FONT_LOG, wrap="word", state="disabled",
            corner_radius=6,
        )
        self._log_box.pack(fill="both", expand=True)

        self._btn_new = ctk.CTkButton(
            bottom, text="＋ Nouveau scrape", font=T.FONT_NORMAL,
            fg_color=T.BG_SURFACE, hover_color=T.BORDER,
            text_color=T.TEXT_DIM, height=32, corner_radius=5,
            command=self._new_scrape,
        )

    # ── Démarrer ──────────────────────────────────────────────────────────────

    def start(self, url: str, modes: list[int], depth: int, log_queue: queue.Queue,
              runner_cancel_fn):
        from gui.wizard import MODES
        if self._poll_job:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        self._log_queue = log_queue
        self._cancel_fn = runner_cancel_fn

        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        self._btn_new.pack_forget()
        MAX_URL = 60
        display_url = url if len(url) <= MAX_URL else url[:MAX_URL] + "…"
        self._lbl_url.configure(text=display_url)
        self._lbl_status.configure(text="● En cours", text_color=T.WARNING)
        self._lbl_counter.configure(text="")
        self._btn_action.configure(text="⏹ Annuler", fg_color="#c0392b",
                                    hover_color="#a93226", command=self._cancel)
        self._progress.configure(mode="indeterminate", progress_color=T.WARNING)
        self._progress.start()

        for w in self._modes_row.winfo_children():
            w.destroy()
        mode_ids_set = set(modes)
        for mid, _, name, _ in MODES:
            if mid in mode_ids_set:
                tag = ctk.CTkLabel(self._modes_row, text=f" {name} ",
                                   font=T.FONT_SMALL, text_color=T.ACCENT,
                                   fg_color=T.BG_MAIN, corner_radius=10)
                tag.pack(side="left", padx=(0, 4))
        depth_tag = ctk.CTkLabel(self._modes_row, text=f" Profondeur +{depth} ",
                                  font=T.FONT_SMALL, text_color=T.TEXT_DIM,
                                  fg_color=T.BG_MAIN, corner_radius=10)
        depth_tag.pack(side="left")

        self._page_count = 0
        self._file_count = 0
        self._poll()

    # ── Poll queue ────────────────────────────────────────────────────────────

    def _poll(self):
        if self._log_queue is None:
            return
        try:
            while True:
                msg = self._log_queue.get_nowait()
                if isinstance(msg, dict):
                    self._handle_control(msg)
                    return
                self._append_log(msg)
        except queue.Empty:
            pass
        self._poll_job = self.after(100, self._poll)

    def _append_log(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{ts}  {text}\n"
        if "✓" in text:
            color = T.SUCCESS
            if "page" in text.lower() or "analysée" in text.lower():
                self._page_count += 1
        elif "↓" in text or "télécharg" in text.lower():
            color = T.ACCENT
            self._file_count += 1
        elif "⚠" in text:
            color = T.WARNING
        elif "✗" in text:
            color = T.ERROR
        else:
            color = T.TEXT_DIM

        self._lbl_counter.configure(
            text=f"{self._page_count} pages · {self._file_count} fichiers"
        )
        self._log_box.configure(state="normal")
        start = self._log_box._textbox.index("end-1c")
        self._log_box.insert("end", line)
        tag_name = f"col_{color.replace('#', '')}"
        self._log_box._textbox.tag_configure(tag_name, foreground=color)
        self._log_box._textbox.tag_add(tag_name, start, "end-1c")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _handle_control(self, msg: dict):
        if self._poll_job:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        items = []
        try:
            while True:
                items.append(self._log_queue.get_nowait())
        except queue.Empty:
            pass
        for item in items:
            if isinstance(item, str):
                self._append_log(item)
            elif isinstance(item, dict) and item.get("type") in ("done", "cancelled", "error"):
                msg = item
        t = msg.get("type")
        if t == "done":
            self._dest = msg.get("dest", "")
            files = msg.get("files", 0)
            size_mb = msg.get("size_bytes", 0) / (1024 * 1024)
            summary = f"{self._page_count} pages · {files} fichiers · {size_mb:.1f} MB"
            self._set_done(summary)
        elif t == "cancelled":
            self._set_error("Scraping annulé.")
        elif t == "error":
            self._set_error(msg.get("message", "Erreur inconnue"))

    # ── États finaux ──────────────────────────────────────────────────────────

    def _set_done(self, summary: str):
        self._progress.stop()
        self._progress.configure(mode="determinate", progress_color=T.SUCCESS)
        self._progress.set(1.0)
        self._lbl_status.configure(text="✅ Terminé", text_color=T.SUCCESS)
        self._lbl_counter.configure(text=summary)
        self._btn_action.configure(
            text="📂 Ouvrir le dossier", fg_color=T.SUCCESS,
            hover_color="#388e3c", command=self._open_folder,
        )
        self._btn_new.pack(anchor="e", pady=(6, 8))

    def _set_error(self, message: str):
        self._progress.stop()
        self._progress.configure(mode="determinate", progress_color=T.ERROR)
        self._progress.set(1.0)
        self._lbl_status.configure(text="✗ Erreur", text_color=T.ERROR)
        self._lbl_counter.configure(text=message)
        self._btn_action.configure(
            text="↩ Réessayer", fg_color=T.BG_SURFACE,
            hover_color=T.BORDER, text_color=T.TEXT_DIM,
            command=self._on_new_scrape,
        )
        self._btn_new.pack(anchor="e", pady=(6, 8))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _cancel(self):
        if hasattr(self, "_cancel_fn") and self._cancel_fn:
            self._cancel_fn()

    def _open_folder(self):
        if self._dest and Path(self._dest).exists():
            if sys.platform == "win32":
                os.startfile(self._dest)
            else:
                subprocess.Popen(["xdg-open", self._dest])

    def _new_scrape(self):
        self._on_new_scrape()
