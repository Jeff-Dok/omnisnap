# File d'attente multi-URL (Phase 3) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre d'ajouter des tâches de scraping en file d'attente pendant qu'une tâche est en cours, avec exécution automatique FIFO.

**Architecture:** `QueueManager` (logique pure dans `core/`) + `QueueView` (panel GUI) + badge vert dans Sidebar. App orchestre via callbacks. Pas de persistance (file volatile).

**Tech Stack:** Python 3.11+, CustomTkinter 5.2+, dataclasses stdlib

---

## Fichiers

| Action | Fichier |
|---|---|
| Créer | `core/queue.py` |
| Créer | `gui/queue_view.py` |
| Créer | `tests/test_queue.py` |
| Modifier | `gui/sidebar.py` |
| Modifier | `gui/scrape_view.py` |
| Modifier | `gui/wizard.py` |
| Modifier | `gui/app.py` |
| Modifier | `build/OmniSnap.spec` |

---

## Task 1 : core/queue.py — QueuedTask + QueueManager

**Files:**
- Create: `core/queue.py`
- Create: `tests/test_queue.py`

- [ ] **Step 1 : Écrire les tests (fichier complet)**

Créer `tests/test_queue.py` :

```python
# tests/test_queue.py
from core.queue import QueuedTask, QueueManager


def _task(**kw):
    defaults = {"url": "https://example.com", "modes": [1], "depth": 0, "cookies_path": None}
    defaults.update(kw)
    return QueuedTask(**defaults)


class TestQueueManager:
    def setup_method(self):
        self.q = QueueManager()

    def test_empty_by_default(self):
        assert self.q.count() == 0
        assert self.q.all() == []

    def test_add_increases_count(self):
        self.q.add(_task())
        assert self.q.count() == 1

    def test_all_returns_copy(self):
        task = _task()
        self.q.add(task)
        result = self.q.all()
        assert result[0] is task
        result.clear()
        assert self.q.count() == 1  # copie, pas la liste interne

    def test_remove_by_id(self):
        task = _task()
        self.q.add(task)
        self.q.remove(task.id)
        assert self.q.count() == 0

    def test_remove_unknown_id_silent(self):
        self.q.remove("nonexistent-id")  # ne doit pas lever d'exception

    def test_next_returns_first_and_removes(self):
        t1 = _task(url="https://a.com")
        t2 = _task(url="https://b.com")
        self.q.add(t1)
        self.q.add(t2)
        assert self.q.next() is t1
        assert self.q.count() == 1

    def test_next_empty_returns_none(self):
        assert self.q.next() is None

    def test_fifo_order(self):
        urls = ["https://a.com", "https://b.com", "https://c.com"]
        for u in urls:
            self.q.add(_task(url=u))
        for u in urls:
            assert self.q.next().url == u

    def test_clear(self):
        self.q.add(_task())
        self.q.add(_task())
        self.q.clear()
        assert self.q.count() == 0
        assert self.q.all() == []

    def test_unique_ids(self):
        t1 = _task()
        t2 = _task()
        assert t1.id != t2.id
```

- [ ] **Step 2 : Lancer les tests — vérifier qu'ils échouent**

```
pytest tests/test_queue.py -v
```

Attendu : `ModuleNotFoundError: No module named 'core.queue'`

- [ ] **Step 3 : Créer core/queue.py**

```python
# core/queue.py
import uuid
from dataclasses import dataclass, field


@dataclass
class QueuedTask:
    url: str
    modes: list[int]
    depth: int
    cookies_path: str | None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class QueueManager:
    def __init__(self) -> None:
        self._tasks: list[QueuedTask] = []

    def add(self, task: QueuedTask) -> None:
        self._tasks.append(task)

    def remove(self, task_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.id != task_id]

    def clear(self) -> None:
        self._tasks = []

    def next(self) -> QueuedTask | None:
        if not self._tasks:
            return None
        return self._tasks.pop(0)

    def all(self) -> list[QueuedTask]:
        return list(self._tasks)

    def count(self) -> int:
        return len(self._tasks)
```

