# OmniSnap Phase 1 — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer l'app Windows OmniSnap Phase 1 — interface CustomTkinter pour le scraper CLI Python, livrée en `.exe` PyInstaller.

**Architecture:** Le wizard collecte URL + modes + profondeur, puis ScraperRunner appelle `crawl()` dans un thread séparé avec `log=queue.put`. La GUI lit la queue via `widget.after(100, ...)` et affiche les logs en temps réel. Aucune logique scraper n'est réimplémentée — seul `crawler.py` reçoit un paramètre `cancel_event` supplémentaire.

**Tech Stack:** Python 3.11+, `customtkinter>=5.2`, `pyinstaller>=6.0`, modules scraper existants dans `scraper_modules/`

**Installation des dépendances :**
```
pip install customtkinter pyinstaller
```

---

## Structure des fichiers

```
scraper_app/
├── main.py                      ← point d'entrée CTk
├── gui/
│   ├── __init__.py
│   ├── app.py                   ← fenêtre principale 900×600
│   ├── sidebar.py               ← widget sidebar fixe 160 px
│   ├── wizard.py                ← wizard 4 étapes
│   ├── scrape_view.py           ← vue split log (pendant + après scraping)
│   └── theme.py                 ← constantes couleurs/fonts
├── core/
│   ├── __init__.py
│   └── runner.py                ← ScraperRunner (thread + queue)
├── build/
│   └── OmniSnap.spec            ← config PyInstaller
└── scraper_modules/             ← existant, modif minimale dans crawler.py
    └── crawler.py               ← +cancel_event param
```

---

## Task 1 : Structure de base + thème

**Files :**
- Create: `gui/__init__.py`
- Create: `core/__init__.py`
- Create: `gui/theme.py`
- Create: `main.py` (squelette)

- [ ] **Étape 1 : Créer les packages**

```python
# gui/__init__.py
# (vide)
```

```python
# core/__init__.py
# (vide)
```

- [ ] **Étape 2 : Écrire `gui/theme.py`**

```python
# gui/theme.py
import customtkinter as ctk

BG_MAIN    = "#16213e"
BG_SIDEBAR = "#1a1040"
BG_SURFACE = "#0d0d26"
BORDER     = "#2d2d4e"
ACCENT     = "#00B4D8"
ACCENT_HOVER = "#0096b4"
TEXT       = "#e0e0e0"
TEXT_DIM   = "#888888"
SUCCESS    = "#4CAF50"
WARNING    = "#FF9800"
ERROR      = "#ef5350"
LOG_BG     = "#0a0a1a"

FONT_NORMAL = ("Segoe UI", 12)
FONT_SMALL  = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 12, "bold")
FONT_TITLE  = ("Segoe UI", 14, "bold")
FONT_LOG    = ("Consolas", 10)

def setup():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
```

- [ ] **Étape 3 : Écrire `main.py` (squelette)**

```python
# main.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from gui.theme import setup
from gui.app import App

if __name__ == "__main__":
    setup()
    app = App()
    app.mainloop()
```

- [ ] **Étape 4 : Vérifier les imports**

```
python -c "from gui.theme import BG_MAIN, ACCENT, setup; print('OK')"
```

Attendu : `OK`

- [ ] **Étape 5 : Commit**

```
git add gui/__init__.py core/__init__.py gui/theme.py main.py
git commit -m "feat(omnisnap): structure de base + thème Nuit Électrique"
```

---

## Task 2 : Support annulation dans `crawler.py`

**Files :**
- Modify: `scraper_modules/crawler.py` — signature `crawl()` + vérification cancel_event
- Test: `tests/test_crawler_cancel.py`

- [ ] **Étape 1 : Écrire le test qui échoue**

```python
# tests/test_crawler_cancel.py
import threading
import time
from pathlib import Path
import requests_mock as req_mock
from scraper_modules.crawler import crawl


def test_cancel_event_stops_crawl(tmp_path):
    cancel = threading.Event()
    visited = set()
    session = __import__('requests').Session()

    with req_mock.Mocker() as m:
        m.get("https://example.com/", text="<html><body>hello</body></html>")
        cancel.set()  # annulé d'avance
        crawl(
            url="https://example.com/",
            modes=[1],
            dest=tmp_path,
            depth=0,
            session=session,
            visited=visited,
            cancel_event=cancel,
        )

    assert len(visited) == 0  # crawl s'est arrêté avant de traiter


def test_cancel_event_none_runs_normally(tmp_path):
    visited = set()
    session = __import__('requests').Session()

    with req_mock.Mocker() as m:
        m.get("https://example.com/", text="<html><body>hello</body></html>")
        crawl(
            url="https://example.com/",
            modes=[1],
            dest=tmp_path,
            depth=0,
            session=session,
            visited=visited,
            cancel_event=None,
        )

    assert "https://example.com/" in visited
```

