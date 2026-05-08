import customtkinter as ctk
from tkinter import filedialog
from gui import theme as T

MODES = [
    (1,  "📄", "Texte propre",        "Contenu lisible sans le code — format .txt"),
    (2,  "📝", "HTML brut",           "Code source complet de la page — format .html"),
    (3,  "🌐", "HTML complet",        "Page + assets CSS/images — ouvrable sans internet"),
    (4,  "🗂️", "Données structurées", "Titre, sections, paragraphes, images — format .json"),
    (5,  "🖼️", "Images",              "Toutes les photos et illustrations (jpg, png, webp...)"),
    (6,  "🗺️", "Arborescence URLs",   "Liste tous les liens de la page avec hiérarchie (.txt)"),
    (7,  "🎬", "Vidéos",              "Fichiers vidéo présents sur la page (mp4, webm, mov...)"),
    (8,  "🎵", "Audios",              "Fichiers audio (mp3, wav, flac, aac...)"),
    (9,  "📁", "Documents",           "PDF, Word, Excel, PowerPoint liés sur la page"),
    (10, "📦", "Archives",            "Fichiers zip, rar, 7z en téléchargement"),
    (11, "📷", "Screenshot",          "Capture d'écran pleine page (.png) via Playwright"),
]

DEPTH_LABELS = [
    ("0",  "Cette page seulement (recommandé)", 0),
    ("+1", "Page + ses liens directs", 1),
    ("+2", "Liens des liens", 2),
    ("+3", "3 niveaux — peut être long", 3),
    ("+4", "4 niveaux — attention : beaucoup de pages", 4),
    ("+5", "5 niveaux — réserver aux petits sites filtrés", 5),
]

# Extensions par mode
EXT_FILTERS = {
    5:  [("JPG/JPEG", {"jpg", "jpeg"}), ("PNG", {"png"}), ("GIF", {"gif"}),
          ("SVG", {"svg"}), ("WEBP", {"webp"}), ("BMP", {"bmp"}),
          ("ICO", {"ico"}), ("AVIF", {"avif"})],
    7:  [("MP4", {"mp4"}), ("WEBM", {"webm"}), ("MOV", {"mov"}), ("AVI", {"avi"}),
          ("MKV", {"mkv"}), ("M4V", {"m4v"}), ("FLV", {"flv"}), ("OGG", {"ogg"})],
    8:  [("MP3", {"mp3"}), ("WAV", {"wav"}), ("FLAC", {"flac"}), ("AAC", {"aac"}),
          ("M4A", {"m4a"}), ("WMA", {"wma"}), ("OPUS", {"opus"}), ("AIFF", {"aiff"})],
    9:  [("PDF", {"pdf"}), ("DOC/DOCX", {"doc", "docx"}), ("XLS/XLSX", {"xls", "xlsx"}),
          ("PPT/PPTX", {"ppt", "pptx"}), ("ODT/ODS/ODP", {"odt", "ods", "odp"}),
          ("EPUB", {"epub"}), ("MOBI", {"mobi"})],
    10: [("ZIP", {"zip"}), ("RAR", {"rar"}), ("7Z", {"7z"}),
          ("TAR/GZ/TGZ", {"tar", "gz", "tgz"}), ("BZ2/XZ/TBZ2", {"bz2", "xz", "tbz2"})],
}

MODE_EXT_ATTR = {5: "_img_ext_filter", 7: "_vid_ext_filter", 8: "_aud_ext_filter",
                 9: "_doc_ext_filter", 10: "_arc_ext_filter"}


