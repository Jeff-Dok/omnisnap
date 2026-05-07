# gui/settings_view.py
from tkinter import filedialog

import customtkinter as ctk

from gui import theme as T


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, store, on_theme_change, **kwargs):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0, **kwargs)
        self._store = store
        self._on_theme_change = on_theme_change
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkFrame(header, height=1, fg_color=T.BORDER,
                     corner_radius=0).pack(fill="x", side="bottom")
        ctk.CTkLabel(header, text="Paramètres", font=T.FONT_TITLE,
                     text_color=T.TEXT, anchor="w", padx=20).pack(fill="x", pady=(12, 10))

        body = ctk.CTkScrollableFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        body.pack(fill="both", expand=True, padx=20, pady=12)

        # Apparence
        self._sec(body, "Apparence")
        self._theme_seg = ctk.CTkSegmentedButton(
            body, values=["🌙 Sombre", "☀️ Clair", "💻 Système"],
            font=T.FONT_SMALL, fg_color=T.BG_SURFACE,
            selected_color=T.ACCENT, selected_hover_color=T.ACCENT_HOVER,
            unselected_color=T.BG_SURFACE, unselected_hover_color=T.BORDER,
            text_color=T.TEXT_DIM,
            command=self._on_theme_seg,
        )
        self._theme_seg.pack(anchor="w", pady=(0, 16))
        self._div(body)

        # Dossier de sortie
        self._sec(body, "Dossier de sortie")
        folder_row = ctk.CTkFrame(body, fg_color="transparent")
        folder_row.pack(fill="x", pady=(0, 4))
        self._folder_entry = ctk.CTkEntry(
            folder_row, font=("Consolas", 11),
            fg_color=T.BG_SURFACE, border_color=T.BORDER,
            text_color=T.TEXT, state="readonly",
        )
        self._folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            folder_row, text="📁 Parcourir…", font=T.FONT_SMALL,
            fg_color=T.BG_SURFACE, hover_color=T.BORDER, text_color=T.TEXT,
            height=32, corner_radius=5, border_width=1, border_color=T.BORDER,
            command=self._browse_folder,
        ).pack(side="right")
        ctk.CTkLabel(
            body,
            text="Les fichiers scrapés seront enregistrés ici. "
                 "Laissez vide pour utiliser le dossier par défaut.",
            font=T.FONT_SMALL, text_color=T.TEXT_DIM, anchor="w",
        ).pack(fill="x", pady=(0, 16))
        self._div(body)

        # Comportement
        self._sec(body, "Comportement")
        toggle_row = ctk.CTkFrame(body, fg_color="transparent")
        toggle_row.pack(fill="x", pady=(0, 16))
        info = ctk.CTkFrame(toggle_row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(info, text="Ouvrir le dossier après scraping",
                     font=T.FONT_NORMAL, text_color=T.TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(
            info,
            text="Ouvre automatiquement l'explorateur quand un scrape se termine avec succès",
            font=T.FONT_SMALL, text_color=T.TEXT_DIM, anchor="w",
        ).pack(fill="x")
        self._switch_auto = ctk.CTkSwitch(
            toggle_row, text="",
            fg_color=T.BORDER, progress_color=T.ACCENT,
            command=self._on_auto_toggle,
        )
        self._switch_auto.pack(side="right", padx=(16, 0))
        self._div(body)

        # À propos
        self._sec(body, "À propos")
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="OmniSnap",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM).pack(side="left")
        ctk.CTkLabel(row, text=f"Version {T.VERSION}",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM).pack(side="right")

    @staticmethod
    def _sec(parent, text: str):
        ctk.CTkLabel(parent, text=text.upper(), font=("Segoe UI", 10, "bold"),
                     text_color=T.TEXT_DIM, anchor="w").pack(fill="x", pady=(0, 8))

    @staticmethod
    def _div(parent):
        ctk.CTkFrame(parent, height=1, fg_color=T.BORDER,
                     corner_radius=0).pack(fill="x", pady=(0, 16))

    def refresh(self) -> None:
        settings = self._store.get_settings()
        theme_map = {"dark": "🌙 Sombre", "light": "☀️ Clair", "system": "💻 Système"}
        self._theme_seg.set(theme_map.get(settings.get("theme", "dark"), "🌙 Sombre"))
        dest = settings.get("dest_dir", "")
        self._folder_entry.configure(state="normal")
        self._folder_entry.delete(0, "end")
        if dest:
            self._folder_entry.insert(0, dest)
        self._folder_entry.configure(state="readonly")
        if settings.get("auto_open", False):
            self._switch_auto.select()
        else:
            self._switch_auto.deselect()

    def _on_theme_seg(self, value: str) -> None:
        name_map = {"🌙 Sombre": "dark", "☀️ Clair": "light", "💻 Système": "system"}
        name = name_map.get(value, "dark")
        self._store.save_settings({"theme": name})
        self._on_theme_change(name)

    def _browse_folder(self) -> None:
        path = filedialog.askdirectory(title="Choisir le dossier de sortie")
        if path:
            self._folder_entry.configure(state="normal")
            self._folder_entry.delete(0, "end")
            self._folder_entry.insert(0, path)
            self._folder_entry.configure(state="readonly")
            self._store.save_settings({"dest_dir": path})

    def _on_auto_toggle(self) -> None:
        self._store.save_settings({"auto_open": bool(self._switch_auto.get())})
