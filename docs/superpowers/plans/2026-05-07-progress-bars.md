# Progress Bars (rich) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter des barres de progression rich au CLI scraper : barre globale (URLs saisies), spinner URL + compteur de pages crawlées, et barre unitaire par fichier lourd téléchargé (vidéo/audio/doc/archive).

**Architecture:** Module centralisé `progress.py` expose `make_progress()`. `scraper.py` crée l'instance et la passe explicitement aux handlers et au crawler. Tous les paramètres `progress` sont optionnels (`None` par défaut) — zéro régression sur le code existant.

**Tech Stack:** Python 3.10+, `rich` (`pip install rich`), `pytest`

---

## Structure des fichiers

| Action | Fichier | Responsabilité |
|---|---|---|
| Créer | `scraper_modules/progress.py` | Factory `make_progress()` |
| Créer | `conftest.py` | Setup PYTHONPATH pour pytest |
| Créer | `tests/__init__.py` | Package marker |
| Créer | `tests/test_progress.py` | Tous les tests |
| Modifier | `scraper_modules/crawler.py` | Barres unitaires + compteur pages |
| Modifier | `scraper.py` | Barre globale + spinner URL + wiring |

---

## Task 1 — Créer `scraper_modules/progress.py` et infrastructure de test

**Files:**
- Create: `scraper_app/scraper_modules/progress.py`
- Create: `scraper_app/conftest.py`
- Create: `scraper_app/tests/__init__.py`
- Create: `scraper_app/tests/test_progress.py`

- [ ] **Step 1 : Créer `conftest.py` à la racine de `scraper_app/`**

```python
# conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

- [ ] **Step 2 : Créer `tests/__init__.py` vide**

Fichier vide — marque le dossier comme package Python.

- [ ] **Step 3 : Écrire le test qui échoue**

```python
# tests/test_progress.py
from rich.progress import Progress


def test_make_progress_returns_progress_instance():
    from scraper_modules.progress import make_progress
    p = make_progress()
    assert isinstance(p, Progress)


def test_make_progress_has_required_columns():
    from scraper_modules.progress import make_progress
    from rich.progress import SpinnerColumn, BarColumn, TaskProgressColumn
    p = make_progress()
    column_types = [type(c) for c in p.columns]
    assert SpinnerColumn in column_types
    assert BarColumn in column_types
    assert TaskProgressColumn in column_types
```

- [ ] **Step 4 : Vérifier que le test échoue**

```
cd scraper_app
pip install rich pytest
pytest tests/test_progress.py -v
```

Résultat attendu : `ModuleNotFoundError: No module named 'scraper_modules.progress'`

- [ ] **Step 5 : Créer `scraper_modules/progress.py`**

```python
# scraper_modules/progress.py
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn,
    TaskProgressColumn, TransferSpeedColumn, DownloadColumn,
    TimeRemainingColumn,
)


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TransferSpeedColumn(),
        DownloadColumn(),
        TimeRemainingColumn(),
    )