class Wizard(ctk.CTkFrame):
    """Wizard 4 étapes : URL → Contenu → Options → Lancer."""

    def __init__(self, master, on_launch, on_enqueue=None, last_url: str = "", **kwargs):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0, **kwargs)
        self._on_launch = on_launch
        self._on_enqueue = on_enqueue
        self._enqueue_mode = False
        self._step = 0
        self._url = last_url
        self._modes: set[int] = set()
        self._depth = 0
        self._cookies_path = ""
        self._respect_robots = False
        self._url_filter = ""
        self._use_playwright: bool = False
        self._playwright_opts: dict = {}
        self._img_ext_filter: set | None = None
        self._vid_ext_filter: set | None = None
        self._aud_ext_filter: set | None = None
        self._doc_ext_filter: set | None = None
        self._arc_ext_filter: set | None = None
        self._ext_vars: dict[int, list[tuple]] = {}  # mode_id -> [(label, exts_set, BoolVar)]
        self._frames: list[ctk.CTkFrame] = []
        self._build_steps_bar()
        self._build_step0()
        self._build_step1()
        self._build_step2()
        self._build_step3()
        self._show_step(0)

    # ── Barre d'étapes ────────────────────────────────────────────────────────

    def _build_steps_bar(self):
        bar = ctk.CTkFrame(self, fg_color=T.BG_SURFACE, corner_radius=0, height=48)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        self._step_labels: list[ctk.CTkLabel] = []
        steps = ["1 URL", "2 Contenu", "3 Options", "4 Lancer"]
        for i, label in enumerate(steps):
            lbl = ctk.CTkLabel(bar, text=label, font=T.FONT_SMALL,
                               text_color=T.TEXT_DIM, width=160)
            lbl.pack(side="left", padx=4, pady=14)
            self._step_labels.append(lbl)

    def _update_steps_bar(self):
        for i, lbl in enumerate(self._step_labels):
            if i < self._step:
                lbl.configure(text_color=T.SUCCESS)
            elif i == self._step:
                lbl.configure(text_color=T.ACCENT)
            else:
                lbl.configure(text_color=T.TEXT_DIM)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _show_step(self, step: int):
        for f in self._frames:
            f.pack_forget()
        self._frames[step].pack(fill="both", expand=True, padx=24, pady=16)
        self._step = step
        self._update_steps_bar()

    def _next(self):
        if self._step == 0:
            url = self._url_entry.get().strip()
            if not url.startswith(("http://", "https://")):
                self._url_error.configure(text="⚠ L'URL doit commencer par http:// ou https://")
                return
            self._url = url
            self._url_error.configure(text="")
        elif self._step == 1:
            if not self._modes:
                self._mode_error.configure(text="⚠ Sélectionnez au moins un type de contenu")
                return
            self._mode_error.configure(text="")
            self._refresh_mode_options()
        elif self._step == 2:
            self.show_recap()
        self._show_step(self._step + 1)

    def _prev(self):
        self._show_step(self._step - 1)

    # ── Étape 0 : URL ─────────────────────────────────────────────────────────

    def _build_step0(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self._frames.append(f)

        ctk.CTkLabel(f, text="Quelle page voulez-vous scraper ?",
                     font=T.FONT_TITLE, text_color=T.TEXT).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="Entrez l'adresse complète de la page web.",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM).pack(anchor="w", pady=(0, 12))

        self._url_entry = ctk.CTkEntry(
            f, placeholder_text="https://exemple.com/article",
            fg_color=T.BG_SURFACE, border_color=T.BORDER,
            text_color=T.TEXT, font=T.FONT_NORMAL, height=38,
        )
        if self._url:
            self._url_entry.insert(0, self._url)
        self._url_entry.pack(fill="x", pady=(0, 6))

        self._url_error = ctk.CTkLabel(f, text="", font=T.FONT_SMALL, text_color=T.ERROR)
        self._url_error.pack(anchor="w")

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom", pady=(16, 0))
        ctk.CTkButton(btn_row, text="Suivant →", font=T.FONT_BOLD,
                      fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                      text_color=T.LOG_BG, height=36,
                      command=self._next).pack(side="right")

    # ── Étape 1 : Contenu ─────────────────────────────────────────────────────

    def _build_step1(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self._frames.append(f)

        ctk.CTkLabel(f, text="Que voulez-vous récupérer ?",
                     font=T.FONT_TITLE, text_color=T.TEXT).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="Vous pouvez choisir plusieurs types.",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM).pack(anchor="w", pady=(0, 10))

        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.pack(fill="x")
        self._mode_vars: dict[int, ctk.BooleanVar] = {}
        for idx, (mode_id, icon, name, desc) in enumerate(MODES):
            var = ctk.BooleanVar()
            self._mode_vars[mode_id] = var
            row, col = divmod(idx, 2)
            card = ctk.CTkFrame(grid, fg_color=T.BG_SURFACE, border_color=T.BORDER,
                                border_width=1, corner_radius=6)
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            grid.columnconfigure(col, weight=1)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=8, pady=(8, 2))
            ctk.CTkLabel(top, text=f"{icon} {name}", font=T.FONT_BOLD,
                         text_color=T.TEXT).pack(side="left")
            ctk.CTkCheckBox(top, text="", variable=var, width=20,
                            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                            border_color=T.BORDER,
                            command=lambda mid=mode_id, v=var: self._toggle_mode(mid, v)
                            ).pack(side="right")
            ctk.CTkLabel(card, text=desc, font=T.FONT_SMALL,
                         text_color=T.TEXT_DIM, wraplength=200, justify="left",
                         anchor="w").pack(anchor="w", padx=8, pady=(0, 8))

        self._mode_error = ctk.CTkLabel(f, text="", font=T.FONT_SMALL, text_color=T.ERROR)
        self._mode_error.pack(anchor="w", pady=(6, 0))

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom", pady=(12, 0))
        ctk.CTkButton(btn_row, text="← Retour", font=T.FONT_NORMAL,
                      fg_color=T.BG_SURFACE, hover_color=T.BORDER,
                      text_color=T.TEXT_DIM, height=34,
                      command=self._prev).pack(side="left")
        ctk.CTkButton(btn_row, text="Suivant →", font=T.FONT_BOLD,
                      fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                      text_color=T.LOG_BG, height=34,
                      command=self._next).pack(side="right")

    def _toggle_mode(self, mode_id: int, var: ctk.BooleanVar):
        if var.get():
            self._modes.add(mode_id)
        else:
            self._modes.discard(mode_id)

    # ── Étape 2 : Options ─────────────────────────────────────────────────────

    def _build_step2(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self._frames.append(f)

        # Navigation buttons — outside the scrollable area
        nav = ctk.CTkFrame(f, fg_color="transparent")
        nav.pack(fill="x", side="bottom", pady=(12, 0))
        ctk.CTkButton(nav, text="← Retour", font=T.FONT_NORMAL,
                      fg_color=T.BG_SURFACE, hover_color=T.BORDER,
                      text_color=T.TEXT_DIM, height=34,
                      command=self._prev).pack(side="left")
        ctk.CTkButton(nav, text="Suivant →", font=T.FONT_BOLD,
                      fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                      text_color=T.LOG_BG, height=34,
                      command=self._next).pack(side="right")

        # Scrollable container for all 3 sections
        self._step2_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent")
        self._step2_scroll.pack(fill="both", expand=True)
        sc = self._step2_scroll

        # ── Section 1 : Moteur de rendu ───────────────────────────────────────
        ctk.CTkLabel(sc, text="Moteur de rendu",
                     font=T.FONT_TITLE, text_color=T.TEXT).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(sc, text="Requests est rapide. Playwright exécute le JavaScript.",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM).pack(anchor="w", pady=(0, 8))

        engine_row = ctk.CTkFrame(sc, fg_color="transparent")
        engine_row.pack(fill="x", pady=(0, 4))

        self._btn_requests = ctk.CTkButton(
            engine_row, text="⚡ Requests", font=T.FONT_BOLD, width=140, height=40,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            text_color=T.LOG_BG, corner_radius=6,
            command=self._select_requests,
        )
        self._btn_requests.pack(side="left", padx=(0, 6))

        self._btn_playwright = ctk.CTkButton(
            engine_row, text="🎭 Playwright", font=T.FONT_BOLD, width=140, height=40,
            fg_color=T.BG_SURFACE, hover_color=T.BORDER,
            text_color=T.TEXT_DIM, corner_radius=6,
            command=self._select_playwright,
        )
        self._btn_playwright.pack(side="left")

        # Playwright sub-panel (hidden by default)
        self._playwright_frame = ctk.CTkFrame(sc, fg_color=T.BG_SURFACE, corner_radius=6)

        # CSS selector
        ctk.CTkLabel(self._playwright_frame,
                     text="Sélecteur CSS à attendre (optionnel)",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM).pack(anchor="w", padx=10, pady=(8, 2))
        self._pw_css_entry = ctk.CTkEntry(
            self._playwright_frame, placeholder_text="#content",
            fg_color=T.BG_MAIN, border_color=T.BORDER,
            text_color=T.TEXT, font=T.FONT_SMALL, height=30,
        )
        self._pw_css_entry.pack(fill="x", padx=10, pady=(0, 8))

        # Delay buttons
        ctk.CTkLabel(self._playwright_frame, text="Délai d'attente",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM).pack(anchor="w", padx=10, pady=(0, 2))
        delay_row = ctk.CTkFrame(self._playwright_frame, fg_color="transparent")
        delay_row.pack(fill="x", padx=10, pady=(0, 4))
        self._delay_btns: list[ctk.CTkButton] = []
        self._delay_custom_entry: ctk.CTkEntry | None = None
        self._delay_val = 2
        for i, (label, val) in enumerate([("2s (rapide)", 2), ("5s", 5), ("Autre…", None)]):
            btn = ctk.CTkButton(
                delay_row, text=label, font=T.FONT_NORMAL, width=90, height=32,
                fg_color=T.ACCENT if i == 0 else T.BG_MAIN,
                hover_color=T.ACCENT_HOVER if i == 0 else T.BORDER,
                text_color=T.LOG_BG if i == 0 else T.TEXT_DIM,
                corner_radius=6,
                command=lambda v=val, lbl=label, idx=i: self._select_delay(v, lbl, idx),
            )
            btn.pack(side="left", padx=2)
            self._delay_btns.append(btn)
        self._delay_custom_frame = ctk.CTkFrame(self._playwright_frame, fg_color="transparent")
        self._delay_custom_entry = ctk.CTkEntry(
            self._delay_custom_frame, placeholder_text="délai en secondes",
            fg_color=T.BG_MAIN, border_color=T.BORDER,
            text_color=T.TEXT, font=T.FONT_SMALL, height=30, width=160,
        )
        self._delay_custom_entry.pack(side="left", padx=(0, 4))

        # Viewport buttons
        ctk.CTkLabel(self._playwright_frame, text="Viewport",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM).pack(anchor="w", padx=10, pady=(4, 2))
        viewport_row = ctk.CTkFrame(self._playwright_frame, fg_color="transparent")
        viewport_row.pack(fill="x", padx=10, pady=(0, 4))
        self._viewport_btns: list[ctk.CTkButton] = []
        self._viewport_val = "1280x720"
        for i, (label, val) in enumerate([("1280×720", "1280x720"), ("1920×1080", "1920x1080"),
                                           ("Mobile", "390x844"), ("Autre…", None)]):
            btn = ctk.CTkButton(
                viewport_row, text=label, font=T.FONT_NORMAL, width=90, height=32,
                fg_color=T.ACCENT if i == 0 else T.BG_MAIN,
                hover_color=T.ACCENT_HOVER if i == 0 else T.BORDER,
                text_color=T.LOG_BG if i == 0 else T.TEXT_DIM,
                corner_radius=6,
                command=lambda v=val, lbl=label, idx=i: self._select_viewport(v, lbl, idx),
            )
            btn.pack(side="left", padx=2)
            self._viewport_btns.append(btn)
        self._viewport_custom_frame = ctk.CTkFrame(self._playwright_frame, fg_color="transparent")
        self._viewport_custom_entry = ctk.CTkEntry(
            self._viewport_custom_frame, placeholder_text="LxH  ex: 1024x768",
            fg_color=T.BG_MAIN, border_color=T.BORDER,
            text_color=T.TEXT, font=T.FONT_SMALL, height=30, width=160,
        )
        self._viewport_custom_entry.pack(side="left", padx=(0, 4))

        ctk.CTkFrame(self._playwright_frame, fg_color="transparent", height=6).pack()

        # ── Section 2 : Options par mode ──────────────────────────────────────
        self._mode_opts_header = ctk.CTkLabel(sc, text="Options par contenu",
                                               font=T.FONT_TITLE, text_color=T.TEXT)
        self._mode_opts_container = ctk.CTkFrame(sc, fg_color="transparent")

        # ── Section 3 : Profondeur ────────────────────────────────────────────
        ctk.CTkFrame(sc, fg_color=T.BORDER, height=1).pack(fill="x", pady=(10, 6))
        ctk.CTkLabel(sc, text="Combien de pages suivre ?",
                     font=T.FONT_TITLE, text_color=T.TEXT).pack(anchor="w", pady=(0, 4))

        self._depth_desc = ctk.CTkLabel(sc, text=DEPTH_LABELS[0][1],
                                         font=T.FONT_SMALL, text_color=T.TEXT_DIM)
        self._depth_desc.pack(anchor="w", pady=(0, 10))

        depth_row = ctk.CTkFrame(sc, fg_color="transparent")
        depth_row.pack(fill="x")
        self._depth_btns: list[ctk.CTkButton] = []
        for i, (label, desc, val) in enumerate(DEPTH_LABELS):
            btn = ctk.CTkButton(
                depth_row, text=label, font=T.FONT_BOLD, width=72, height=56,
                fg_color=T.ACCENT if i == 0 else T.BG_SURFACE,
                hover_color=T.ACCENT_HOVER if i == 0 else T.BORDER,
                text_color=T.LOG_BG if i == 0 else T.TEXT_DIM,
                corner_radius=6,
                command=lambda v=val, d=desc, idx=i: self._select_depth(v, d, idx),
            )
            btn.pack(side="left", padx=3)
            self._depth_btns.append(btn)
        # "Autre…" button
        btn_other = ctk.CTkButton(
            depth_row, text="Autre…", font=T.FONT_BOLD, width=72, height=56,
            fg_color=T.BG_SURFACE, hover_color=T.BORDER,
            text_color=T.TEXT_DIM, corner_radius=6,
            command=self._select_depth_other,
        )
        btn_other.pack(side="left", padx=3)
        self._depth_btns.append(btn_other)

        self._depth_custom_frame = ctk.CTkFrame(sc, fg_color="transparent")
        self._depth_custom_entry = ctk.CTkEntry(
            self._depth_custom_frame, placeholder_text="0–999",
            fg_color=T.BG_SURFACE, border_color=T.BORDER,
            text_color=T.TEXT, font=T.FONT_SMALL, height=32, width=120,
        )
        self._depth_custom_entry.pack(side="left", padx=(0, 4))

    def _select_requests(self):
        self._use_playwright = False
        self._btn_requests.configure(fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                                      text_color=T.LOG_BG)
        self._btn_playwright.configure(fg_color=T.BG_SURFACE, hover_color=T.BORDER,
                                        text_color=T.TEXT_DIM)
        self._playwright_frame.pack_forget()

    def _select_playwright(self):
        self._use_playwright = True
        self._btn_playwright.configure(fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                                        text_color=T.LOG_BG)
        self._btn_requests.configure(fg_color=T.BG_SURFACE, hover_color=T.BORDER,
                                      text_color=T.TEXT_DIM)
        # Insert after engine_row — pack in scrollable frame
        self._playwright_frame.pack(fill="x", pady=(6, 4))

    def _select_delay(self, val, label: str, idx: int):
        for i, btn in enumerate(self._delay_btns):
            active = (i == idx)
            btn.configure(fg_color=T.ACCENT if active else T.BG_MAIN,
                           hover_color=T.ACCENT_HOVER if active else T.BORDER,
                           text_color=T.LOG_BG if active else T.TEXT_DIM)
        if val is None:
            self._delay_custom_frame.pack(fill="x", padx=10, pady=(0, 6))
        else:
            self._delay_val = val
            self._delay_custom_frame.pack_forget()

    def _select_viewport(self, val, label: str, idx: int):
        for i, btn in enumerate(self._viewport_btns):
            active = (i == idx)
            btn.configure(fg_color=T.ACCENT if active else T.BG_MAIN,
                           hover_color=T.ACCENT_HOVER if active else T.BORDER,
                           text_color=T.LOG_BG if active else T.TEXT_DIM)
        if val is None:
            self._viewport_custom_frame.pack(fill="x", padx=10, pady=(0, 6))
        else:
            self._viewport_val = val
            self._viewport_custom_frame.pack_forget()

    def _collect_playwright_opts(self):
        """Collect playwright options from UI into self._playwright_opts."""
        if not self._use_playwright:
            self._playwright_opts = {}
            return
        opts = {}
        css = self._pw_css_entry.get().strip()
        if css:
            opts["wait_selector"] = css
        # Delay
        delay_custom_visible = self._delay_custom_frame.winfo_manager() != ""
        if delay_custom_visible:
            try:
                opts["delay"] = int(self._delay_custom_entry.get().strip())
            except (ValueError, AttributeError):
                opts["delay"] = 2
        else:
            opts["delay"] = self._delay_val
        # Viewport
        vp_custom_visible = self._viewport_custom_frame.winfo_manager() != ""
        if vp_custom_visible:
            raw = self._viewport_custom_entry.get().strip()
            opts["viewport"] = raw if raw else "1280x720"
        else:
            opts["viewport"] = self._viewport_val
        self._playwright_opts = opts

    def _refresh_mode_options(self):
        """Rebuild the mode-specific extension checkboxes based on current self._modes."""
        # Destroy previous widgets
        for widget in self._mode_opts_container.winfo_children():
            widget.destroy()
        self._ext_vars = {}

        modes_with_filters = [m for m in sorted(self._modes) if m in EXT_FILTERS]

        if modes_with_filters:
            self._mode_opts_header.pack(anchor="w", pady=(10, 4),
                                         before=self._mode_opts_container)
            self._mode_opts_container.pack(fill="x", before=self._depth_desc)
        else:
            self._mode_opts_header.pack_forget()
            self._mode_opts_container.pack_forget()

        for mode_id in modes_with_filters:
            mode_name = next((name for mid, _, name, _ in MODES if mid == mode_id), str(mode_id))
            section = ctk.CTkFrame(self._mode_opts_container, fg_color=T.BG_SURFACE,
                                    corner_radius=6)
            section.pack(fill="x", pady=(0, 6))
            ctk.CTkLabel(section, text=mode_name, font=T.FONT_BOLD,
                          text_color=T.TEXT).pack(anchor="w", padx=10, pady=(6, 4))

            row_frame = ctk.CTkFrame(section, fg_color="transparent")
            row_frame.pack(fill="x", padx=10, pady=(0, 8))

            ext_entries = []
            for col_idx, (ext_label, exts) in enumerate(EXT_FILTERS[mode_id]):
                var = ctk.BooleanVar(value=True)
                cb = ctk.CTkCheckBox(row_frame, text=ext_label, variable=var,
                                      fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                                      border_color=T.BORDER, font=T.FONT_SMALL,
                                      text_color=T.TEXT)
                cb.grid(row=col_idx // 4, column=col_idx % 4, padx=4, pady=2, sticky="w")
                row_frame.columnconfigure(col_idx % 4, weight=1)
                ext_entries.append((ext_label, exts, var))
            self._ext_vars[mode_id] = ext_entries

    def _collect_ext_filters(self):
        """Read checkbox states and store into _xxx_ext_filter attributes."""
        attr_map = MODE_EXT_ATTR
        for mode_id, attr in attr_map.items():
            if mode_id not in self._ext_vars or mode_id not in self._modes:
                setattr(self, attr, None)
                continue
            entries = self._ext_vars[mode_id]
            all_checked = all(var.get() for _, _, var in entries)
            if all_checked:
                setattr(self, attr, None)
            else:
                selected: set[str] = set()
                for _, exts, var in entries:
                    if var.get():
                        selected.update(exts)
                setattr(self, attr, selected if selected else None)

    def _select_depth(self, val: int, desc: str, idx: int):
        self._depth = val
        self._depth_desc.configure(text=desc)
        self._depth_custom_frame.pack_forget()
        for i, btn in enumerate(self._depth_btns):
            active = (i == idx)
            btn.configure(
                fg_color=T.ACCENT if active else T.BG_SURFACE,
                hover_color=T.ACCENT_HOVER if active else T.BORDER,
                text_color=T.LOG_BG if active else T.TEXT_DIM,
            )

    def _select_depth_other(self):
        """Show custom depth entry and mark last button active."""
        idx = len(self._depth_btns) - 1
        for i, btn in enumerate(self._depth_btns):
            active = (i == idx)
            btn.configure(
                fg_color=T.ACCENT if active else T.BG_SURFACE,
                hover_color=T.ACCENT_HOVER if active else T.BORDER,
                text_color=T.LOG_BG if active else T.TEXT_DIM,
            )
        self._depth_desc.configure(text="Profondeur personnalisée")
        self._depth_custom_frame.pack(fill="x", pady=(4, 0))

    # ── Étape 3 : Récapitulatif + Lancer ──────────────────────────────────────

    def _build_step3(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self._frames.append(f)

        ctk.CTkLabel(f, text="Prêt à lancer ?",
                     font=T.FONT_TITLE, text_color=T.TEXT).pack(anchor="w", pady=(0, 10))

        recap = ctk.CTkFrame(f, fg_color=T.BG_SURFACE, corner_radius=6)
        recap.pack(fill="x", pady=(0, 10))
        self._recap_url = ctk.CTkLabel(recap, text="", font=T.FONT_SMALL,
                                        text_color=T.TEXT, anchor="w", padx=12, pady=6)
        self._recap_url.pack(fill="x")
        self._recap_modes = ctk.CTkLabel(recap, text="", font=T.FONT_SMALL,
                                          text_color=T.TEXT_DIM, anchor="w", padx=12, pady=4)
        self._recap_modes.pack(fill="x")
        self._recap_depth = ctk.CTkLabel(recap, text="", font=T.FONT_SMALL,
                                          text_color=T.TEXT_DIM, anchor="w", padx=12, pady=6)
        self._recap_depth.pack(fill="x")

        self._adv_visible = False
        self._adv_btn = ctk.CTkButton(
            f, text="▸ Options avancées (optionnel)",
            font=T.FONT_SMALL, fg_color="transparent",
            hover_color=T.BG_SURFACE, text_color=T.TEXT_DIM,
            anchor="w", height=28, corner_radius=4,
            command=self._toggle_advanced,
        )
        self._adv_btn.pack(fill="x", pady=(0, 4))

        self._adv_frame = ctk.CTkFrame(f, fg_color=T.BG_SURFACE, corner_radius=6)

        # Cookies
        ctk.CTkLabel(self._adv_frame,
                     text="Cookies — pour les sites nécessitant une connexion.",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM,
                     justify="left", anchor="w", wraplength=500,
                     ).pack(anchor="w", padx=12, pady=(8, 2))
        cookies_row = ctk.CTkFrame(self._adv_frame, fg_color="transparent")
        cookies_row.pack(fill="x", padx=12, pady=(0, 8))
        self._cookies_entry = ctk.CTkEntry(
            cookies_row, placeholder_text="(aucun — optionnel)",
            fg_color=T.BG_MAIN, border_color=T.BORDER,
            text_color=T.TEXT, font=T.FONT_SMALL, height=32,
        )
        self._cookies_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(cookies_row, text="Parcourir…", width=90,
                      fg_color=T.BG_SURFACE, hover_color=T.BORDER,
                      text_color=T.TEXT, font=T.FONT_SMALL, height=32,
                      command=self._browse_cookies).pack(side="right")

        # Robots.txt
        robots_row = ctk.CTkFrame(self._adv_frame, fg_color="transparent")
        robots_row.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(robots_row, text="Respecter robots.txt",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM).pack(side="left")
        self._robots_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(robots_row, text="", variable=self._robots_var, width=40,
                      fg_color=T.BORDER, progress_color=T.ACCENT,
                      command=lambda: setattr(self, '_respect_robots', self._robots_var.get()),
                      ).pack(side="right")

        # Filtre URL
        ctk.CTkLabel(self._adv_frame,
                     text="Filtre URL (crawl) — ne suivre que les liens contenant ce mot-clé.",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM,
                     justify="left", anchor="w", wraplength=500,
                     ).pack(anchor="w", padx=12, pady=(0, 2))
        self._url_filter_entry = ctk.CTkEntry(
            self._adv_frame, placeholder_text="ex: /articles/  (vide = tous les liens)",
            fg_color=T.BG_MAIN, border_color=T.BORDER,
            text_color=T.TEXT, font=T.FONT_SMALL, height=32,
        )
        self._url_filter_entry.pack(fill="x", padx=12, pady=(0, 10))

        self._nav_step3 = ctk.CTkFrame(f, fg_color="transparent")
        self._nav_step3.pack(fill="x", side="bottom", pady=(12, 0))
        ctk.CTkButton(self._nav_step3, text="← Retour", font=T.FONT_NORMAL,
                      fg_color=T.BG_SURFACE, hover_color=T.BORDER,
                      text_color=T.TEXT_DIM, height=36,
                      command=self._prev).pack(side="left")
        self._btn_launch = ctk.CTkButton(
            self._nav_step3, text="▶ Lancer le scraping", font=T.FONT_BOLD,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            text_color=T.LOG_BG, height=36,
            command=self._launch,
        )
        self._btn_launch.pack(side="right")

    def _toggle_advanced(self):
        self._adv_visible = not self._adv_visible
        self._adv_btn.configure(
            text=("▾ Options avancées (optionnel)" if self._adv_visible
                  else "▸ Options avancées (optionnel)")
        )
        if self._adv_visible:
            self._adv_frame.pack(fill="x", pady=(0, 8), before=self._nav_step3)
        else:
            self._adv_frame.pack_forget()

    def _browse_cookies(self):
        path = filedialog.askopenfilename(
            title="Sélectionner cookies.txt",
            filetypes=[("Cookies Netscape", "*.txt"), ("Tous", "*.*")],
        )
        if path:
            self._cookies_entry.delete(0, "end")
            self._cookies_entry.insert(0, path)

    def _launch(self):
        self._cookies_path = self._cookies_entry.get().strip()
        self._url_filter = self._url_filter_entry.get().strip()
        self._respect_robots = self._robots_var.get()
        # Collect custom depth if "Autre…" was selected
        if self._depth_custom_frame.winfo_manager() != "":
            try:
                self._depth = max(0, min(999, int(self._depth_custom_entry.get().strip())))
            except (ValueError, AttributeError):
                pass
        self._collect_playwright_opts()
        self._collect_ext_filters()
        params = dict(
            url=self._url,
            modes=sorted(self._modes),
            depth=self._depth,
            cookies_path=self._cookies_path or None,
            respect_robots=self._respect_robots,
            url_filter=self._url_filter,
            use_playwright=self._use_playwright,
            playwright_opts=self._playwright_opts,
            img_ext_filter=self._img_ext_filter,
            vid_ext_filter=self._vid_ext_filter,
            aud_ext_filter=self._aud_ext_filter,
            doc_ext_filter=self._doc_ext_filter,
            arc_ext_filter=self._arc_ext_filter,
        )
        if self._enqueue_mode and self._on_enqueue:
            self._on_enqueue(**params)
        else:
            self._on_launch(**params)

    def show_recap(self):
        """Mettre à jour le récapitulatif avant affichage de l'étape 3."""
        self._recap_url.configure(text=f"🔗 {self._url}")
        mode_names = [name for mid, _, name, _ in MODES if mid in self._modes]
        self._recap_modes.configure(text="Types : " + ", ".join(mode_names))
        # Depth label — find by value
        depth_label = next(
            (desc for _, desc, val in DEPTH_LABELS if val == self._depth),
            f"Profondeur {self._depth}",
        )
        engine = "🎭 Playwright" if self._use_playwright else "⚡ Requests"
        # Count active extension filters (non-None)
        active_filters = sum(
            1 for attr in ("_img_ext_filter", "_vid_ext_filter", "_aud_ext_filter",
                           "_doc_ext_filter", "_arc_ext_filter")
            if getattr(self, attr) is not None
        )
        filter_info = f" — {active_filters} filtre(s) actif(s)" if active_filters else ""
        self._recap_depth.configure(
            text=f"Profondeur : {depth_label} | Moteur : {engine}{filter_info}"
        )

    def reset(self, last_url: str = ""):
        """Réinitialiser le wizard pour un nouveau scrape."""
        self._url = last_url
        self._modes = set()
        self._depth = 0
        self._cookies_path = ""
        self._use_playwright = False
        self._playwright_opts = {}
        self._img_ext_filter = None
        self._vid_ext_filter = None
        self._aud_ext_filter = None
        self._doc_ext_filter = None
        self._arc_ext_filter = None
        self._ext_vars = {}
        self._url_entry.delete(0, "end")
        self._url_error.configure(text="")
        if last_url:
            self._url_entry.insert(0, last_url)
        self._mode_error.configure(text="")
        for var in self._mode_vars.values():
            var.set(False)
        self._select_depth(0, DEPTH_LABELS[0][1], 0)
        # Reset engine buttons
        self._btn_requests.configure(fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                                      text_color=T.LOG_BG)
        self._btn_playwright.configure(fg_color=T.BG_SURFACE, hover_color=T.BORDER,
                                        text_color=T.TEXT_DIM)
        self._playwright_frame.pack_forget()
        # Reset delay/viewport to defaults
        self._delay_val = 2
        self._viewport_val = "1280x720"
        for i, btn in enumerate(self._delay_btns):
            btn.configure(fg_color=T.ACCENT if i == 0 else T.BG_MAIN,
                           hover_color=T.ACCENT_HOVER if i == 0 else T.BORDER,
                           text_color=T.LOG_BG if i == 0 else T.TEXT_DIM)
        for i, btn in enumerate(self._viewport_btns):
            btn.configure(fg_color=T.ACCENT if i == 0 else T.BG_MAIN,
                           hover_color=T.ACCENT_HOVER if i == 0 else T.BORDER,
                           text_color=T.LOG_BG if i == 0 else T.TEXT_DIM)
        self._delay_custom_frame.pack_forget()
        self._viewport_custom_frame.pack_forget()
        self._depth_custom_frame.pack_forget()
        # Reset mode options container
        for widget in self._mode_opts_container.winfo_children():
            widget.destroy()
        self._mode_opts_header.pack_forget()
        self._mode_opts_container.pack_forget()
        self._cookies_entry.delete(0, "end")
        self._robots_var.set(False)
        self._respect_robots = False
        self._url_filter_entry.delete(0, "end")
        self._url_filter = ""
        if self._adv_visible:
            self._adv_visible = False
            self._adv_btn.configure(text="▸ Options avancées (optionnel)")
            self._adv_frame.pack_forget()
        self._enqueue_mode = False
        self._btn_launch.configure(text="▶ Lancer le scraping")
        self._show_step(0)

    def prefill(self, url: str, modes: list, depth: int) -> None:
        """Pré-remplir le wizard après reset() avec les paramètres d'une entrée historique."""
        self._url = url
        self._url_entry.delete(0, "end")
        self._url_entry.insert(0, url)
        self._modes = set()
        for var in self._mode_vars.values():
            var.set(False)
        for mode_id in modes:
            if mode_id in self._mode_vars:
                self._mode_vars[mode_id].set(True)
                self._modes.add(mode_id)
        # Find matching DEPTH_LABELS entry by value
        match = next(((i, lbl) for i, (_, lbl, val) in enumerate(DEPTH_LABELS) if val == depth), None)
        if match:
            idx, desc = match
            self._select_depth(depth, desc, idx)
        else:
            # Depth not in presets → use "Autre…" button (last index)
            self._select_depth_other()
            self._depth_custom_entry.delete(0, "end")
            self._depth_custom_entry.insert(0, str(depth))
            self._depth = depth

    def set_enqueue_mode(self, active: bool) -> None:
        self._enqueue_mode = active
        text = "➕ Ajouter aux tâches en attente" if active else "▶ Lancer le scraping"
        self._btn_launch.configure(text=text)
