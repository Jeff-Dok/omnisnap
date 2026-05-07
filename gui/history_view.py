# gui/history_view.py
import os
import urllib.parse
from datetime import datetime, date
from pathlib import Path

import customtkinter as ctk

from gui import theme as T
from gui.wizard import MODES, DEPTH_LABELS

_MODE_LABELS: dict[int, str] = {mid: f"{icon} {name}" for mid, icon, name, _ in MODES}
_DEPTH_LABELS: list[str] = [f"Profondeur {label}" for label, _ in DEPTH_LABELS]


def _format_date(iso_date: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_date)
        delta = (date.today() - dt.date()).days
        hm = dt.strftime("%H:%M")
        if delta == 0:
            return f"Aujourd'hui {hm}"
        if delta == 1:
            return f"Hier {hm}"
        if delta == 2:
            return f"Avant-hier {hm}"
        months = ["jan","fév","mars","avr","mai","juin",
                  "juil","août","sep","oct","nov","déc"]
        return f"{dt.day} {months[dt.month - 1]} {hm}"
    except Exception:
        return iso_date


def _domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc or url[:40]
    except Exception:
        return url[:40]


class _EntryRow(ctk.CTkFrame):
    def __init__(self, master, entry: dict, selected: bool,
                 on_select, on_delete, **kwargs):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0, **kwargs)
        self._entry = entry
        self._selected = selected
        self._on_select = on_select
        self._on_delete = on_delete
        self._hovered = False
        self._build()
        self._bind_hover_recursive(self)
        self._apply_selection(selected)

    def _build(self):
        self._border_bar = ctk.CTkFrame(self, width=3, fg_color="transparent",
                                         corner_radius=0)
        self._border_bar.pack(side="left", fill="y")
        self._border_bar.pack_propagate(False)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=(6, 36), pady=8)

        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill="x")
        url_display = self._entry.get("url", "")
        if len(url_display) > 65:
            url_display = url_display[:62] + "…"
        ctk.CTkLabel(row1, text=url_display, font=T.FONT_SMALL,
                     text_color=T.TEXT, anchor="w").pack(side="left", fill="x", expand=True)
        status_text, status_color = self._status_info()
        ctk.CTkLabel(row1, text=status_text, font=T.FONT_SMALL,
                     text_color=status_color).pack(side="right")

        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill="x", pady=(3, 0))
        ctk.CTkLabel(row2, text=_format_date(self._entry.get("date", "")),
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM).pack(side="left")
        ctk.CTkLabel(row2, text=" · ", font=T.FONT_SMALL,
                     text_color=T.BORDER).pack(side="left")
        for mode_id in self._entry.get("modes", []):
            label = _MODE_LABELS.get(mode_id)
            if label:
                ctk.CTkLabel(row2, text=f" {label} ", font=("Segoe UI", 10),
                             text_color=T.ACCENT, fg_color="#0d1f2d",
                             corner_radius=4).pack(side="left", padx=(0, 3))
        depth = self._entry.get("depth", 0)
        depth_idx = max(0, min(depth, len(_DEPTH_LABELS) - 1))
        ctk.CTkLabel(row2, text=f" {_DEPTH_LABELS[depth_idx]} ",
                     font=("Segoe UI", 10), text_color=T.TEXT_DIM,
                     fg_color=T.BG_SURFACE, corner_radius=4).pack(side="left")

        row3_text, row3_color = self._row3_info()
        ctk.CTkLabel(content, text=row3_text, font=T.FONT_SMALL,
                     text_color=row3_color, anchor="w").pack(fill="x", pady=(2, 0))

        self._btn_x = ctk.CTkButton(
            self, text="✕", width=22, height=22, font=("Segoe UI", 11),
            corner_radius=4, fg_color="transparent", hover_color="#3d1010",
            text_color=T.TEXT_DIM, border_width=0,
            command=lambda: self._on_delete(self._entry["id"]),
        )

        for w in (self, content, row1, row2):
            w.bind("<Button-1>",
                   lambda e: self._on_select(self._entry["id"]), add="+")

    def _bind_hover_recursive(self, widget):
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave_check, add="+")
        for child in widget.winfo_children():
            self._bind_hover_recursive(child)

    def _on_enter(self, event=None):
        if not self._hovered:
            self._hovered = True
            self._btn_x.place(relx=1.0, rely=0.5, x=-10, anchor="e")
            if not self._selected:
                self.configure(fg_color="#1c2644")

    def _on_leave_check(self, event=None):
        try:
            px, py = self.winfo_pointerxy()
            bx, by = self.winfo_rootx(), self.winfo_rooty()
            bw, bh = self.winfo_width(), self.winfo_height()
            if bx <= px < bx + bw and by <= py < by + bh:
                return
        except Exception:
            pass
        if self._hovered:
            self._hovered = False
            self._btn_x.place_forget()
            if not self._selected:
                self.configure(fg_color=T.BG_MAIN)

    def _apply_selection(self, selected: bool):
        self._selected = selected
        if selected:
            self.configure(fg_color="#0e1e30")
            self._border_bar.configure(fg_color=T.ACCENT)
        else:
            self.configure(fg_color="#1c2644" if self._hovered else T.BG_MAIN)
            self._border_bar.configure(fg_color="transparent")

    def _status_info(self) -> tuple:
        return {
            "done": ("✅ Terminé", T.SUCCESS),
            "error": ("✗ Erreur", T.ERROR),
            "cancelled": ("⏹ Annulé", T.WARNING),
        }.get(self._entry.get("status", "done"), ("?", T.TEXT_DIM))

    def _row3_info(self) -> tuple:
        if self._entry.get("status") == "error" and self._entry.get("error_msg"):
            return self._entry["error_msg"], T.ERROR
        pages = self._entry.get("pages", 0)
        files = self._entry.get("file_count", 0)
        size = self._entry.get("size_mb", 0.0)
        return f"{pages} pages · {files} fichiers · {size:.1f} MB", T.TEXT_DIM