```

- [ ] **Step 6 : Vérifier que les tests passent**

```
pytest tests/test_progress.py -v
```

Résultat attendu : `2 passed`

- [ ] **Step 7 : Commit**

```
git add scraper_modules/progress.py conftest.py tests/__init__.py tests/test_progress.py
git commit -m "feat: add progress.py factory and test infrastructure"
```

---

## Task 2 — Barre unitaire dans `_download_files()`

**Files:**
- Modify: `scraper_app/scraper_modules/crawler.py` (lignes 203–246)
- Test: `scraper_app/tests/test_progress.py`

- [ ] **Step 1 : Ajouter les tests**

Ajouter à la fin de `tests/test_progress.py` :

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, call


def _make_mock_session(content=b"data", content_length="4"):
    session = MagicMock()
    resp = MagicMock()
    resp.headers = {"Content-Length": content_length} if content_length else {}
    resp.iter_content.return_value = [content]
    resp.raise_for_status.return_value = None
    session.get.return_value = resp
    return session


def test_download_files_no_progress_regression(tmp_path):
    """progress=None doit fonctionner exactement comme avant."""
    from scraper_modules.crawler import _download_files
    session = _make_mock_session()
    seen = set()
    count = _download_files(
        ["https://example.com/report.pdf"],
        tmp_path, session, seen, ext_filter=None, label="doc"
    )
    assert count == 1
    assert (tmp_path / "report.pdf").exists()


def test_download_files_with_progress_calls_advance(tmp_path):
    """Avec progress, add_task/advance/remove_task doivent être appelés."""
    from scraper_modules.crawler import _download_files
    session = _make_mock_session(content=b"x" * 100, content_length="100")
    seen = set()
    progress = MagicMock()
    progress.add_task.return_value = 42
    count = _download_files(
        ["https://example.com/archive.zip"],
        tmp_path, session, seen, ext_filter=None, label="archive",
        progress=progress
    )
    assert count == 1
    progress.add_task.assert_called_once_with("archive.zip", total=100)
    progress.advance.assert_called_with(42, 100)
    progress.remove_task.assert_called_once_with(42)


def test_download_files_no_content_length(tmp_path):
    """Sans Content-Length, total doit être None (barre indéterminée)."""
    from scraper_modules.crawler import _download_files
    session = _make_mock_session(content_length=None)
    seen = set()
    progress = MagicMock()
    progress.add_task.return_value = 0
    _download_files(
        ["https://example.com/doc.pdf"],
        tmp_path, session, seen, ext_filter=None, label="doc",
        progress=progress
    )
    progress.add_task.assert_called_once_with("doc.pdf", total=None)
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```
pytest tests/test_progress.py -v
```

Résultat attendu : `3 failed` (les 3 nouveaux tests)

- [ ] **Step 3 : Modifier `_download_files()` dans `crawler.py`**

Remplacer la fonction `_download_files` (lignes ~203–234) par :

```python
def _download_files(urls: list[str], dest: Path, session: requests.Session,
                    seen: set, ext_filter: set | None, label: str,
                    progress=None) -> int:
    count = 0
    for url in urls:
        if ext_filter:
            ext = Path(urlparse(url).path).suffix.lower()
            if ext not in ext_filter:
                continue
        if url in seen:
            continue
        try:
            fname = _safe(Path(urlparse(url).path).name or label)
            if not fname or fname == '_':
                fname = f"{label}_{count + 1}"
            out = dest / fname
            if out.exists():
                seen.add(url)
                continue
            r = session.get(url, headers=HEADERS, timeout=120, stream=True)
            r.raise_for_status()
            dest.mkdir(parents=True, exist_ok=True)
            content_length = int(r.headers.get('Content-Length', 0)) or None
            task_file = progress.add_task(fname, total=content_length) if progress else None
            with open(out, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
                    if progress and task_file is not None:
                        progress.advance(task_file, len(chunk))
            if progress and task_file is not None:
                progress.remove_task(task_file)
            seen.add(url)
            if not progress:
                print(f"    ✅ {fname}")
            count += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"    ✗ {url}: {e}")
    return count
```

- [ ] **Step 4 : Mettre à jour `_download_documents()` et `_download_archives()` pour transmettre `progress`**

Remplacer les deux fonctions (lignes ~237–246) par :

```python
def _download_documents(doc_urls, dest, session, seen=None, ext_filter=None, progress=None):
    if seen is None:
        seen = set()
    return _download_files(doc_urls, dest, session, seen, ext_filter, 'document', progress)


def _download_archives(arc_urls, dest, session, seen=None, ext_filter=None, progress=None):
    if seen is None:
        seen = set()
    return _download_files(arc_urls, dest, session, seen, ext_filter, 'archive', progress)
```

- [ ] **Step 5 : Vérifier que tous les tests passent**

```
pytest tests/test_progress.py -v
```

Résultat attendu : `5 passed`

- [ ] **Step 6 : Commit**

```
git add scraper_modules/crawler.py tests/test_progress.py
git commit -m "feat: add unit progress bar to _download_files, docs and archives"
```

---

## Task 3 — Barre unitaire dans `_download_videos()` et `_download_audios()`

**Files:**
- Modify: `scraper_app/scraper_modules/crawler.py` (lignes ~125–200)
- Test: `scraper_app/tests/test_progress.py`

- [ ] **Step 1 : Ajouter les tests**

Ajouter à la fin de `tests/test_progress.py` :

```python
def test_download_videos_with_progress(tmp_path):
    from scraper_modules.crawler import _download_videos
    session = _make_mock_session(content=b"v" * 200, content_length="200")
    progress = MagicMock()
    progress.add_task.return_value = 7
    count = _download_videos(
        ["https://cdn.example.com/clip.mp4"],
        tmp_path, session, progress=progress
    )
    assert count == 1
    progress.add_task.assert_called_once_with("clip.mp4", total=200)
    progress.remove_task.assert_called_once_with(7)


