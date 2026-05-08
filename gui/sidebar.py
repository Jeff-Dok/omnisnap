# gui/sidebar.py
from pathlib import Path
from urllib.parse import urlparse

import customtkinter as ctk
from gui import theme as T

# Chemin vers l'asset logo
_ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
_ICON_ICO = _ASSET_DIR / "omnisnap.ico"
_ICON_PNG = _ASSET_DIR / "icon.png"

_STATUS_ICON = {
    "done": "✅",
    "error": "✗",
    "cancelled": "⏹",
}


def _get_logo_image(size: int = 28):
    """Tente de charger le logo via CTkImage. Retourne None si échec."""
    try:
        from PIL import Image
        path = None
        if _ICON_ICO.exists():
            path = _ICON_ICO
        elif _ICON_PNG.exists():
            path = _ICON_PNG
        if path is None:
            return None
        img = Image.open(path)
        # Pour .ico, prendre la taille la plus proche ou la première frame
        if hasattr(img, "seek"):
            try:
                img.seek(0)
            except EOFError:
                pass
        img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        return None


def _domain_short(url: str, max_len: int = 20) -> str:
    """Extrait le domaine d'une URL et le tronque."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Supprimer le www.
        if domain.startswith("www."):
            domain = domain[4:]
        if len(domain) > max_len:
            domain = domain[:max_len - 1] + "…"
        return domain
    except Exception:
        return url[:max_len]


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_new_scrape, on_history, on_settings,
                 on_badge_click, on_recent_click=None, **kwargs):
        super().__init__(master, fg_color=T.BG_SIDEBAR, width=160,
                         corner_radius=0, **kwargs)
        self.pack_propagate(False)
        self._on_new_scrape = on_new_scrape
        self._on_history = on_history
        self._on_settings = on_settings
        self._on_badge_click = on_badge_click
        self._on_recent_click = on_recent_click
        self._recent_widgets: list = []
        self._build()

    def _build(self):
        # ── P1 : Header logo + texte ──────────────────────────────────────
        header_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        header_frame.pack(fill="x", pady=(14, 0), padx=12)

        logo_img = _get_logo_image(28)
        if logo_img is not None:
            ctk.CTkLabel(
                header_frame, image=logo_img, text="",
                width=28, height=28,
            ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            header_frame, text="OmniSnap",
            font=T.FONT_BOLD, text_color=T.ACCENT, anchor="w",
        ).pack(side="left")

        ctk.CTkFrame(self, height=1, fg_color=T.BORDER, corner_radius=0
                     ).pack(fill="x", padx=10, pady=(10, 6))

        # ── Boutons de navigation ─────────────────────────────────────────
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

        # ── P15 : Section "Récent" (masquée par défaut) ───────────────────
        self._recent_section = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        # Ne pas pack ici — géré par update_recent()

        ctk.CTkFrame(self._recent_section, height=1, fg_color=T.BORDER,
                     corner_radius=0).pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(
            self._recent_section, text="Récent",
            font=T.FONT_SMALL, text_color=T.TEXT_DIM, anchor="w", padx=12,
        ).pack(fill="x")

        self._recent_list = ctk.CTkFrame(
            self._recent_section, fg_color="transparent", corner_radius=0
        )
        self._recent_list.pack(fill="x", padx=8)

        # ── P7 & Badge vert — masqué par défaut ──────────────────────────
        self._badge_frame = ctk.CTkFrame(self, fg_color="#14532d", corner_radius=8,
                                         cursor="hand2")
        self._badge_frame.bind("<Button-1>", lambda e: self._on_badge_click())

        self._badge_count_lbl = ctk.CTkLabel(
            self._badge_frame, text="0",
            font=("", 24, "bold"), text_color="#4ade80",
            cursor="hand2",
        )
        self._badge_count_lbl.pack(pady=(10, 0))
        self._badge_count_lbl.bind("<Button-1>", lambda e: self._on_badge_click())

        self._badge_label_lbl = ctk.CTkLabel(
            self._badge_frame, text="Tâche(s) en attente",
            font=T.FONT_SMALL, text_color="#86efac",
            cursor="hand2",
        )
        self._badge_label_lbl.pack()
        self._badge_label_lbl.bind("<Button-1>", lambda e: self._on_badge_click())

        self._badge_sep = ctk.CTkFrame(
            self._badge_frame, height=1, fg_color="#14532d", corner_radius=0,
            cursor="hand2",
        )
        self._badge_sep.pack(fill="x", padx=8, pady=(6, 0))

        self._badge_see_lbl = ctk.CTkLabel(
            self._badge_frame, text="▼ Voir la liste",
            font=T.FONT_SMALL, text_color="#14532d",
            cursor="hand2",
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

    def update_recent(self, entries: list) -> None:
        """Affiche jusqu'à 3 entrées récentes dans la sidebar.

        Args:
            entries: Liste de dicts d'historique (champs url, status, id).
                     Liste vide → masque la section.
        """
        # Nettoyer les anciens widgets
        for w in self._recent_widgets:
            w.destroy()
        self._recent_widgets.clear()

        if not entries:
            self._recent_section.pack_forget()
            return

        # S'assurer que la section est visible (entre les boutons nav et le bas)
        if not self._recent_section.winfo_ismapped():
            self._recent_section.pack(fill="x", pady=(4, 0))

        for entry in entries[:3]:
            entry_id = entry.get("id", "")
            url = entry.get("url", "")
            status = entry.get("status", "")
            domain = _domain_short(url)
            icon = _STATUS_ICON.get(status, "•")
            label_text = f"{icon} {domain}"

            row = ctk.CTkButton(
                self._recent_list,
                text=label_text,
                font=T.FONT_SMALL,
                anchor="w",
                height=28,
                fg_color="transparent",
                hover_color=T.BORDER,
                text_color=T.TEXT_DIM,
                corner_radius=4,
                cursor="hand2",
                command=lambda eid=entry_id: self._fire_recent_click(eid),
            )
            row.pack(fill="x", pady=1)
            self._recent_widgets.append(row)

    def _fire_recent_click(self, entry_id: str) -> None:
        if self._on_recent_click:
            self._on_recent_click(entry_id)