- [ ] **Step 4 : Lancer les tests — vérifier qu'ils passent**

```
pytest tests/test_queue.py -v
```

Attendu : 10 tests PASSED

- [ ] **Step 5 : Commit**

```
git add core/queue.py tests/test_queue.py
git commit -m "feat: add QueuedTask and QueueManager for multi-URL queue"
```

---

## Task 2 : gui/sidebar.py — Badge vert dynamique

**Files:**
- Modify: `gui/sidebar.py`

Le badge vert s'affiche en bas de la sidebar quand la file est non vide. Il comporte : grand chiffre, "Tâche(s) en attente", et optionnellement un séparateur + "▼ Voir la liste" (seulement quand ScrapeView est active).

- [ ] **Step 1 : Ajouter `on_badge_click` au constructeur**

Remplacer la signature de `__init__` :

```python
def __init__(self, master, on_new_scrape, on_history, on_settings, on_badge_click, **kwargs):
    super().__init__(master, fg_color=T.BG_SIDEBAR, width=160,
                     corner_radius=0, **kwargs)
    self.pack_propagate(False)
    self._on_new_scrape = on_new_scrape
    self._on_history = on_history
    self._on_settings = on_settings
    self._on_badge_click = on_badge_click
    self._build()
```

- [ ] **Step 2 : Ajouter les widgets badge dans `_build()` (après le bouton settings)**

Ajouter à la fin de `_build()`, après `self._btn_settings.pack(...)` :

```python
    # Badge vert — masqué par défaut (pack_forget à la fin)
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
    # Badge masqué par défaut
```

Note : `fg_color="#14532d"` rend le séparateur et le label "▼ Voir la liste" invisibles initialement (couleur = fond du badge). `update_badge` les rend visibles en changeant leur couleur.

- [ ] **Step 3 : Ajouter la méthode `update_badge`**

Ajouter après `set_active` :

```python
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
```

- [ ] **Step 4 : Commit**

```
git add gui/sidebar.py
git commit -m "feat: add queue badge to sidebar with update_badge()"
```

---

## Task 3 : gui/scrape_view.py — Bouton "➕ Ajouter une tâche"

**Files:**
- Modify: `gui/scrape_view.py`

Le bouton apparaît à côté d'Annuler dans le header (row1 de top_inner), visible seulement pendant le scrape actif.

- [ ] **Step 1 : Ajouter `on_add_task` au constructeur**

Modifier `__init__` :

```python
def __init__(self, master, on_new_scrape, on_done=None, on_add_task=None, **kwargs):
    super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0, **kwargs)
    self._on_new_scrape = on_new_scrape
    self._on_done = on_done
    self._on_add_task = on_add_task
    # ... reste inchangé
```

- [ ] **Step 2 : Ajouter `_btn_add` dans `_build()` dans row1**

Dans `_build()`, après `self._btn_action.pack(side="right")`, ajouter :

```python
        self._btn_add = ctk.CTkButton(
            row1, text="➕ Ajouter une tâche", width=130, height=30,
            font=T.FONT_SMALL, corner_radius=5,
            fg_color="#14532d", hover_color="#166534",
            border_color="#16a34a", border_width=1,
            text_color="#86efac",
            command=self._add_task,
        )
        self._btn_add.pack(side="right", padx=(0, 8))
```

- [ ] **Step 3 : Ajouter la méthode `_add_task`**

```python
    def _add_task(self):
        if self._on_add_task:
            self._on_add_task()
```

- [ ] **Step 4 : Masquer le bouton dans `start()` puis le réafficher**

Dans `start()`, après `self._btn_new.pack_forget()`, ajouter :

```python
        if not self._btn_add.winfo_ismapped():
            self._btn_add.pack(side="right", padx=(0, 8))
```

- [ ] **Step 5 : Masquer le bouton dans `_set_done()` et `_set_error()`**

Dans `_set_done()`, avant `self._btn_new.pack(...)` :

```python
        self._btn_add.pack_forget()
```

Dans `_set_error()`, avant `self._btn_new.pack(...)` :

```python
        self._btn_add.pack_forget()
```

