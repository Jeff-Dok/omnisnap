# gui/sidebar.py
import customtkinter as ctk
from gui import theme as T


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_new_scrape, on_history, on_settings, **kwargs):
        super().__init__(master, fg_color=T.BG_SIDEBAR, width=160,
                         corner_radius=0, **kwargs)
        self.pack_propagate(False)
        self._on_new_scrape = on_new_scrape
        self._on_history = on_history
        self._on_settings = on_settings
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="⚡ OmniSnap",
            font=T.FONT_BOLD, text_color=T.ACCENT, anchor="w", padx=12,
        ).pack(fill="x", pady=(14, 0))

        ctk.CTkFrame(self, height=1, fg_color=T.BORDER, corner_radius=0
                     ).pack(fill="x", padx=10, pady=(10, 6))

        self._btn_scrape = ctk.CTkButton(
            self, text="🔍 Nouveau scrape",
            font=T.FONT_SMALL, anchor="w", height=34,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            text_color=T.LOG_BG, corner_radius=6,
            command=self._on_new_scrape,
        )
        self._btn_scrape.pack(fill="x", padx=8, pady=2)

        self._btn_history = ctk.CTkButton(
            self, text="🕐 Historique",
            font=T.FONT_SMALL, anchor="w", height=34,
            fg_color="transparent", hover_color=T.BORDER,
            text_color=T.TEXT_DIM, corner_radius=6,
            command=self._on_history,
        )
        self._btn_history.pack(fill="x", padx=8, pady=2)

        self._btn_settings = ctk.CTkButton(
            self, text="⚙️ Paramètres",
            font=T.FONT_SMALL, anchor="w", height=34,
            fg_color="transparent", hover_color=T.BORDER,
            text_color=T.TEXT_DIM, corner_radius=6,
            command=self._on_settings,
        )
        self._btn_settings.pack(fill="x", padx=8, pady=2)

    def set_active(self, view_name: str) -> None:
        buttons = {
            "scrape": self._btn_scrape,
            "history": self._btn_history,
            "settings": self._btn_settings,
        }
        for name, btn in buttons.items():
            if name == view_name:
                btn.configure(fg_color=T.ACCENT, text_color=T.LOG_BG,
                              hover_color=T.ACCENT_HOVER)
            else:
                btn.configure(fg_color="transparent", text_color=T.TEXT_DIM,
                              hover_color=T.BORDER)