- [ ] **Étape 2 : Lancer le test pour confirmer qu'il échoue**

```
pytest tests/test_crawler_cancel.py -v
```

Attendu : `FAILED` — `TypeError: crawl() got an unexpected keyword argument 'cancel_event'`

- [ ] **Étape 3 : Modifier la signature de `crawl()` dans `crawler.py`**

Localiser la ligne `def crawl(` (ligne ~410) et ajouter `cancel_event` en dernier paramètre, juste avant le corps de la fonction, et ajouter la vérification au tout début du corps :

```python
def crawl(
    url: str,
    modes: list[int],
    dest: Path,
    depth: int,
    session: requests.Session,
    visited: set,
    delay: float = 0.3,
    current_depth: int = 0,
    use_playwright: bool = False,
    playwright_opts: dict | None = None,
    url_filter: str = '',
    content_hashes: set | None = None,
    image_urls_seen: set | None = None,
    video_urls_seen: set | None = None,
    audio_urls_seen: set | None = None,
    doc_urls_seen: set | None = None,
    arc_urls_seen: set | None = None,
    img_ext_filter: set | None = None,
    vid_ext_filter: set | None = None,
    aud_ext_filter: set | None = None,
    doc_ext_filter: set | None = None,
    arc_ext_filter: set | None = None,
    respect_robots: bool = False,
    _robots_cache: dict | None = None,
    progress=None,
    task_url=None,
    session_data: dict | None = None,
    sessions_dir: Path | None = None,
    log: callable | None = None,
    cancel_event=None,          # ← nouveau
):
    if cancel_event is not None and cancel_event.is_set():
        return
    if url in visited or current_depth > depth:
        return
    # ... reste inchangé
```

Aussi propager `cancel_event` dans les appels récursifs à `crawl()` (ligne ~598) :

```python
crawl(url=child_url, modes=modes, dest=dest, depth=depth,
      session=session, visited=visited, delay=delay,
      current_depth=current_depth + 1,
      use_playwright=use_playwright, playwright_opts=playwright_opts,
      url_filter=url_filter, content_hashes=content_hashes,
      image_urls_seen=image_urls_seen, video_urls_seen=video_urls_seen,
      audio_urls_seen=audio_urls_seen, doc_urls_seen=doc_urls_seen,
      arc_urls_seen=arc_urls_seen,
      img_ext_filter=img_ext_filter, vid_ext_filter=vid_ext_filter,
      aud_ext_filter=aud_ext_filter, doc_ext_filter=doc_ext_filter,
      arc_ext_filter=arc_ext_filter,
      respect_robots=respect_robots, _robots_cache=_robots_cache,
      progress=progress, task_url=task_url,
      session_data=session_data, sessions_dir=sessions_dir,
      log=log, cancel_event=cancel_event)   # ← propagé
```

- [ ] **Étape 4 : Lancer tous les tests**

```
pytest tests/ -v
```

Attendu : tous verts (27 existants + 2 nouveaux = 29 PASSED)

- [ ] **Étape 5 : Commit**

```
git add scraper_modules/crawler.py tests/test_crawler_cancel.py
git commit -m "feat(omnisnap): cancel_event dans crawl() pour l'annulation GUI"
```

---

## Task 3 : ScraperRunner

**Files :**
- Create: `core/runner.py`
- Test: `tests/test_runner.py`

- [ ] **Étape 1 : Écrire les tests qui échouent**