- [ ] **Step 6 : Commit**

```
git add gui/scrape_view.py
git commit -m "feat: add 'Ajouter une tâche' button to ScrapeView header"
```

---

## Task 4 : gui/wizard.py — Mode enqueue

**Files:**
- Modify: `gui/wizard.py`

En mode enqueue, le bouton step 4 dit "➕ Ajouter aux tâches en attente" et route vers `on_enqueue` au lieu de `on_launch`. Le mode est reset automatiquement via `reset()`.

- [ ] **Step 1 : Ajouter `on_enqueue` et `_enqueue_mode` au constructeur**

Modifier `__init__` :

```python
    def __init__(self, master, on_launch, on_enqueue=None, last_url: str = "", **kwargs):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0, **kwargs)
        self._on_launch = on_launch
        self._on_enqueue = on_enqueue
        self._enqueue_mode = False
        self._step = 0
        # ... reste inchangé
```

- [ ] **Step 2 : Stocker la référence au bouton "Lancer" dans `_build_step3()`**

Dans `_build_step3()`, remplacer :

```python
        ctk.CTkButton(self._nav_step3, text="▶ Lancer le scraping", font=T.FONT_BOLD,
                      fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                      text_color=T.LOG_BG, height=36,
                      command=self._launch).pack(side="right")
```

par :

```python
        self._btn_launch = ctk.CTkButton(
            self._nav_step3, text="▶ Lancer le scraping", font=T.FONT_BOLD,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            text_color=T.LOG_BG, height=36,
            command=self._launch,
        )
        self._btn_launch.pack(side="right")
```

- [ ] **Step 3 : Modifier `_launch()` pour router selon le mode**

Remplacer la méthode `_launch` existante :

```python
    def _launch(self):
        self._cookies_path = self._cookies_entry.get().strip()
        params = dict(
            url=self._url,
            modes=sorted(self._modes),
            depth=self._depth,
            cookies_path=self._cookies_path or None,
        )
        if self._enqueue_mode and self._on_enqueue:
            self._on_enqueue(**params)
        else:
            self._on_launch(**params)
```

- [ ] **Step 4 : Ajouter `set_enqueue_mode()`**

Ajouter après `prefill()` :

```python
    def set_enqueue_mode(self, active: bool) -> None:
        self._enqueue_mode = active
        text = "➕ Ajouter aux tâches en attente" if active else "▶ Lancer le scraping"
        self._btn_launch.configure(text=text)
```

- [ ] **Step 5 : Réinitialiser le mode dans `reset()`**

Dans `reset()`, ajouter avant `self._show_step(0)` :

```python
        self._enqueue_mode = False
        self._btn_launch.configure(text="▶ Lancer le scraping")
```

- [ ] **Step 6 : Commit**

```
git add gui/wizard.py
git commit -m "feat: add enqueue mode to Wizard (on_enqueue callback + set_enqueue_mode)"
```

---

## Task 5 : gui/queue_view.py — Vue liste des tâches

**Files:**
- Create: `gui/queue_view.py`

- [ ] **Step 1 : Créer le fichier complet**

