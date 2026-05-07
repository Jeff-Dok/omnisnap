import customtkinter as ctk
from gui import theme as T


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_new_scrape, **kwargs):
        super().__init__(master, fg_color=T.BG_SIDEBAR, width=160, corner_radius=0, **kwargs)
        self.pack_propagate(False)
        self._on_new_scrape = on_new_scrape
        self._build()

    def _build(self):
        logo = ctk.CTkLabel(
            self, text="⚡ OmniSnap",
            font=T.FONT_BOLD, text_color=T.ACCENT,
            anchor="w", padx=12,
        )
        logo.pack(fill="x", pady=(14, 0))

        sep = ctk.CTkFrame(self, height=1, fg_color=T.BORDER, corner_radius=0)
        sep.pack(fill="x", padx=10, pady=(10, 6))

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
            state="disabled",
        )
        self._btn_history.pack(fill="x", padx=8, pady=2)

        self._btn_settings = ctk.CTkButton(
            self, text="⚙️ Paramètres",
            font=T.FONT_SMALL, anchor="w", height=34,
            fg_color="transparent", hover_color=T.BORDER,
            text_color=T.TEXT_DIM, corner_radius=6,
            state="disabled",
        )
        self._btn_settings.pack(fill="x", padx=8, pady=2)

        ctk.CTkLabel(
            self, text="Disponible en Phase 2",
            font=T.FONT_SMALL, text_color=T.TEXT_DIM,
            anchor="center",
        ).pack(fill="x", padx=8, pady=(0, 4))

    def set_active(self, view_name: str):
        """Mettre en surbrillance le bouton correspondant à la vue active."""
        is_scrape = view_name == "scrape"
        self._btn_scrape.configure(
            fg_color=T.ACCENT if is_scrape else "transparent",
            text_color=T.LOG_BG if is_scrape else T.TEXT_DIM,
        )