```python
# tests/test_runner.py
import queue
import threading
import time
from pathlib import Path
from core.runner import ScraperRunner


def _fake_crawl_ok(**kwargs):
    kwargs['log']("✓ page test")


def _fake_crawl_slow(**kwargs):
    cancel_event = kwargs.get('cancel_event')
    for _ in range(50):
        if cancel_event and cancel_event.is_set():
            return
        kwargs['log']("✓ page")
        time.sleep(0.02)


def _fake_crawl_error(**kwargs):
    raise RuntimeError("Erreur réseau simulée")


def test_runner_done_message(tmp_path):
    q = queue.Queue()
    runner = ScraperRunner(
        url="https://example.com",
        modes=[1],
        depth=0,
        dest_base=tmp_path,
        log_queue=q,
        _crawl_fn=_fake_crawl_ok,
    )
    runner.start()
    runner._thread.join(timeout=5)

    messages = []
    while not q.empty():
        messages.append(q.get_nowait())

    done = next((m for m in messages if isinstance(m, dict) and m.get("type") == "done"), None)
    assert done is not None
    assert "dest" in done


def test_runner_log_forwarded(tmp_path):
    q = queue.Queue()
    runner = ScraperRunner(
        url="https://example.com",
        modes=[1],
        depth=0,
        dest_base=tmp_path,
        log_queue=q,
        _crawl_fn=_fake_crawl_ok,
    )
    runner.start()
    runner._thread.join(timeout=5)

    messages = [m for m in list(q.queue) if isinstance(m, str)]
    assert any("page test" in m for m in messages)


def test_runner_cancel(tmp_path):
    q = queue.Queue()
    runner = ScraperRunner(
        url="https://example.com",
        modes=[1],
        depth=0,
        dest_base=tmp_path,
        log_queue=q,
        _crawl_fn=_fake_crawl_slow,
    )
    runner.start()
    time.sleep(0.05)
    runner.cancel()
    runner._thread.join(timeout=3)

    assert not runner._thread.is_alive()
    messages = list(q.queue)
    cancelled = any(isinstance(m, dict) and m.get("type") == "cancelled" for m in messages)
    assert cancelled


def test_runner_error(tmp_path):
    q = queue.Queue()
    runner = ScraperRunner(
        url="https://example.com",
        modes=[1],
        depth=0,
        dest_base=tmp_path,
        log_queue=q,
        _crawl_fn=_fake_crawl_error,
    )
    runner.start()
    runner._thread.join(timeout=5)

    messages = list(q.queue)
    error = next((m for m in messages if isinstance(m, dict) and m.get("type") == "error"), None)
    assert error is not None
    assert "Erreur réseau" in error["message"]
```

- [ ] **Étape 2 : Lancer les tests pour confirmer qu'ils échouent**

```
pytest tests/test_runner.py -v
```

Attendu : `ModuleNotFoundError: No module named 'core.runner'`

- [ ] **Étape 3 : Écrire `core/runner.py`**

```python
# core/runner.py
import http.cookiejar
import queue
import threading
from pathlib import Path

import requests

from scraper_modules.exporter import url_to_folder, DEFAULT_DEST


class ScraperRunner:
    def __init__(
        self,
        url: str,
        modes: list[int],
        depth: int,
        log_queue: queue.Queue,
        dest_base: Path | None = None,
        cookies_path: str | None = None,
        _crawl_fn=None,
    ):
        self.url = url
        self.modes = modes
        self.depth = depth
        self.log_queue = log_queue
        self.dest_base = Path(dest_base) if dest_base else DEFAULT_DEST
        self.cookies_path = cookies_path
        self._cancel_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._crawl_fn = _crawl_fn  # injectable pour tests

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancel_event.set()

    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _run(self):
        try:
            url_dest = self.dest_base / url_to_folder(self.url)
            session = requests.Session()
            pw_cookies: list[dict] = []

            if self.cookies_path:
                pw_cookies = self._load_cookies(session, self.cookies_path)

            crawl_fn = self._crawl_fn or self._default_crawl
            crawl_fn(
                url=self.url,
                modes=self.modes,
                dest=url_dest,
                depth=self.depth,
                session=session,
                visited=set(),
                log=self._log,
                cancel_event=self._cancel_event,
            )

            if self._cancel_event.is_set():
                self.log_queue.put({"type": "cancelled"})
                return

            files, size_bytes = self._count_output(url_dest)
            self.log_queue.put({
                "type": "done",
                "dest": str(url_dest),
                "files": files,
                "size_bytes": size_bytes,
            })

        except Exception as exc:
            self.log_queue.put({"type": "error", "message": str(exc)})

    @staticmethod
    def _default_crawl(**kwargs):
        from scraper_modules.crawler import crawl
        crawl(**kwargs)

    @staticmethod
    def _load_cookies(session: requests.Session, path: str) -> list[dict]:
        jar = http.cookiejar.MozillaCookieJar(path)
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except Exception as e:
            return []
        session.cookies.update(jar)
        return [
            {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
            for c in jar
        ]

    @staticmethod
    def _count_output(dest: Path) -> tuple[int, int]:
        if not dest.exists():
            return 0, 0
        files = [f for f in dest.rglob("*") if f.is_file()]
        return len(files), sum(f.stat().st_size for f in files)
```