```python
# gui/queue_view.py
import customtkinter as ctk

from gui import theme as T
from core.queue import QueuedTask


class QueueView(ctk.CTkFrame):
    """Panel liste des tâches en attente — remplace ScrapeView dans la zone principale."""

    def __init__(self, master, on_close, on_add, on_remove, on_edit, on_clear, **kwargs):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0, **kwargs)
        self._on_close = on_close
        self._on_add = on_add
        self._on_remove = on_remove
        self._on_edit = on_edit
        self._on_clear = on_clear
        self._build()

    def _build(self):
        # ── Header ───────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=T.BG_SURFACE, corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=10)

        title_col = ctk.CTkFrame(inner, fg_color="transparent")
        title_col.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(title_col, text="Tâches en attente",
                     font=T.FONT_BOLD, text_color=T.TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(title_col,
                     text="Démarrent automatiquement après la tâche en cours",
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM, anchor="w").pack(anchor="w")

        ctk.CTkButton(
            inner, text="✕ Fermer", width=80, height=28,
            font=T.FONT_SMALL, corner_radius=5,
            fg_color=T.BG_MAIN, hover_color=T.BORDER,
            text_color=T.TEXT_DIM, border_color=T.BORDER, border_width=1,
            command=self._on_close,
        ).pack(side="right", padx=(8, 0))

        # ── Body ─────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        body.pack(fill="both", expand=True, padx=14, pady=(12, 0))

        self._list_frame = ctk.CTkScrollableFrame(body, fg_color=T.BG_MAIN, corner_radius=0)
        self._list_frame.pack(fill="both", expand=True)

        # ── Footer ───────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(body, fg_color=T.BG_MAIN, corner_radius=0)
        footer.pack(fill="x", pady=(8, 8))
        ctk.CTkButton(
            footer, text="🗑 Vider la file", height=32,
            font=T.FONT_SMALL, corner_radius=5,
            fg_color=T.BG_SURFACE, hover_color=T.BORDER,
            text_color=T.TEXT_DIM, border_color=T.BORDER, border_width=1,
            command=self._on_clear,
        ).pack(fill="x")

    def refresh(self, tasks: list[QueuedTask]) -> None:
        for child in self._list_frame.winfo_children():
            child.destroy()

        for task in tasks:
            self._add_task_row(task)

        ctk.CTkButton(
            self._list_frame, text="➕ Ajouter une autre URL",
            height=32, font=T.FONT_SMALL, corner_radius=5,
            fg_color="transparent", hover_color=T.BG_SURFACE,
            text_color=T.TEXT_DIM, border_color=T.BORDER, border_width=1,
            command=self._on_add,
        ).pack(fill="x", pady=(4, 0))

    def _add_task_row(self, task: QueuedTask) -> None:
        from gui.wizard import MODES, DEPTH_LABELS

        row = ctk.CTkFrame(self._list_frame, fg_color=T.BG_SURFACE, corner_radius=6)
        row.pack(fill="x", pady=(0, 4))

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)

        display_url = task.url if len(task.url) <= 45 else task.url[:45] + "…"
        ctk.CTkLabel(info, text=display_url,
                     font=T.FONT_SMALL, text_color=T.TEXT, anchor="w").pack(anchor="w")

        mode_names = [name for mid, _, name, _ in MODES if mid in set(task.modes)]
        depth_str = DEPTH_LABELS[task.depth][0] if task.depth < len(DEPTH_LABELS) else f"+{task.depth}"
        detail = " · ".join(mode_names) + f" · profondeur {depth_str}"
        ctk.CTkLabel(info, text=detail,
                     font=T.FONT_SMALL, text_color=T.TEXT_DIM, anchor="w").pack(anchor="w")

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="right", padx=(0, 10), pady=6)

        ctk.CTkButton(
            actions, text="✎", width=28, height=28,
            font=T.FONT_NORMAL, corner_radius=4,
            fg_color=T.BG_MAIN, hover_color=T.BORDER, text_color=T.TEXT_DIM,
            command=lambda t=task: self._on_edit(t),
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            actions, text="✕", width=28, height=28,
            font=T.FONT_NORMAL, corner_radius=4,
            fg_color=T.BG_MAIN, hover_color="#7f1d1d", text_color=T.ERROR,
            command=lambda t=task: self._on_remove(t.id),
        ).pack(side="left")
```

- [ ] **Step 2 : Commit**

```
git add gui/queue_view.py
git commit -m "feat: add QueueView panel for pending task list"
```

---

## Task 6 : gui/app.py — Orchestration complète

**Files:**
- Modify: `gui/app.py`

C'est la tâche d'intégration. Tout est câblé ici.

- [ ] **Step 1 : Ajouter les imports**

En haut du fichier, ajouter après `from core.notifier import notify` :

```python
from core.queue import QueueManager, QueuedTask
from gui.queue_view import QueueView
```

- [ ] **Step 2 : Ajouter `self._queue` dans `__init__`**

Dans `__init__`, après `self._store = AppStore()` :

```python
        self._queue: QueueManager = QueueManager()
```

