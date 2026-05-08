# gui/queue_view.py
import customtkinter as ctk

from core.queue import QueuedTask
from gui.wizard import MODES

# Build modes dict: mode_id -> (icon, name)
_MODES_DICT = {mode[0]: (mode[1], mode[2]) for mode in MODES}


class QueueView(ctk.CTkFrame):
    def __init__(self, master, on_close, on_edit, on_remove, on_add, on_clear, **kwargs):
        kwargs.setdefault("fg_color", "#1e293b")
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        self._on_close = on_close
        self._on_edit = on_edit
        self._on_remove = on_remove
        self._on_add = on_add
        self._on_clear = on_clear
        self._build()

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 8))

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_block, text="Tâches en attente",
            font=("Segoe UI", 13, "bold"), text_color="#e2e8f0", anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_block, text="Démarrent automatiquement après la tâche en cours",
            font=("Segoe UI", 11), text_color="#64748b", anchor="w",
        ).pack(anchor="w")

        ctk.CTkButton(
            header, text="✕ Fermer",
            font=("Segoe UI", 11), text_color="#94a3b8",
            fg_color="#1e293b", hover_color="#334155",
            border_color="#334155", border_width=1,
            corner_radius=6, width=70, height=30,
            command=self._on_close,
        ).pack(side="right", padx=(8, 0))

        # ── Corps scrollable ─────────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="#1e293b", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=14)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=14, pady=(8, 12))

        ctk.CTkButton(
            footer, text="🗑 Vider la file",
            font=("Segoe UI", 11), text_color="#94a3b8",
            fg_color="#1e293b", hover_color="#334155",
            border_color="#334155", border_width=1,
            corner_radius=6, height=30,
            command=self._on_clear,
        ).pack(fill="x")

    def refresh(self, tasks: list[QueuedTask]) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()

        for position, task in enumerate(tasks, start=1):
            self._build_task_row(task, position)

        # Bouton "➕ Ajouter une autre URL" en bas de liste
        ctk.CTkButton(
            self._scroll, text="➕ Ajouter une autre URL",
            font=("Segoe UI", 11), text_color="#64748b",
            fg_color="#1e293b", hover_color="#1e3a5f",
            border_color="#334155", border_width=1,
            corner_radius=6, height=30,
            command=self._on_add,
        ).pack(fill="x", pady=(4, 0))

    def _build_task_row(self, task: QueuedTask, position: int) -> None:
        card = ctk.CTkFrame(self._scroll, fg_color="#1e293b",
                            border_color="#334155", border_width=1, corner_radius=6)
        card.pack(fill="x", pady=(0, 4))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=9, pady=7)

        # Boutons ✎ et ✕ (à droite, packés en premier pour réserver l'espace)
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(
            btn_frame, text="✎", width=28, height=28,
            font=("Segoe UI", 14), text_color="#94a3b8",
            fg_color="transparent", hover_color="#334155",
            corner_radius=4,
            command=lambda t_id=task.id: self._on_edit(t_id),
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_frame, text="✕", width=28, height=28,
            font=("Segoe UI", 14), text_color="#ef4444",
            fg_color="transparent", hover_color="#3f1212",
            corner_radius=4,
            command=lambda t_id=task.id: self._on_remove(t_id),
        ).pack(side="left")

        # Bloc texte (à gauche)
        text_block = ctk.CTkFrame(inner, fg_color="transparent")
        text_block.pack(side="left", fill="x", expand=True)

        # Numéro de position (discret)
        ctk.CTkLabel(
            text_block, text=f"#{position}",
            font=("Segoe UI", 9), text_color="#475569",
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_block, text=task.url,
            font=("Segoe UI", 12), text_color="#e2e8f0",
            anchor="w", wraplength=0,
        ).pack(anchor="w", fill="x")

        # Construire la liste des modes avec noms en clair
        modes_names = []
        for mode_id in sorted(task.modes):
            if mode_id in _MODES_DICT:
                icon, name = _MODES_DICT[mode_id]
                modes_names.append(f"{icon} {name}")

        # Tronquer si plus de 3 modes
        if len(modes_names) > 3:
            modes_str = " · ".join(modes_names[:3]) + " · ..."
        else:
            modes_str = " · ".join(modes_names)

        detail = f"{modes_str} · profondeur: {task.depth}"
        ctk.CTkLabel(
            text_block, text=detail,
            font=("Segoe UI", 10), text_color="#64748b",
            anchor="w",
        ).pack(anchor="w")

        # Badges indicateurs
        if task.url_filter or task.respect_robots:
            badges_row = ctk.CTkFrame(text_block, fg_color="transparent")
            badges_row.pack(anchor="w", pady=(2, 0))

            if task.url_filter:
                url_filter_display = task.url_filter[:20]
                ctk.CTkLabel(
                    badges_row, text=f"🔍 {url_filter_display}",
                    font=("Segoe UI", 10), text_color="#94a3b8",
                    fg_color="#334155", corner_radius=4,
                ).pack(side="left", padx=(2, 4), pady=2)

            if task.respect_robots:
                ctk.CTkLabel(
                    badges_row, text="🤖 robots.txt",
                    font=("Segoe UI", 10), text_color="#94a3b8",
                    fg_color="#334155", corner_radius=4,
                ).pack(side="left", padx=(2, 0), pady=2)