- [ ] **Étape 4 : Lancer les tests**

```
pytest tests/test_runner.py -v
```

Attendu : 4 PASSED

- [ ] **Étape 5 : Lancer tous les tests pour vérifier aucune régression**

```
pytest tests/ -v
```

Attendu : 33 PASSED

- [ ] **Étape 6 : Commit**

```
git add core/runner.py tests/test_runner.py
git commit -m "feat(omnisnap): ScraperRunner — thread + queue + cancel"
```

---

## Task 4 : Sidebar

**Files :**
- Create: `gui/sidebar.py`

*Note : pas de test unitaire automatisé pour les widgets CTk — test manuel à l'étape 3.*

- [ ] **Étape 1 : Écrire `gui/sidebar.py`**

```python
# gui/sidebar.py
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
            text_color="#0a0a1a", corner_radius=6,
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

    def set_active(self, view_name: str):
        """Mettre en surbrillance le bouton correspondant à la vue active."""
        is_scrape = view_name == "scrape"
        self._btn_scrape.configure(
            fg_color=T.ACCENT if is_scrape else "transparent",
            text_color="#0a0a1a" if is_scrape else T.TEXT_DIM,
        )
```

- [ ] **Étape 2 : Smoke test manuel**

Créer temporairement `test_sidebar_manual.py` à la racine :

```python
import customtkinter as ctk
from gui.theme import setup
from gui.sidebar import Sidebar

setup()
root = ctk.CTk()
root.geometry("160x400")
root.configure(fg_color="#16213e")
s = Sidebar(root, on_new_scrape=lambda: print("new scrape"))
s.pack(fill="both", expand=True)
root.mainloop()
```

Lancer : `python test_sidebar_manual.py`

Vérifier : sidebar s'affiche avec logo cyan, 3 boutons, boutons historique/paramètres grisés.

Supprimer `test_sidebar_manual.py` après vérification.

- [ ] **Étape 3 : Commit**

```
git add gui/sidebar.py
git commit -m "feat(omnisnap): widget Sidebar"
```

---

## Task 5 : Wizard (4 étapes)

**Files :**
- Create: `gui/wizard.py`

- [ ] **Étape 1 : Écrire `gui/wizard.py`**

```python
# gui/wizard.py
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
            self.show_recap()  # mettre à jour le récap avant d'afficher l'étape 3
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
                      text_color="#0a0a1a", height=36,
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
                      text_color="#0a0a1a", height=34,
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
                text_color="#0a0a1a" if i == 0 else T.TEXT_DIM,
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
                      text_color="#0a0a1a", height=34,
                      command=self._next).pack(side="right")

    def _select_depth(self, idx: int, desc: str):
        self._depth = idx
        self._depth_desc.configure(text=desc)
        for i, btn in enumerate(self._depth_btns):
            active = (i == idx)
            btn.configure(
                fg_color=T.ACCENT if active else T.BG_SURFACE,
                hover_color=T.ACCENT_HOVER if active else T.BORDER,
                text_color="#0a0a1a" if active else T.TEXT_DIM,
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

        # Section avancée (repliée par défaut)
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
                      text_color="#0a0a1a", height=36,
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
```

- [ ] **Étape 2 : Smoke test manuel**

Créer temporairement `test_wizard_manual.py` :

```python
import customtkinter as ctk
from gui.theme import setup
from gui.wizard import Wizard

def on_launch(**kwargs):
    print("LAUNCH:", kwargs)

setup()
root = ctk.CTk()
root.geometry("740x520")
root.configure(fg_color="#16213e")
w = Wizard(root, on_launch=on_launch, last_url="https://exemple.com")
w.pack(fill="both", expand=True)
root.mainloop()
```