- [ ] **Step 3 : Mettre à jour `_build()` — câbler Sidebar, ScrapeView, Wizard, ajouter QueueView**

Remplacer tout `_build()` par :

```python
    def _build(self):
        self._sidebar = Sidebar(
            self,
            on_new_scrape=self._show_wizard,
            on_history=self._show_history,
            on_settings=self._show_settings,
            on_badge_click=self._show_queue_view,
        )
        self._sidebar.pack(side="left", fill="y")

        self._main = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        self._main.pack(side="left", fill="both", expand=True)

        self._wizard = Wizard(
            self._main, on_launch=self._launch,
            on_enqueue=self._enqueue,
            last_url=self._last_url,
        )
        self._scrape_view = ScrapeView(
            self._main, on_new_scrape=self._show_wizard,
            on_done=self._on_scrape_done,
            on_add_task=self._show_wizard_enqueue,
        )
        self._history_view = HistoryView(
            self._main, store=self._store,
            on_relaunch=self._relaunch_direct,
            on_wizard_relaunch=self._relaunch_wizard,
        )
        self._settings_view = SettingsView(
            self._main, store=self._store,
            on_theme_change=T.apply_theme,
        )
        self._queue_view = QueueView(
            self._main,
            on_close=self._show_scrape_view,
            on_add=self._show_wizard_enqueue,
            on_remove=self._on_queue_remove,
            on_edit=self._on_queue_edit,
            on_clear=self._on_queue_clear,
        )
        self._show_wizard()
```

- [ ] **Step 4 : Mettre à jour `_hide_all()` pour inclure QueueView**

```python
    def _hide_all(self):
        for view in (self._wizard, self._scrape_view,
                     self._history_view, self._settings_view, self._queue_view):
            view.pack_forget()
```

- [ ] **Step 5 : Mettre à jour les méthodes de navigation pour appeler `_refresh_badge`**

Remplacer `_show_wizard` :

```python
    def _show_wizard(self):
        self._hide_all()
        self._wizard.pack(fill="both", expand=True)
        self._wizard.reset(last_url=self._last_url)
        self._sidebar.set_active("scrape")
        self._refresh_badge(show_see_list=False)
```

Remplacer `_show_scrape_view` :

```python
    def _show_scrape_view(self):
        self._hide_all()
        self._scrape_view.pack(fill="both", expand=True)
        self._refresh_badge(show_see_list=True)
```

Remplacer `_show_history` :

```python
    def _show_history(self):
        self._hide_all()
        self._history_view.refresh()
        self._history_view.pack(fill="both", expand=True)
        self._sidebar.set_active("history")
        self._refresh_badge(show_see_list=False)
```

Remplacer `_show_settings` :

```python
    def _show_settings(self):
        self._hide_all()
        self._settings_view.refresh()
        self._settings_view.pack(fill="both", expand=True)
        self._sidebar.set_active("settings")
        self._refresh_badge(show_see_list=False)
```

- [ ] **Step 6 : Ajouter les nouvelles méthodes de navigation et gestion de file**

Ajouter après `_show_settings` :

```python
    def _show_queue_view(self):
        self._hide_all()
        self._queue_view.refresh(self._queue.all())
        self._queue_view.pack(fill="both", expand=True)
        self._refresh_badge(show_see_list=False)

    def _show_wizard_enqueue(self):
        self._hide_all()
        self._wizard.pack(fill="both", expand=True)
        self._wizard.reset(last_url=self._last_url)
        self._wizard.set_enqueue_mode(True)
        self._sidebar.set_active("scrape")
        self._refresh_badge(show_see_list=False)

    def _refresh_badge(self, show_see_list: bool = False) -> None:
        self._sidebar.update_badge(self._queue.count(), show_see_list=show_see_list)

    def _enqueue(self, url: str, modes: list, depth: int, cookies_path: str | None):
        task = QueuedTask(url=url, modes=modes, depth=depth, cookies_path=cookies_path)
        self._queue.add(task)
        self._show_scrape_view()

    def _launch_queued(self, task: QueuedTask) -> None:
        self._launch(url=task.url, modes=task.modes, depth=task.depth,
                     cookies_path=task.cookies_path)

    def _on_queue_remove(self, task_id: str) -> None:
        self._queue.remove(task_id)
        if self._queue.count() == 0:
            self._show_scrape_view()
        else:
            self._queue_view.refresh(self._queue.all())
            self._refresh_badge(show_see_list=False)

    def _on_queue_edit(self, task: QueuedTask) -> None:
        self._queue.remove(task.id)
        self._show_wizard_enqueue()
        self._wizard.prefill(url=task.url, modes=task.modes, depth=task.depth)

    def _on_queue_clear(self) -> None:
        self._queue.clear()
        self._show_scrape_view()
```