def test_download_audios_with_progress(tmp_path):
    from scraper_modules.crawler import _download_audios
    session = _make_mock_session(content=b"a" * 50, content_length="50")
    progress = MagicMock()
    progress.add_task.return_value = 3
    count = _download_audios(
        ["https://cdn.example.com/track.mp3"],
        tmp_path, session, progress=progress
    )
    assert count == 1
    progress.add_task.assert_called_once_with("track.mp3", total=50)
    progress.remove_task.assert_called_once_with(3)


def test_download_videos_no_progress_regression(tmp_path):
    from scraper_modules.crawler import _download_videos
    session = _make_mock_session()
    count = _download_videos(["https://cdn.example.com/clip.mp4"], tmp_path, session)
    assert count == 1
    assert (tmp_path / "clip.mp4").exists()
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```
pytest tests/test_progress.py -v
```

Résultat attendu : `3 failed` (les 3 nouveaux tests)

- [ ] **Step 3 : Modifier `_download_videos()` dans `crawler.py`**

Remplacer la signature et le bloc de téléchargement dans `_download_videos` (lignes ~125–163) :

```python
def _download_videos(video_urls: list[str], dest: Path, session: requests.Session,
                     video_urls_seen: set | None = None,
                     ext_filter: set | None = None,
                     progress=None) -> int:
    if video_urls_seen is None:
        video_urls_seen = set()
    if ext_filter:
        video_urls = [u for u in video_urls
                      if Path(urlparse(u).path).suffix.lower() in ext_filter]
    best = _best_quality_urls(video_urls)
    count = 0
    for url in best:
        canonical = _canonical_video_key(url)
        if canonical in video_urls_seen:
            continue
        try:
            fname = _safe(Path(urlparse(url).path).name or 'video')
            if not fname or fname == '_':
                fname = f"video_{count+1}"
            out = dest / fname
            if out.exists():
                if not progress:
                    print(f"    [skip] {fname} (déjà téléchargé)")
                video_urls_seen.add(canonical)
                continue
            parts = urlparse(url).path.split('/')
            quality = f"  [{parts[-2]}px]" if len(parts) >= 2 and parts[-2].isdigit() else ""
            r = session.get(url, headers=HEADERS, timeout=60, stream=True)
            r.raise_for_status()
            dest.mkdir(parents=True, exist_ok=True)
            content_length = int(r.headers.get('Content-Length', 0)) or None
            task_file = progress.add_task(fname, total=content_length) if progress else None
            with open(out, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
                    if progress and task_file is not None:
                        progress.advance(task_file, len(chunk))
            if progress and task_file is not None:
                progress.remove_task(task_file)
            video_urls_seen.add(canonical)
            if not progress:
                print(f"    ✅ {fname}{quality}")
            count += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"    ✗ {url}: {e}")
    return count
```

- [ ] **Step 4 : Modifier `_download_audios()` dans `crawler.py`**

Remplacer `_download_audios` (lignes ~166–200) :