Lancer : `python test_wizard_manual.py`

Vérifier :
- Étape 1 : URL pré-remplie, validation URL incorrecte affiche erreur rouge
- Étape 2 : 8 cases à cocher, sélection obligatoire
- Étape 3 : 4 boutons de profondeur, le premier actif (cyan)
- Étape 4 : récapitulatif, section avancée repliable, bouton "Parcourir…" ouvre dialog
- Clic "Lancer" : affiche `LAUNCH: {url: ..., modes: [...], depth: 0, cookies_path: None}`

Supprimer `test_wizard_manual.py`.

- [ ] **Étape 3 : Commit**

```
git add gui/wizard.py
git commit -m "feat(omnisnap): Wizard 4 étapes"
```

---

## Task 6 : ScrapeView

**Files :**
- Create: `gui/scrape_view.py`

- [ ] **Étape 1 : Écrire `gui/scrape_view.py`**

```python
# gui/scrape_view.py
import os
import queue
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from gui import theme as T


class ScrapeView(ctk.CTkFrame):
    """Vue split : résumé en haut + log en bas. Gère les états en cours / terminé / erreur."""

    def __init__(self, master, on_new_scrape, **kwargs):
        super().__init__(master, fg_color=T.BG_MAIN, corner_radius=0, **kwargs)
        self._on_new_scrape = on_new_scrape
        self._log_queue: queue.Queue | None = None
        self._dest: str = ""
        self._poll_job = None
        self._build()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self):
        # Zone haute (résumé)
        self._top = ctk.CTkFrame(self, fg_color=T.BG_SURFACE,
                                  corner_radius=0, height=120)
        self._top.pack(fill="x")
        self._top.pack_propagate(False)

        top_inner = ctk.CTkFrame(self._top, fg_color="transparent")
        top_inner.pack(fill="both", expand=True, padx=14, pady=10)

        # Ligne 1 : URL + badge état + bouton annuler/ouvrir
        row1 = ctk.CTkFrame(top_inner, fg_color="transparent")
        row1.pack(fill="x")
        self._lbl_url = ctk.CTkLabel(row1, text="", font=T.FONT_SMALL,
                                      text_color=T.TEXT_DIM, anchor="w")
        self._lbl_url.pack(side="left", fill="x", expand=True)
        self._lbl_status = ctk.CTkLabel(row1, text="● En cours",
                                         font=T.FONT_SMALL, text_color=T.WARNING)
        self._lbl_status.pack(side="left", padx=(8, 12))
        self._btn_action = ctk.CTkButton(
            row1, text="⏹ Annuler", width=110, height=30,
            font=T.FONT_SMALL, corner_radius=5,
            fg_color="#c0392b", hover_color="#a93226", text_color="#fff",
            command=self._cancel,
        )
        self._btn_action.pack(side="right")

        # Ligne 2 : tags modes
        self._modes_row = ctk.CTkFrame(top_inner, fg_color="transparent")
        self._modes_row.pack(fill="x", pady=(4, 0))

        # Ligne 3 : compteur + barre progression
        self._lbl_counter = ctk.CTkLabel(top_inner, text="",
                                          font=T.FONT_SMALL, text_color=T.TEXT_DIM,
                                          anchor="w")
        self._lbl_counter.pack(fill="x", pady=(6, 2))
        self._progress = ctk.CTkProgressBar(top_inner, fg_color=T.BG_MAIN,
                                             progress_color=T.WARNING, height=4,
                                             corner_radius=2)
        self._progress.pack(fill="x")
        self._progress.configure(mode="indeterminate")
        self._progress.start()

        # Zone basse (log)
        bottom = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        bottom.pack(fill="both", expand=True, padx=14, pady=(8, 0))

        ctk.CTkLabel(bottom, text="Journal", font=T.FONT_SMALL,
                     text_color=T.TEXT_DIM).pack(anchor="w", pady=(0, 4))

        self._log_box = ctk.CTkTextbox(
            bottom, fg_color=T.LOG_BG, text_color=T.TEXT_DIM,
            font=T.FONT_LOG, wrap="word", state="disabled",
            corner_radius=6,
        )
        self._log_box.pack(fill="both", expand=True)

        # Bouton "Nouveau scrape" (caché jusqu'à la fin)
        self._btn_new = ctk.CTkButton(
            bottom, text="＋ Nouveau scrape", font=T.FONT_NORMAL,
            fg_color=T.BG_SURFACE, hover_color=T.BORDER,
            text_color=T.TEXT_DIM, height=32, corner_radius=5,
            command=self._new_scrape,
        )

    # ── Démarrer ──────────────────────────────────────────────────────────────

    def start(self, url: str, modes: list[int], depth: int, log_queue: queue.Queue,
              runner_cancel_fn):
        from gui.wizard import MODES
        self._log_queue = log_queue
        self._cancel_fn = runner_cancel_fn

        # Reset
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        self._btn_new.pack_forget()
        self._lbl_url.configure(text=url)
        self._lbl_status.configure(text="● En cours", text_color=T.WARNING)
        self._lbl_counter.configure(text="")
        self._btn_action.configure(text="⏹ Annuler", fg_color="#c0392b",
                                    hover_color="#a93226", command=self._cancel)
        self._progress.configure(mode="indeterminate", progress_color=T.WARNING)
        self._progress.start()

        # Tags modes
        for w in self._modes_row.winfo_children():
            w.destroy()
        mode_ids_set = set(modes)
        for mid, _, name, _ in MODES:
            if mid in mode_ids_set:
                tag = ctk.CTkLabel(self._modes_row, text=f" {name} ",
                                   font=T.FONT_SMALL, text_color=T.ACCENT,
                                   fg_color=T.BG_MAIN, corner_radius=10)
                tag.pack(side="left", padx=(0, 4))
        depth_tag = ctk.CTkLabel(self._modes_row, text=f" Profondeur +{depth} ",
                                  font=T.FONT_SMALL, text_color=T.TEXT_DIM,
                                  fg_color=T.BG_MAIN, corner_radius=10)
        depth_tag.pack(side="left")

        self._page_count = 0
        self._file_count = 0
        self._poll()

    # ── Poll queue ────────────────────────────────────────────────────────────

    def _poll(self):
        if self._log_queue is None:
            return
        try:
            while True:
                msg = self._log_queue.get_nowait()
                if isinstance(msg, dict):
                    self._handle_control(msg)
                    return
                self._append_log(msg)
        except queue.Empty:
            pass
        self._poll_job = self.after(100, self._poll)

    def _append_log(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{ts}  {text}\n"
        if "✓" in text:
            color = T.SUCCESS
            if "page" in text.lower() or "analysée" in text.lower():
                self._page_count += 1
        elif "↓" in text or "télécharg" in text.lower():
            color = T.ACCENT
            self._file_count += 1
        elif "⚠" in text:
            color = T.WARNING
        elif "✗" in text:
            color = T.ERROR
        else:
            color = T.TEXT_DIM

        self._lbl_counter.configure(
            text=f"{self._page_count} pages · {self._file_count} fichiers"
        )
        self._log_box.configure(state="normal")
        self._log_box.insert("end", line)
        self._log_box.configure(state="disabled")
        self._log_box.see("end")

    def _handle_control(self, msg: dict):
        if self._poll_job:
            self.after_cancel(self._poll_job)
        t = msg.get("type")
        if t == "done":
            self._dest = msg.get("dest", "")
            files = msg.get("files", 0)
            size_mb = msg.get("size_bytes", 0) / (1024 * 1024)
            summary = f"{self._page_count} pages · {files} fichiers · {size_mb:.1f} MB"
            self._set_done(summary)
        elif t == "cancelled":
            self._set_error("Scraping annulé.")
        elif t == "error":
            self._set_error(msg.get("message", "Erreur inconnue"))

    # ── États finaux ──────────────────────────────────────────────────────────

    def _set_done(self, summary: str):
        self._progress.stop()
        self._progress.configure(mode="determinate", progress_color=T.SUCCESS)
        self._progress.set(1.0)
        self._lbl_status.configure(text="✅ Terminé", text_color=T.SUCCESS)
        self._lbl_counter.configure(text=summary)
        self._btn_action.configure(
            text="📂 Ouvrir le dossier", fg_color=T.SUCCESS,
            hover_color="#388e3c", command=self._open_folder,
        )
        self._btn_new.pack(anchor="e", pady=(6, 8))

    def _set_error(self, message: str):
        self._progress.stop()
        self._progress.configure(mode="determinate", progress_color=T.ERROR)
        self._progress.set(1.0)
        self._lbl_status.configure(text="✗ Erreur", text_color=T.ERROR)
        self._lbl_counter.configure(text=message)
        self._btn_action.configure(
            text="↩ Réessayer", fg_color=T.BG_SURFACE,
            hover_color=T.BORDER, text_color=T.TEXT_DIM,
            command=self._on_new_scrape,
        )
        self._btn_new.pack(anchor="e", pady=(6, 8))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _cancel(self):
        if hasattr(self, "_cancel_fn") and self._cancel_fn:
            self._cancel_fn()

    def _open_folder(self):
        if self._dest and Path(self._dest).exists():
            if sys.platform == "win32":
                os.startfile(self._dest)
            else:
                subprocess.Popen(["xdg-open", self._dest])

    def _new_scrape(self):
        self._on_new_scrape()
```