- [ ] **Step 7 : Mettre à jour `_on_scrape_done()` pour l'auto-start**

Remplacer `_on_scrape_done` :

```python
    def _on_scrape_done(self, result: dict):
        entry = {
            "id": str(uuid.uuid4()),
            "url": result["url"],
            "modes": result["modes"],
            "depth": result["depth"],
            "status": result["status"],
            "date": datetime.datetime.now().isoformat(timespec="seconds"),
            "pages": result.get("pages", 0),
            "file_count": result.get("file_count", 0),
            "size_mb": result.get("size_mb", 0.0),
            "dest_path": result.get("dest_path", ""),
            "error_msg": result.get("error_msg"),
        }
        self._store.add_entry(entry)
        settings = self._store.get_settings()
        if settings.get("notifications", True) and result["status"] in ("done", "error"):
            notify(result["status"], result["url"], result)
        if result["status"] == "done" and settings.get("auto_open"):
            dest = entry["dest_path"]
            if dest:
                try:
                    os.startfile(dest)
                except Exception:
                    pass
        next_task = self._queue.next()
        if next_task:
            self._launch_queued(next_task)
```

- [ ] **Step 8 : Lancer tous les tests**

```
pytest tests/ -v
```

Attendu : tous les tests PASSED (minimum 53 + 10 nouveaux = 63 tests)

- [ ] **Step 9 : Commit**

```
git add gui/app.py
git commit -m "feat: wire queue feature in App — badge, auto-start, enqueue flow"
```

---

## Task 7 : Mettre à jour OmniSnap.spec

**Files:**
- Modify: `build/OmniSnap.spec`

- [ ] **Step 1 : Ajouter core.queue et gui.queue_view aux hiddenimports**

Dans `build/OmniSnap.spec`, dans la liste `hiddenimports`, ajouter `'core.queue'` et `'gui.queue_view'` :

```python
hiddenimports=[
    'core.store', 'core.notifier', 'core.queue',
    'gui.history_view', 'gui.settings_view', 'gui.queue_view',
    'winotify',
    # ... autres existants
],
```

- [ ] **Step 2 : Commit**

```
git add build/OmniSnap.spec
git commit -m "build: add core.queue and gui.queue_view to PyInstaller hiddenimports"
```

---

## Validation manuelle après implémentation

Tester le flux complet :

1. Lancer l'app → wizard affiché, pas de badge
2. Lancer un scrape → ScrapeView visible, bouton "➕ Ajouter une tâche" visible en haut à droite
3. Clic "➕" → wizard s'ouvre, bouton step 4 dit "➕ Ajouter aux tâches en attente"
4. Confirmer → retour ScrapeView, badge vert "1 · Tâche(s) en attente · ▼ Voir la liste" apparaît
5. Ajouter une 2ème tâche → badge dit "2"
6. Clic badge / "▼ Voir la liste" → QueueView : 2 tâches listées, badge dit "2" sans "▼ Voir la liste"
7. Supprimer une tâche → badge dit "1", reste en QueueView
8. Supprimer la dernière → retour auto à ScrapeView, badge disparaît
9. Scrape se termine → tâche suivante démarre automatiquement (si file non vide)
10. ✎ Modifier une tâche → wizard prefill, nouvelle tâche en fin de file après confirmation
11. 🗑 Vider la file → retour ScrapeView, badge disparaît