class HistoryView(ctk.CTkFrame):
    def __init__(self, master, store, on_relaunch, on_wizard_relaunch, **kwargs):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0, **kwargs)
        self._store = store
        self._on_relaunch = on_relaunch
        self._on_wizard_relaunch = on_wizard_relaunch
        self._selected_id: str | None = None
        self._rows: dict = {}
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkFrame(header, height=1, fg_color=T.BORDER,
                     corner_radius=0).pack(fill="x", side="bottom")
        inner_h = ctk.CTkFrame(header, fg_color="transparent")
        inner_h.pack(fill="x", padx=20, pady=(12, 10))
        ctk.CTkLabel(inner_h, text="Historique", font=T.FONT_TITLE,
                     text_color=T.TEXT).pack(side="left")
        ctk.CTkButton(
            inner_h, text="🗑 Vider tout", font=T.FONT_SMALL,
            fg_color="transparent", hover_color=T.BORDER, text_color=T.TEXT_DIM,
            height=26, corner_radius=4, border_width=1, border_color=T.BORDER,
            command=self._clear_all,
        ).pack(side="right")

        self._list = ctk.CTkScrollableFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        self._list.pack(fill="both", expand=True)

        self._action_bar = ctk.CTkFrame(self, fg_color=T.BG_SURFACE, corner_radius=0)
        ctk.CTkFrame(self._action_bar, height=1, fg_color=T.BORDER,
                     corner_radius=0).pack(fill="x", side="top")
        bar_inner = ctk.CTkFrame(self._action_bar, fg_color="transparent")
        bar_inner.pack(fill="x", padx=20, pady=8)
        self._lbl_info = ctk.CTkLabel(bar_inner, text="", font=T.FONT_SMALL,
                                       text_color=T.TEXT_DIM)
        self._lbl_info.pack(side="left")
        btns = ctk.CTkFrame(bar_inner, fg_color="transparent")
        btns.pack(side="right")
        for text, cmd, style in [
            ("🗑 Supprimer", self._delete_selected,
             {"fg_color": "transparent", "text_color": T.TEXT_DIM,
              "border_width": 1, "border_color": T.BORDER}),
            ("📂 Ouvrir le dossier", self._open_folder,
             {"fg_color": "transparent", "text_color": T.TEXT_DIM,
              "border_width": 1, "border_color": T.BORDER}),
            ("✏️ Modifier et relancer", self._relaunch_wizard,
             {"fg_color": "transparent", "text_color": T.TEXT,
              "border_width": 1, "border_color": T.BORDER}),
            ("▶ Relancer directement", self._relaunch_direct,
             {"fg_color": T.ACCENT, "text_color": T.LOG_BG,
              "hover_color": T.ACCENT_HOVER}),
        ]:
            ctk.CTkButton(btns, text=text, font=T.FONT_SMALL, height=28,
                          corner_radius=5, hover_color=T.BORDER,
                          command=cmd, **style).pack(side="left", padx=(0, 6))

    def refresh(self) -> None:
        for w in self._list.winfo_children():
            w.destroy()
        self._rows.clear()
        history = self._store.get_history()
        if not history:
            ctk.CTkLabel(
                self._list,
                text="🕐\n\nAucun scrape dans l'historique.\n"
                     "Lancez votre premier scrape depuis \"Nouveau scrape\".",
                font=T.FONT_NORMAL, text_color=T.TEXT_DIM, justify="center",
            ).pack(expand=True, pady=60)
            self._hide_action_bar()
            return

        for entry in history:
            selected = (entry["id"] == self._selected_id)
            row = _EntryRow(self._list, entry=entry, selected=selected,
                            on_select=self._select_entry, on_delete=self._delete_entry)
            row.pack(fill="x")
            ctk.CTkFrame(self._list, height=1, fg_color=T.BORDER,
                         corner_radius=0).pack(fill="x")
            self._rows[entry["id"]] = row

        if self._selected_id and self._selected_id in self._rows:
            entry = next((e for e in history if e["id"] == self._selected_id), None)
            if entry:
                self._update_action_bar(entry)
                self._show_action_bar()
            else:
                self._selected_id = None
                self._hide_action_bar()
        else:
            self._hide_action_bar()

    def _select_entry(self, entry_id: str) -> None:
        if self._selected_id == entry_id:
            self._selected_id = None
            if entry_id in self._rows:
                self._rows[entry_id]._apply_selection(False)
            self._hide_action_bar()
            return
        if self._selected_id and self._selected_id in self._rows:
            self._rows[self._selected_id]._apply_selection(False)
        self._selected_id = entry_id
        if entry_id in self._rows:
            self._rows[entry_id]._apply_selection(True)
        entry = next((e for e in self._store.get_history() if e["id"] == entry_id), None)
        if entry:
            self._update_action_bar(entry)
            self._show_action_bar()

    def _update_action_bar(self, entry: dict) -> None:
        domain = _domain(entry.get("url", ""))
        files = entry.get("file_count", 0)
        size = entry.get("size_mb", 0.0)
        self._lbl_info.configure(text=f"{domain} · {files} fichiers · {size:.1f} MB")

    def _show_action_bar(self):
        self._action_bar.pack(fill="x", side="bottom")

    def _hide_action_bar(self):
        self._action_bar.pack_forget()

    def _delete_entry(self, entry_id: str) -> None:
        self._store.delete_entry(entry_id)
        if self._selected_id == entry_id:
            self._selected_id = None
        self.refresh()

    def _delete_selected(self) -> None:
        if self._selected_id:
            self._delete_entry(self._selected_id)

    def _clear_all(self) -> None:
        dialog = ctk.CTkInputDialog(
            text="Supprimer tout l'historique ?\n\nTapez « effacer » pour confirmer.",
            title="Confirmer suppression",
        )
        value = dialog.get_input()
        if value and value.strip().lower() == "effacer":
            self._selected_id = None
            self._store.clear_history()
            self.refresh()

    def _open_folder(self) -> None:
        if not self._selected_id:
            return
        entry = next((e for e in self._store.get_history()
                      if e["id"] == self._selected_id), None)
        if entry:
            dest = entry.get("dest_path", "")
            if dest and Path(dest).exists():
                try:
                    os.startfile(dest)
                except Exception:
                    pass

    def _relaunch_wizard(self) -> None:
        if not self._selected_id:
            return
        entry = next((e for e in self._store.get_history()
                      if e["id"] == self._selected_id), None)
        if entry:
            self._on_wizard_relaunch(entry)

    def _relaunch_direct(self) -> None:
        if not self._selected_id:
            return
        entry = next((e for e in self._store.get_history()
                      if e["id"] == self._selected_id), None)
        if entry:
            self._on_relaunch(entry["url"], entry["modes"], entry["depth"])