- [ ] **Étape 2 : Smoke test manuel**

Créer temporairement `test_scrapeview_manual.py` :

```python
import queue, threading, time
import customtkinter as ctk
from gui.theme import setup
from gui.scrape_view import ScrapeView

def fake_scrape(q):
    for i in range(8):
        time.sleep(0.4)
        q.put(f"✓ Page {i+1} analysée")
        if i % 3 == 0:
            q.put(f"↓ video_{i}.mp4 (24 MB)")
    time.sleep(0.3)
    q.put({"type": "done", "dest": "C:/tmp", "files": 3, "size_bytes": 75000000})

setup()
root = ctk.CTk()
root.geometry("740x520")
root.configure(fg_color="#16213e")
q = queue.Queue()
sv = ScrapeView(root, on_new_scrape=lambda: print("nouveau scrape"))
sv.pack(fill="both", expand=True)
sv.start("https://exemple.com/article", [1, 7], 0, q, runner_cancel_fn=None)
threading.Thread(target=fake_scrape, args=(q,), daemon=True).start()
root.mainloop()
```

Lancer : `python test_scrapeview_manual.py`

Vérifier :
- Logs apparaissent en temps réel avec couleurs (vert ✓, cyan ↓)
- Compteur "X pages · X fichiers" se met à jour
- Après 4 secondes : bannière verte, barre verte 100%, bouton "📂 Ouvrir le dossier"
- Bouton "＋ Nouveau scrape" apparaît en bas