```python
def _download_audios(audio_urls: list[str], dest: Path, session: requests.Session,
                     audio_urls_seen: set | None = None,
                     ext_filter: set | None = None,
                     progress=None) -> int:
    if audio_urls_seen is None:
        audio_urls_seen = set()
    count = 0
    for url in audio_urls:
        if ext_filter:
            ext = Path(urlparse(url).path).suffix.lower()
            if ext not in ext_filter:
                continue
        if url in audio_urls_seen:
            continue
        try:
            fname = _safe(Path(urlparse(url).path).name or 'audio')
            if not fname or fname == '_':
                fname = f"audio_{count + 1}"
            out = dest / fname
            if out.exists():
                audio_urls_seen.add(url)
                continue
            r = session.get(url, headers=HEADERS, timeout=60, stream=True)
            r.raise_for_status()
            dest.mkdir(parents=True, exist_ok=True)
            content_length = int(r.headers.get('Content-Length', 0)) or None
            task_file = progress.add_task(fname, total=content_length) if progress else None
            with open(out, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
                    if progress and task_file is not None:
                        progress.advance(task_file, len(chunk))
            if progress and task_file is not None:
                progress.remove_task(task_file)
            audio_urls_seen.add(url)
            if not progress:
                print(f"    ✅ {fname}")
            count += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"    ✗ {url}: {e}")
    return count
```

- [ ] **Step 5 : Vérifier que tous les tests passent**

```
pytest tests/test_progress.py -v
```

Résultat attendu : `8 passed`

- [ ] **Step 6 : Commit**

```
git add scraper_modules/crawler.py tests/test_progress.py
git commit -m "feat: add unit progress bar to _download_videos and _download_audios"
```

---

## Task 4 — Compteur de pages dans `crawl()`

**Files:**
- Modify: `scraper_app/scraper_modules/crawler.py` (lignes ~364–549)
- Test: `scraper_app/tests/test_progress.py`

- [ ] **Step 1 : Ajouter le test**

Ajouter à la fin de `tests/test_progress.py` :

```python
def test_crawl_updates_task_url_description(tmp_path):
    """crawl() doit mettre à jour la description de task_url à chaque page visitée."""
    from unittest.mock import patch
    from scraper_modules.crawler import crawl

    html = "<html><body><p>Hello</p></body></html>"
    session = MagicMock()
    resp = MagicMock()
    resp.text = html
    resp.url = "https://example.com/"
    resp.raise_for_status.return_value = None
    session.get.return_value = resp

    progress = MagicMock()
    task_url = 5

    crawl(
        url="https://example.com/",
        modes=[1],
        dest=tmp_path,
        depth=0,
        session=session,
        visited=set(),
        progress=progress,
        task_url=task_url,
    )

    progress.update.assert_called_with(
        task_url,
        description="example.com — 1 pages visitées"
    )
```

- [ ] **Step 2 : Vérifier que le test échoue**

```
pytest tests/test_progress.py::test_crawl_updates_task_url_description -v
```

Résultat attendu : `FAILED` — `crawl() got unexpected keyword argument 'progress'`

- [ ] **Step 3 : Modifier la signature de `crawl()` dans `crawler.py`**

Ajouter `progress=None, task_url=None` à la fin des paramètres de `crawl()` (lignes ~364–389) :

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
):
```

- [ ] **Step 4 : Ajouter la mise à jour du compteur au début du corps de `crawl()`**

Juste après `visited.add(url)` (ligne ~391), ajouter :

```python
    if progress and task_url is not None:
        progress.update(task_url, description=f"{urlparse(url).netloc} — {len(visited)} pages visitées")
```

- [ ] **Step 5 : Passer `progress` aux appels de téléchargement dans `crawl()`**

Dans le bloc `for mode in active_modes:`, modifier les 4 appels concernés :

```python
        elif mode == 7:
            # ... (code existant inchangé pour la détection)
            if vid_urls:
                count = _download_videos(vid_urls, vid_dest, session, video_urls_seen,
                                         ext_filter=vid_ext_filter, progress=progress)
            # ...

        elif mode == 8:
            # ...
            if aud_urls:
                count = _download_audios(aud_urls, aud_dest, session, audio_urls_seen,
                                         ext_filter=aud_ext_filter, progress=progress)
            # ...

        elif mode == 9:
            # ...
            if doc_urls:
                count = _download_documents(doc_urls, doc_dest, session, doc_urls_seen,
                                            ext_filter=doc_ext_filter, progress=progress)
            # ...

        elif mode == 10:
            # ...
            if arc_urls:
                count = _download_archives(arc_urls, arc_dest, session, arc_urls_seen,
                                           ext_filter=arc_ext_filter, progress=progress)
            # ...
