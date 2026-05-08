# gui/sidebar.py
import customtkinter as ctk
from gui import theme as T


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_new_scrape, on_history, on_settings, on_badge_click, **kwargs):
        super().__init__(master, fg_color=T.BG_SIDEBAR, width=160,
                         corner_radius=0, **kwargs)
        self.pack_propagate(False)
        self._on_new_scrape = on_new_scrape
        self._on_history = on_history
        self._on_settings = on_settings
        self._on_badge_click = on_badge_click
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

        # Badge vert — masqué par défaut
        self._badge_frame = ctk.CTkFrame(self, fg_color="#14532d", corner_radius=8)
        self._badge_frame.bind("<Button-1>", lambda e: self._on_badge_click())

        self._badge_count_lbl = ctk.CTkLabel(
            self._badge_frame, text="0",
            font=("", 24, "bold"), text_color="#4ade80",
        )
        self._badge_count_lbl.pack(pady=(10, 0))
        self._badge_count_lbl.bind("<Button-1>", lambda e: self._on_badge_click())

        self._badge_label_lbl = ctk.CTkLabel(
            self._badge_frame, text="Tâche(s) en attente",
            font=T.FONT_SMALL, text_color="#86efac",
        )
        self._badge_label_lbl.pack()
        self._badge_label_lbl.bind("<Button-1>", lambda e: self._on_badge_click())

        self._badge_sep = ctk.CTkFrame(
            self._badge_frame, height=1, fg_color="#14532d", corner_radius=0,
        )
        self._badge_sep.pack(fill="x", padx=8, pady=(6, 0))

        self._badge_see_lbl = ctk.CTkLabel(
            self._badge_frame, text="▼ Voir la liste",
            font=T.FONT_SMALL, text_color="#14532d",
        )
        self._badge_see_lbl.pack(pady=(4, 10))
        self._badge_see_lbl.bind("<Button-1>", lambda e: self._on_badge_click())

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

    def update_badge(self, count: int, show_see_list: bool = False) -> None:
        if count == 0:
            self._badge_frame.pack_forget()
            return
        self._badge_count_lbl.configure(text=str(count))
        if show_see_list:
            self._badge_frame.configure(border_width=1, border_color="#16a34a")
            self._badge_sep.configure(fg_color="#166534")
            self._badge_see_lbl.configure(text_color="#4ade80")
        else:
            self._badge_frame.configure(border_width=2, border_color="#4ade80")
            self._badge_sep.configure(fg_color="#14532d")
            self._badge_see_lbl.configure(text_color="#14532d")
        if not self._badge_frame.winfo_ismapped():
            self._badge_frame.pack(fill="x", padx=8, pady=(0, 8), side="bottom")