Supprimer `test_scrapeview_manual.py`.

- [ ] **Étape 3 : Commit**

```
git add gui/scrape_view.py
git commit -m "feat(omnisnap): ScrapeView — split log + états terminé/erreur"
```

---

## Task 7 : App principale + main.py

**Files :**
- Create: `gui/app.py`
- Modify: `main.py` (déjà créé en Task 1)

- [ ] **Étape 1 : Écrire `gui/app.py`**

```python
# gui/app.py
import json
import os
import queue
from pathlib import Path

import customtkinter as ctk

from gui import theme as T
from gui.sidebar import Sidebar
from gui.wizard import Wizard
from gui.scrape_view import ScrapeView
from core.runner import ScraperRunner

PREFS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "OmniSnap"
PREFS_FILE = PREFS_DIR / "prefs.json"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OmniSnap")
        self.geometry("900x600")
        self.resizable(False, False)
        self.configure(fg_color=T.BG_MAIN)
        self._runner: ScraperRunner | None = None
        self._last_url = self._load_prefs().get("last_url", "")
        self._build()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self):
        self._sidebar = Sidebar(self, on_new_scrape=self._show_wizard)
        self._sidebar.pack(side="left", fill="y")

        self._main = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0)
        self._main.pack(side="left", fill="both", expand=True)

        self._wizard = Wizard(self._main, on_launch=self._launch,
                               last_url=self._last_url)
        self._scrape_view = ScrapeView(self._main, on_new_scrape=self._show_wizard)

        self._show_wizard()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _show_wizard(self):
        self._scrape_view.pack_forget()
        self._wizard.pack(fill="both", expand=True)
        self._wizard.reset(last_url=self._last_url)
        self._sidebar.set_active("scrape")

    def _show_scrape_view(self):
        self._wizard.pack_forget()
        self._scrape_view.pack(fill="both", expand=True)

    # ── Lancement scraping ────────────────────────────────────────────────────

    def _launch(self, url: str, modes: list[int], depth: int,
                cookies_path: str | None):
        self._last_url = url
        self._save_prefs({"last_url": url})

        log_queue: queue.Queue = queue.Queue()
        self._runner = ScraperRunner(
            url=url,
            modes=modes,
            depth=depth,
            log_queue=log_queue,
            cookies_path=cookies_path,
        )
        self._show_scrape_view()
        self._scrape_view.start(
            url=url,
            modes=modes,
            depth=depth,
            log_queue=log_queue,
            runner_cancel_fn=self._runner.cancel,
        )
        self._runner.start()

    # ── Persistance ───────────────────────────────────────────────────────────

    def _load_prefs(self) -> dict:
        try:
            return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_prefs(self, data: dict):
        try:
            PREFS_DIR.mkdir(parents=True, exist_ok=True)
            PREFS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
```

