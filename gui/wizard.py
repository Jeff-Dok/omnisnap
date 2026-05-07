import customtkinter as ctk
from tkinter import filedialog
from gui import theme as T

MODES = [
    (1,  "📄", "Texte propre",   "Contenu lisible sans le code — format .txt"),
    (5,  "🖼️", "Images",         "Toutes les photos et illustrations (jpg, png, webp...)"),
    (7,  "🎬", "Vidéos",         "Fichiers vidéo présents sur la page (mp4, webm, mov...)"),
    (8,  "🎵", "Audios",         "Fichiers audio (mp3, wav, flac, aac...)"),
    (9,  "📁", "Documents",      "PDF, Word, Excel, PowerPoint liés sur la page"),
    (10, "📦", "Archives",       "Fichiers zip, rar, 7z en téléchargement"),
    (11, "📷", "Screenshot",     "Capture d'écran pleine page (.png) via Playwright"),
    (3,  "🌐", "HTML complet",   "Page + assets CSS/images — ouvrable sans internet"),
]

DEPTH_LABELS = [
    ("0",  "Cette page seulement (recommandé)"),
    ("+1", "Page + ses liens directs"),
    ("+2", "Liens des liens"),
    ("+3", "3 niveaux — peut être long"),
]


class Wizard(ctk.CTkFrame):
    """Wizard 4 étapes : URL → Contenu → Options → Lancer."""

    def __init__(self, master, on_launch, last_url: str = "", **kwargs):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0, **kwargs)
        self._on_launch = on_launch
        self._step = 0
        self._url = last_url
        self._modes: set[int] = set()
        self._depth = 0
        self._cookies_path = ""
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

    # ── Étape 2 : Profondeur ──────────────────────────────────────────────────

    def _build_step2(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self._frames.append(f)

        ctk.CTkLabel(f, text="Combien de pages suivre ?",
                     font=T.FONT_TITLE, text_color=T.TEXT).pack(anchor="w", pady=(0, 4))

        self._depth_desc = ctk.CTkLabel(f, text=DEPTH_LABELS[0][1],
                                         font=T.FONT_SMALL, text_color=T.TEXT_DIM)
        self._depth_desc.pack(anchor="w", pady=(0, 14))

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x")
        self._depth_btns: list[ctk.CTkButton] = []
        for i, (label, desc) in enumerate(DEPTH_LABELS):
            btn = ctk.CTkButton(
                btn_row, text=label, font=T.FONT_BOLD, width=90, height=64,
                fg_color=T.ACCENT if i == 0 else T.BG_SURFACE,
                hover_color=T.ACCENT_HOVER if i == 0 else T.BORDER,
                text_color=T.LOG_BG if i == 0 else T.TEXT_DIM,
                corner_radius=6,
                command=lambda idx=i, d=desc: self._select_depth(idx, d),
            )
            btn.pack(side="left", padx=4)
            self._depth_btns.append(btn)

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

    def _select_depth(self, idx: int, desc: str):
        self._depth = idx
        self._depth_desc.configure(text=desc)
        for i, btn in enumerate(self._depth_btns):
            active = (i == idx)
            btn.configure(
                fg_color=T.ACCENT if active else T.BG_SURFACE,
                hover_color=T.ACCENT_HOVER if active else T.BORDER,
                text_color=T.LOG_BG if active else T.TEXT_DIM,
            )

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
                                          text_color=T.TEXT_DIM, anchor="w", padx=12, pady=(4, 8))
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
        ctk.CTkLabel(self._adv_frame,
                     text="Fichier cookies.txt — pour les sites nécessitant une connexion.\n"
                          "Exportez avec l'extension 'Get cookies.txt LOCALLY' (Chrome/Firefox).",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM,
                     justify="left", anchor="w", wraplength=500,
                     ).pack(anchor="w", padx=12, pady=(8, 4))
        cookies_row = ctk.CTkFrame(self._adv_frame, fg_color="transparent")
        cookies_row.pack(fill="x", padx=12, pady=(0, 10))
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

        nav = ctk.CTkFrame(f, fg_color="transparent")
        nav.pack(fill="x", side="bottom", pady=(12, 0))
        ctk.CTkButton(nav, text="← Retour", font=T.FONT_NORMAL,
                      fg_color=T.BG_SURFACE, hover_color=T.BORDER,
                      text_color=T.TEXT_DIM, height=36,
                      command=self._prev).pack(side="left")
        ctk.CTkButton(nav, text="▶ Lancer le scraping", font=T.FONT_BOLD,
                      fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                      text_color=T.LOG_BG, height=36,
                      command=self._launch).pack(side="right")

    def _toggle_advanced(self):
        self._adv_visible = not self._adv_visible
        self._adv_btn.configure(
            text=("▾ Options avancées (optionnel)" if self._adv_visible
                  else "▸ Options avancées (optionnel)")
        )
        if self._adv_visible:
            self._adv_frame.pack(fill="x", pady=(0, 8))
        else:
            self._adv_frame.pack_forget()

    def _browse_cookies(self):
        path = filedialog.askopenfilename(
            title="Sélectionner cookies.txt",
            filetypes=[("Cookies Netscape", "*.txt"), ("Tous", "*.*")],
        )
        if path:
            self._cookies_path = path
            self._cookies_entry.delete(0, "end")
            self._cookies_entry.insert(0, path)

    def _launch(self):
        self._cookies_path = self._cookies_entry.get().strip()
        self._on_launch(
            url=self._url,
            modes=sorted(self._modes),
            depth=self._depth,
            cookies_path=self._cookies_path or None,
        )

    def show_recap(self):
        """Mettre à jour le récapitulatif avant affichage de l'étape 3."""
        self._recap_url.configure(text=f"🔗 {self._url}")
        mode_names = [name for mid, _, name, _ in MODES if mid in self._modes]
        self._recap_modes.configure(text="Types : " + ", ".join(mode_names))
        depth_label = DEPTH_LABELS[self._depth][1]
        self._recap_depth.configure(text=f"Profondeur : {depth_label}")

    def reset(self, last_url: str = ""):
        """Réinitialiser le wizard pour un nouveau scrape."""
        self._url = last_url
        self._modes = set()
        self._depth = 0
        self._cookies_path = ""
        self._url_entry.delete(0, "end")
        if last_url:
            self._url_entry.insert(0, last_url)
        for var in self._mode_vars.values():
            var.set(False)
        self._select_depth(0, DEPTH_LABELS[0][1])
        self._show_step(0)