```

- [ ] **Step 6 : Passer `progress` et `task_url` dans l'appel récursif de `crawl()` (ligne ~532–549)**

```python
    if current_depth < depth:
        for child_url in _extract_links(html, url):
            if child_url not in visited and _same_domain(child_url, url):
                if url_filter and url_filter.lower() not in child_url.lower():
                    continue
                time.sleep(delay)
                crawl(url=child_url, modes=modes, dest=dest, depth=depth,
                      session=session, visited=visited, delay=delay,
                      current_depth=current_depth + 1,
                      use_playwright=use_playwright, playwright_opts=playwright_opts,
                      url_filter=url_filter, content_hashes=content_hashes,
                      image_urls_seen=image_urls_seen, video_urls_seen=video_urls_seen,
                      audio_urls_seen=audio_urls_seen,
                      doc_urls_seen=doc_urls_seen, arc_urls_seen=arc_urls_seen,
                      img_ext_filter=img_ext_filter, vid_ext_filter=vid_ext_filter,
                      aud_ext_filter=aud_ext_filter,
                      doc_ext_filter=doc_ext_filter, arc_ext_filter=arc_ext_filter,
                      respect_robots=respect_robots, _robots_cache=_robots_cache,
                      progress=progress, task_url=task_url)
```

- [ ] **Step 7 : Vérifier que tous les tests passent**

```
pytest tests/test_progress.py -v
```

Résultat attendu : `9 passed`

- [ ] **Step 8 : Commit**

```
git add scraper_modules/crawler.py tests/test_progress.py
git commit -m "feat: add page counter to crawl() via progress task_url"
```

---

## Task 5 — Wiring dans `scraper.py` (barre globale + spinner URL)

**Files:**
- Modify: `scraper_app/scraper.py`

Pas de tests unitaires — validation manuelle.

- [ ] **Step 1 : Ajouter les imports en haut de `scraper.py`**

Après la ligne `import sys, http.cookiejar` (ligne 7), ajouter :

```python
from urllib.parse import urlparse
```

Après `from scraper_modules import crawler as _crawler` (ligne 16), ajouter :

```python
from scraper_modules.progress import make_progress
```

- [ ] **Step 2 : Modifier la signature de `_handle_general()`**

Ligne ~205 — ajouter `progress=None, task_url=None` :

```python
def _handle_general(url: str, dest: Path, session: requests.Session,
                    pw_cookies: list | None = None,
                    progress=None, task_url=None):
```

Modifier l'appel à `_crawler.crawl()` dans `_handle_general()` (ligne ~344) pour passer `progress` et `task_url` :

```python
        _crawler.crawl(url=url, modes=content_modes, dest=dest, depth=depth,
                       session=session, visited=set(),
                       use_playwright=(engine == 2), playwright_opts=playwright_opts,
                       url_filter=url_filter,
                       img_ext_filter=img_ext_filter, vid_ext_filter=vid_ext_filter,
                       aud_ext_filter=aud_ext_filter,
                       doc_ext_filter=doc_ext_filter, arc_ext_filter=arc_ext_filter,
                       respect_robots=respect_robots,
                       progress=progress, task_url=task_url)
```

- [ ] **Step 3 : Modifier la signature de `_handle_mediawiki()`**

Ligne ~354 — ajouter `progress=None, task_url=None` :

```python
def _handle_mediawiki(url: str, dest: Path, session: requests.Session,
                      progress=None, task_url=None):
```

Note : `crawl_mediawiki()` n'a pas de barres unitaires dans cette version — `progress` est reçu mais pas transmis (YAGNI). Le compteur de pages pourra être ajouté ultérieurement si nécessaire.

- [ ] **Step 4 : Modifier la signature de `_handle_js()`**

Ligne ~422 — ajouter `progress=None` :

```python
def _handle_js(url: str, dest: Path, session: requests.Session,
               pw_cookies: list | None = None, progress=None):