- [ ] **Étape 2 : Lancer l'application complète**

```
python main.py
```

Vérifier le flux complet :
1. Fenêtre 900×600 s'ouvre, sidebar à gauche, wizard à droite
2. Étape 1 — entrer une URL valide, cliquer Suivant
3. Étape 2 — sélectionner "Texte propre", Suivant
4. Étape 3 — profondeur 0, Suivant
5. Étape 4 — récap affiché correctement, cliquer "▶ Lancer le scraping"
6. ScrapeView s'affiche, logs défilent en temps réel
7. À la fin : bannière verte, bouton "📂 Ouvrir le dossier"
8. Clic "＋ Nouveau scrape" : retour au wizard, URL pré-remplie

- [ ] **Étape 3 : Commit**

```
git add gui/app.py main.py
git commit -m "feat(omnisnap): App principale — navigation wizard↔scrapeview + persistance URL"
```

---

## Task 8 : Build PyInstaller

**Files :**
- Create: `build/OmniSnap.spec`

- [ ] **Étape 1 : Créer le dossier build**

```
mkdir build
```

- [ ] **Étape 2 : Générer le .spec de base**

Depuis `scraper_app/` :

```
pyi-makespec main.py --name OmniSnap --windowed --onefile --specpath build/
```

Ceci crée `build/OmniSnap.spec`. L'éditer pour s'assurer que les données CustomTkinter sont incluses :

- [ ] **Étape 3 : Écrire `build/OmniSnap.spec`**

```python
# build/OmniSnap.spec
import sys
from pathlib import Path
import customtkinter

block_cipher = None

ctk_path = Path(customtkinter.__file__).parent

a = Analysis(
    ['../main.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        (str(ctk_path), 'customtkinter'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._imagingtk',
        'scraper_modules.crawler',
        'scraper_modules.downloader',
        'scraper_modules.exporter',
        'scraper_modules.detector',
        'scraper_modules.session',
        'scraper_modules.mediawiki',
        'scraper_modules.progress',
        'core.runner',
        'gui.app',
        'gui.sidebar',
        'gui.wizard',
        'gui.scrape_view',
        'gui.theme',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='OmniSnap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    windowed=True,
)
```

- [ ] **Étape 4 : Builder le .exe**

Depuis `scraper_app/` :

```
pyinstaller build/OmniSnap.spec --distpath build/dist --workpath build/work --noconfirm
```

Attendu : `build/dist/OmniSnap.exe` créé sans erreur.

- [ ] **Étape 5 : Tester le .exe**

Double-cliquer sur `build/dist/OmniSnap.exe` (sans Python installé si possible, ou dans un venv désactivé).

Vérifier : la fenêtre OmniSnap s'ouvre normalement.

- [ ] **Étape 6 : Commit**

```
git add build/OmniSnap.spec
git commit -m "feat(omnisnap): config PyInstaller Phase 1"
```

---

## Critères de succès

- [ ] `pytest tests/ -v` → 33 PASSED (27 existants + 2 cancel + 4 runner)
- [ ] `python main.py` → app fonctionnelle, flux complet wizard → scraping → résultat
- [ ] `build/dist/OmniSnap.exe` → lanceable sans Python, même comportement
- [ ] Bouton "⏹ Annuler" arrête le scraper proprement
- [ ] Bouton "📂 Ouvrir le dossier" ouvre l'explorateur Windows au bon endroit
- [ ] L'app se ferme proprement (pas de thread zombie)