```

Modifier les appels aux fonctions de téléchargement dans `_handle_js()` pour passer `progress` :

```python
            if 6 in modes:
                # ... (code existant inchangé pour la détection)
                if vid_urls:
                    count = _download_videos(vid_urls, vid_dest, session,
                                             ext_filter=vid_ext_filter, progress=progress)
                # ...

            if 7 in modes:
                # ...
                if aud_urls:
                    count = _download_audios(aud_urls, aud_dest, session,
                                             ext_filter=aud_ext_filter, progress=progress)
                # ...

            if 8 in modes:
                # ...
                if doc_urls:
                    count = _download_documents(doc_urls, doc_dest, session,
                                                ext_filter=doc_ext_filter, progress=progress)
                # ...

            if 9 in modes:
                # ...
                if arc_urls:
                    count = _download_archives(arc_urls, arc_dest, session,
                                               ext_filter=arc_ext_filter, progress=progress)
                # ...
```

- [ ] **Step 5 : Modifier `main()` pour créer la barre globale et le spinner URL**

Dans `main()`, remplacer la boucle `for url in urls:` (lignes ~649–696) par :

```python
    with make_progress() as progress:
        task_global = progress.add_task("Scraping global", total=len(urls))

        for url in urls:
            if not url.startswith('http'):
                url = 'https://' + url

            url_dest = dest / url_to_folder(url)
            url_dest.mkdir(parents=True, exist_ok=True)

            progress.console.print(f'\n{"═" * 47}')
            url_type = detect(url)

            netloc = urlparse(url).netloc
            task_url = progress.add_task(f"{netloc} — 0 pages visitées", total=None)

            if url_type == 'general' and is_js_heavy(url):
                progress.console.print('  ⚠ Ce site semble utiliser beaucoup de JavaScript.')
                progress.console.print('    Avec requests, la page pourrait être incomplète.')
                js_choice = _ask_choice(
                    "  Que faire ?",
                    [
                        (1, "Continuer avec requests  — plus rapide, peut manquer du contenu"),
                        (2, "Utiliser Playwright      — charge la page comme un vrai navigateur (recommandé)"),
                    ],
                    default=2,
                )
                if js_choice == 2:
                    url_type = 'js'

            type_labels = {
                'mediawiki': '🔖  Wiki MediaWiki  (Wikipedia, UESP, Fandom...)',
                'github':    '🐙  GitHub',
                'js':        '⚡  Site interactif JS  (Playwright)',
                'general':   '🌐  Site général',
            }
            progress.console.print(f"\n  Type détecté → {type_labels.get(url_type, url_type)}")

            try:
                if url_type == 'mediawiki':
                    _handle_mediawiki(url, url_dest, session,
                                      progress=progress, task_url=task_url)
                elif url_type == 'github':
                    _handle_github(url, url_dest, session)
                elif url_type == 'js':
                    _handle_js(url, url_dest, session,
                               pw_cookies=pw_cookies, progress=progress)
                else:
                    _handle_general(url, url_dest, session,
                                    pw_cookies=pw_cookies,
                                    progress=progress, task_url=task_url)
                open_folder(url_dest)
            except KeyboardInterrupt:
                progress.console.print('\n  Interrompu (Ctrl+C).')
            except Exception as e:
                progress.console.print(f'\n  ❌ Erreur : {e}')
            finally:
                progress.update(task_url, visible=False)
                progress.advance(task_global)
```

- [ ] **Step 6 : Test manuel — 1 URL sans crawl**

```
cd scraper_app
python scraper.py
```

Entrer `https://example.com`, mode 1 (Texte), profondeur 0.

Résultat attendu :
- Barre `Scraping global ━━━━━━━━━━━━━━━━━━━━━━━━ 0/1  0%` apparaît
- Spinner `example.com — 1 pages visitées` s'anime pendant le scrape
- Barre passe à `1/1 100%` à la fin
- Fichier `page.txt` créé dans `Downloads/Scraper/example.com/`

- [ ] **Step 7 : Test manuel — 2 URLs avec fichier lourd**

Entrer deux URLs dont une avec des vidéos (ex. une page avec des MP4 directs), mode 7.

Résultat attendu :
- Barre globale avance de 1 par URL complétée
- Barre unitaire apparaît pour chaque vidéo avec vitesse MB/s et ETA
- Barre unitaire disparaît une fois le fichier terminé

- [ ] **Step 8 : Commit final**

```
git add scraper.py
git commit -m "feat: wire rich progress bars in scraper.py — global bar + URL spinner"
```
