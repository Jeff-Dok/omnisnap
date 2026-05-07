# Reprise sur interruption — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter la reprise sur interruption — skip des URLs déjà traitées, re-téléchargement des fichiers partiels, persistance de session dans `scraper_app/sessions/`.

**Architecture:** Nouveau module `session.py` (load/save/is_partial). `crawler.py` détecte les partiels avant skip et sauvegarde la session après chaque page. `scraper.py` charge la session avant chaque URL, reconstitue `visited`, marque la session complète en fin de run.

**Tech Stack:** stdlib uniquement — `json`, `pathlib`, `datetime`, `urllib.parse`. Aucune nouvelle dépendance.

---

### Task 1: `session.py` — `is_partial()` + constantes

**Files:**
- Create: `scraper_app/scraper_modules/session.py`
- Create: `scraper_app/tests/test_session.py`

- [ ] **Step 1: Écrire les tests failing pour `is_partial()`**

```python
# scraper_app/tests/test_session.py
from pathlib import Path
from scraper_modules.session import is_partial, MIN_SIZE_VIDEO_AUDIO, MIN_SIZE_DOC_ARCHIVE


def test_is_partial_content_length_match(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"x" * 1000)
    assert not is_partial(f, content_length=1000)


def test_is_partial_content_length_mismatch(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"x" * 500)
    assert is_partial(f, content_length=1000)


def test_is_partial_no_content_length_large_enough(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"x" * MIN_SIZE_VIDEO_AUDIO)
    assert not is_partial(f, content_length=None, min_size=MIN_SIZE_VIDEO_AUDIO)


def test_is_partial_no_content_length_too_small(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"x" * 100)
    assert is_partial(f, content_length=None, min_size=MIN_SIZE_VIDEO_AUDIO)


def test_is_partial_file_not_exists(tmp_path):
    f = tmp_path / "nonexistent.mp4"
    assert not is_partial(f, content_length=None)


def test_is_partial_default_min_size(tmp_path):
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"x" * (MIN_SIZE_DOC_ARCHIVE - 1))
    assert is_partial(f, content_length=None)
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `pytest scraper_app/tests/test_session.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'scraper_modules.session'`

- [ ] **Step 3: Créer `session.py`**

```python
# scraper_app/scraper_modules/session.py
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

MIN_SIZE_VIDEO_AUDIO = 65536   # 64 KB
MIN_SIZE_DOC_ARCHIVE = 1024    # 1 KB

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"


def is_partial(path: Path, content_length: int | None, min_size: int = MIN_SIZE_DOC_ARCHIVE) -> bool:
    if not path.exists():
        return False
    size = path.stat().st_size
    if content_length is not None:
        return size != content_length
    return size < min_size
```

- [ ] **Step 4: Vérifier que les tests passent**

Run: `pytest scraper_app/tests/test_session.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add scraper_app/scraper_modules/session.py scraper_app/tests/test_session.py
git commit -m "feat: add session module with is_partial() for partial file detection"
```

---

### Task 2: `session.py` — `load_session()` + `save_session()`

**Files:**
- Modify: `scraper_app/scraper_modules/session.py`
- Modify: `scraper_app/tests/test_session.py`

- [ ] **Step 1: Ajouter les tests failing**

Append to `scraper_app/tests/test_session.py`:

```python
from scraper_modules.session import load_session, save_session


def _make_session_data(url="https://example.com"):
    return {
        "url": url,
        "dest": "/tmp/example",
        "modes": [7, 8],
        "completed": False,
        "visited": ["https://example.com/"],
        "started_at": "2026-05-07T100000",
        "completed_at": None,
    }


def test_load_session_no_dir(tmp_path):
    result = load_session("https://example.com", sessions_dir=tmp_path / "sessions")
    assert result is None


def test_save_and_load_session(tmp_path):
    sessions_dir = tmp_path / "sessions"
    data = _make_session_data()
    save_session(data, sessions_dir=sessions_dir)
    result = load_session("https://example.com", sessions_dir=sessions_dir)
    assert result is not None
    assert result["url"] == "https://example.com"
    assert result["visited"] == ["https://example.com/"]
    assert result["completed"] is False


def test_load_session_corrupted_json(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "bad.json").write_text("not json", encoding="utf-8")
    result = load_session("https://example.com", sessions_dir=sessions_dir)
    assert result is None


def test_load_session_no_match(tmp_path):
    sessions_dir = tmp_path / "sessions"
    data = _make_session_data("https://other.com")
    save_session(data, sessions_dir=sessions_dir)
    result = load_session("https://example.com", sessions_dir=sessions_dir)
    assert result is None


def test_save_session_creates_dir(tmp_path):
    sessions_dir = tmp_path / "sessions"
    assert not sessions_dir.exists()
    save_session(_make_session_data(), sessions_dir=sessions_dir)
    assert sessions_dir.exists()
    assert len(list(sessions_dir.glob("*.json"))) == 1


def test_save_session_updates_existing(tmp_path):
    sessions_dir = tmp_path / "sessions"
    data = _make_session_data()
    save_session(data, sessions_dir=sessions_dir)
    data["visited"].append("https://example.com/page2")
    save_session(data, sessions_dir=sessions_dir)
    files = list(sessions_dir.glob("*.json"))
    assert len(files) == 1
    result = load_session("https://example.com", sessions_dir=sessions_dir)
    assert "https://example.com/page2" in result["visited"]
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `pytest scraper_app/tests/test_session.py::test_save_and_load_session -v`
Expected: FAIL avec `ImportError: cannot import name 'load_session'`

- [ ] **Step 3: Ajouter `load_session()` et `save_session()` dans `session.py`**

```python
def load_session(url: str, sessions_dir: Path = SESSIONS_DIR) -> dict | None:
    if not sessions_dir.exists():
        return None
    for f in sessions_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            if data.get('url') == url:
                data['_session_file'] = str(f)
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return None


def save_session(data: dict, sessions_dir: Path = SESSIONS_DIR) -> None:
    sessions_dir.mkdir(parents=True, exist_ok=True)
    if '_session_file' in data:
        path = Path(data['_session_file'])
    else:
        netloc = urlparse(data['url']).netloc.replace('.', '_').replace(':', '_')
        ts = data.get('started_at', datetime.now().isoformat(timespec='seconds'))
        ts_clean = ts.replace(':', '').replace('-', '').replace('T', '')[:14]
        path = sessions_dir / f"{ts_clean}_{netloc}.json"
        data['_session_file'] = str(path)
    to_save = {k: v for k, v in data.items() if k != '_session_file'}
    path.write_text(json.dumps(to_save, ensure_ascii=False, indent=2), encoding='utf-8')
```

- [ ] **Step 4: Vérifier que tous les tests passent**

Run: `pytest scraper_app/tests/test_session.py -v`
Expected: 12 PASS

- [ ] **Step 5: Commit**

```bash
git add scraper_app/scraper_modules/session.py scraper_app/tests/test_session.py
git commit -m "feat: add load_session() and save_session() to session module"
```

---

### Task 3: `crawler.py` — détection de partiels dans les téléchargements

**Files:**
- Modify: `scraper_app/scraper_modules/crawler.py`
- Modify: `scraper_app/tests/test_progress.py`

- [ ] **Step 1: Ajouter les tests failing**

Append to `scraper_app/tests/test_progress.py` (MagicMock déjà importé) :

```python
from scraper_modules.session import MIN_SIZE_DOC_ARCHIVE, MIN_SIZE_VIDEO_AUDIO


def test_download_files_skips_complete_file(tmp_path):
    dest = tmp_path / "archives"
    dest.mkdir()
    out = dest / "archive.zip"
    out.write_bytes(b"x" * MIN_SIZE_DOC_ARCHIVE)
    session = MagicMock()
    count = _download_files(
        ["http://example.com/archive.zip"],
        dest, session, set(), ext_filter=None, label="archive"
    )
    assert count == 0
    session.get.assert_not_called()


def test_download_files_redownloads_partial_file(tmp_path):
    dest = tmp_path / "archives"
    dest.mkdir()
    out = dest / "archive.zip"
    out.write_bytes(b"x" * 10)
    session = MagicMock()
    r = MagicMock()
    r.headers = {}
    r.iter_content.return_value = [b"x" * MIN_SIZE_DOC_ARCHIVE]
    session.get.return_value = r
    count = _download_files(
        ["http://example.com/archive.zip"],
        dest, session, set(), ext_filter=None, label="archive"
    )
    assert count == 1
    session.get.assert_called_once()


def test_download_videos_redownloads_partial_file(tmp_path):
    dest = tmp_path / "videos"
    dest.mkdir()
    out = dest / "video.mp4"
    out.write_bytes(b"x" * 100)
    session = MagicMock()
    r = MagicMock()
    r.headers = {}
    r.iter_content.return_value = [b"x" * MIN_SIZE_VIDEO_AUDIO]
    session.get.return_value = r
    count = _download_videos(["http://example.com/video.mp4"], dest, session)
    assert count == 1
    session.get.assert_called_once()


def test_download_audios_redownloads_partial_file(tmp_path):
    dest = tmp_path / "audios"
    dest.mkdir()
    out = dest / "audio.mp3"
    out.write_bytes(b"x" * 100)
    session = MagicMock()
    r = MagicMock()
    r.headers = {}
    r.iter_content.return_value = [b"x" * MIN_SIZE_VIDEO_AUDIO]
    session.get.return_value = r
    count = _download_audios(["http://example.com/audio.mp3"], dest, session)
    assert count == 1
    session.get.assert_called_once()
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `pytest scraper_app/tests/test_progress.py::test_download_files_redownloads_partial_file -v`
Expected: FAIL (count == 0, pas de re-téléchargement)

- [ ] **Step 3: Ajouter l'import dans `crawler.py`**

Après les imports existants en haut de `crawler.py`, ajouter :

```python
from .session import is_partial, MIN_SIZE_VIDEO_AUDIO, MIN_SIZE_DOC_ARCHIVE
```

- [ ] **Step 4: Modifier `_download_files()` — remplacer le bloc `if out.exists():` (ligne ~239)**

Remplacer :
```python
            if out.exists():
                seen.add(url)
                continue
```

Par :
```python
            if out.exists():
                if is_partial(out, content_length=None, min_size=MIN_SIZE_DOC_ARCHIVE):
                    out.unlink()
                else:
                    seen.add(url)
                    continue
```

- [ ] **Step 5: Modifier `_download_videos()` — remplacer le bloc `if out.exists():` (ligne ~146)**

Remplacer :
```python
            if out.exists():
                if not progress:
                    print(f"    [skip] {fname} (déjà téléchargé)")
                video_urls_seen.add(canonical)
                continue
```

Par :
```python
            if out.exists():
                if is_partial(out, content_length=None, min_size=MIN_SIZE_VIDEO_AUDIO):
                    out.unlink()
                else:
                    if not progress:
                        print(f"    [skip] {fname} (déjà téléchargé)")
                    video_urls_seen.add(canonical)
                    continue
```

- [ ] **Step 6: Modifier `_download_audios()` — remplacer le bloc `if out.exists():` (ligne ~194)**

Remplacer :
```python
            if out.exists():
                if not progress:
                    print(f"    [skip] {fname} (déjà téléchargé)")
                audio_urls_seen.add(url)
                continue
```

Par :
```python
            if out.exists():
                if is_partial(out, content_length=None, min_size=MIN_SIZE_VIDEO_AUDIO):
                    out.unlink()
                else:
                    if not progress:
                        print(f"    [skip] {fname} (déjà téléchargé)")
                    audio_urls_seen.add(url)
                    continue
```

- [ ] **Step 7: Vérifier que tous les tests passent**

Run: `pytest scraper_app/tests/ -v`
Expected: tous PASS

- [ ] **Step 8: Commit**

```bash
git add scraper_app/scraper_modules/crawler.py scraper_app/tests/test_progress.py
git commit -m "feat: detect and re-download partial files in download functions"
```

---

### Task 4: `crawler.py` — sauvegarde de session dans `crawl()`

**Files:**
- Modify: `scraper_app/scraper_modules/crawler.py`
- Modify: `scraper_app/tests/test_progress.py`

- [ ] **Step 1: Ajouter les tests failing**

Append to `scraper_app/tests/test_progress.py` :

```python
from scraper_modules.crawler import crawl


def test_crawl_saves_session_after_page(tmp_path):
    session = MagicMock()
    r = MagicMock()
    r.url = "http://example.com/"
    r.text = "<html><body>Hello</body></html>"
    session.get.return_value = r

    sessions_dir = tmp_path / "sessions"
    session_data = {
        "url": "http://example.com/",
        "dest": str(tmp_path),
        "modes": [1],
        "completed": False,
        "visited": [],
        "started_at": "2026-05-07T100000",
        "completed_at": None,
    }

    crawl(
        url="http://example.com/",
        modes=[1],
        dest=tmp_path,
        depth=0,
        session=session,
        visited=set(),
        session_data=session_data,
        sessions_dir=sessions_dir,
    )

    assert "http://example.com/" in session_data["visited"]
    assert sessions_dir.exists()
    assert len(list(sessions_dir.glob("*.json"))) == 1


def test_crawl_skips_visited_urls(tmp_path):
    session = MagicMock()
    crawl(
        url="http://example.com/",
        modes=[1],
        dest=tmp_path,
        depth=0,
        session=session,
        visited={"http://example.com/"},
    )
    session.get.assert_not_called()
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `pytest scraper_app/tests/test_progress.py::test_crawl_saves_session_after_page -v`
Expected: FAIL avec `TypeError: crawl() got an unexpected keyword argument 'session_data'`

- [ ] **Step 3: Ajouter `session_data` et `sessions_dir` à la signature de `crawl()`**

Dans la signature de `crawl()`, après `task_url=None,`, ajouter :

```python
    session_data: dict | None = None,
    sessions_dir=None,
```

- [ ] **Step 4: Sauvegarder la session après `visited.add(url)` dans `crawl()`**

Juste après le bloc `if progress and task_url is not None:` (ligne ~422-425), ajouter :

```python
    if session_data is not None:
        session_data['visited'] = list(visited)
        from .session import save_session, SESSIONS_DIR as _SD
        save_session(session_data, sessions_dir if sessions_dir is not None else _SD)
```

- [ ] **Step 5: Propager les nouveaux params dans l'appel récursif**

Dans l'appel récursif à `crawl()` en fin de fonction (ligne ~571), ajouter en fin de l'appel :

```python
                      session_data=session_data, sessions_dir=sessions_dir)
```

- [ ] **Step 6: Vérifier que tous les tests passent**

Run: `pytest scraper_app/tests/ -v`
Expected: tous PASS

- [ ] **Step 7: Commit**

```bash
git add scraper_app/scraper_modules/crawler.py scraper_app/tests/test_progress.py
git commit -m "feat: save session state in crawl() after each page visit"
```

---

### Task 5: `scraper.py` — intégration session complète

**Files:**
- Modify: `scraper_app/scraper.py`

- [ ] **Step 1: Ajouter les imports**

Après `from scraper_modules.progress import make_progress`, ajouter :

```python
from datetime import datetime
from scraper_modules.session import (load_session, save_session, is_partial,
                                      MIN_SIZE_VIDEO_AUDIO, MIN_SIZE_DOC_ARCHIVE)
```

- [ ] **Step 2: Ajouter `session_data` et `initial_visited` à `_handle_general()`**

Remplacer la signature de `_handle_general` :
```python
def _handle_general(url: str, dest: Path, session: requests.Session,
                    pw_cookies: list | None = None,
                    progress=None, task_url=None):
```

Par :
```python
def _handle_general(url: str, dest: Path, session: requests.Session,
                    pw_cookies: list | None = None,
                    progress=None, task_url=None,
                    session_data: dict | None = None,
                    initial_visited: set | None = None):
```

- [ ] **Step 3: Mettre à jour `session_data['modes']` et passer les params à `crawl()` dans `_handle_general()`**

Juste après `modes = _ask_modes(...)` dans `_handle_general`, ajouter :

```python
    if session_data is not None:
        session_data['modes'] = sorted(modes)
        save_session(session_data)
```

Dans l'appel à `_crawler.crawl()`, remplacer `visited=set()` par `visited=initial_visited or set()` et ajouter `session_data=session_data` :

```python
        _crawler.crawl(url=url, modes=content_modes, dest=dest, depth=depth,
                       session=session, visited=initial_visited or set(),
                       use_playwright=(engine == 2), playwright_opts=playwright_opts,
                       url_filter=url_filter,
                       img_ext_filter=img_ext_filter, vid_ext_filter=vid_ext_filter,
                       aud_ext_filter=aud_ext_filter,
                       doc_ext_filter=doc_ext_filter, arc_ext_filter=arc_ext_filter,
                       respect_robots=respect_robots,
                       progress=progress, task_url=task_url,
                       session_data=session_data)
```

- [ ] **Step 4: Dans `main()`, ajouter la logique de session avant `task_url = None`**

Dans le `for url in urls:`, après `url_dest.mkdir(parents=True, exist_ok=True)` et avant `progress.console.print(...)`, insérer :

```python
                existing_session = load_session(url)
                initial_visited: set = set()
                session_data: dict | None = None
                skip_crawl = False

                if existing_session and existing_session.get('completed'):
                    partials_found = 0
                    for subdir, min_sz in [
                        ('videos', MIN_SIZE_VIDEO_AUDIO), ('audios', MIN_SIZE_VIDEO_AUDIO),
                        ('documents', MIN_SIZE_DOC_ARCHIVE), ('archives', MIN_SIZE_DOC_ARCHIVE),
                    ]:
                        d = url_dest / subdir
                        if d.exists():
                            for f in d.iterdir():
                                if f.is_file() and is_partial(f, None, min_sz):
                                    f.unlink()
                                    partials_found += 1
                                    (progress.console.print if progress else print)(
                                        f"  ♻ Partiel supprimé : {f.name}")
                    if partials_found == 0:
                        (progress.console.print if progress else print)(
                            f"  ✓ {netloc} — déjà traité, aucun partiel")
                        skip_crawl = True
                    else:
                        existing_session = None

                elif existing_session and not existing_session.get('completed'):
                    initial_visited = set(existing_session.get('visited', []))
                    (progress.console.print if progress else print)(
                        f"  ♻ Reprise depuis {existing_session['started_at']} "
                        f"({len(initial_visited)} pages déjà visitées)")
                    session_data = existing_session

                if session_data is None and not skip_crawl:
                    session_data = {
                        'url': url,
                        'dest': str(url_dest),
                        'modes': [],
                        'completed': False,
                        'visited': [],
                        'started_at': datetime.now().isoformat(timespec='seconds'),
                        'completed_at': None,
                    }
                    save_session(session_data)
```

- [ ] **Step 5: Modifier le bloc `try:` pour gérer `skip_crawl`, marquer `completed` et sauvegarder dans `finally:`**

Remplacer le bloc `task_url = None` + `try:` + `except:` + `finally:` (lignes 678-724) par :

```python
                task_url = None
                try:
                    task_url = progress.add_task(f"{netloc} — 0 pages visitées", total=None)

                    if not skip_crawl:
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

                        if url_type == 'mediawiki':
                            _handle_mediawiki(url, url_dest, session,
                                              progress=progress, task_url=task_url)
                        elif url_type == 'github':
                            _handle_github(url, url_dest, session)
                        elif url_type == 'js':
                            _handle_js(url, url_dest, session,
                                       pw_cookies=pw_cookies, progress=progress, task_url=task_url)
                        else:
                            _handle_general(url, url_dest, session,
                                            pw_cookies=pw_cookies,
                                            progress=progress, task_url=task_url,
                                            session_data=session_data,
                                            initial_visited=initial_visited)

                        if session_data is not None:
                            session_data['completed'] = True
                            session_data['completed_at'] = datetime.now().isoformat(timespec='seconds')
                            save_session(session_data)

                        open_folder(url_dest)

                except KeyboardInterrupt:
                    progress.console.print('\n  Interrompu (Ctrl+C).')
                except Exception as e:
                    progress.console.print(f'\n  ❌ Erreur : {e}')
                finally:
                    if session_data is not None and not session_data.get('completed'):
                        save_session(session_data)
                    if task_url is not None:
                        progress.update(task_url, visible=False)
                    progress.advance(task_global)
```

- [ ] **Step 6: Tester manuellement les 4 scénarios clés**

**Scénario 1 — Premier run :**
```
python scraper_app/scraper.py
# URL: https://example.com, mode 1, depth 0
# Attendu : scraper_app/sessions/*.json créé avec completed: true
```

**Scénario 2 — Re-run URL complète :**
```
python scraper_app/scraper.py
# Même URL
# Attendu : "✓ example.com — déjà traité, aucun partiel"
```

**Scénario 3 — Reprise après Ctrl+C :**
```
python scraper_app/scraper.py
# URL avec depth 1 → Ctrl+C
# Vérifier : sessions/*.json avec completed: false
# Relancer → Attendu : "♻ Reprise depuis ... (N pages déjà visitées)"
```

**Scénario 4 — Fichier partiel :**
```
# Créer manuellement un fichier de 10 octets dans videos/ d'une URL terminée
# Relancer → Attendu : "♻ Partiel supprimé : filename.mp4"
```

- [ ] **Step 7: Vérifier que toute la suite de tests passe**

Run: `pytest scraper_app/tests/ -v`
Expected: tous PASS

- [ ] **Step 8: Commit**

```bash
git add scraper_app/scraper.py
git commit -m "feat: integrate session resume into scraper CLI — skip completed URLs, resume interrupted crawls, detect partial files"
```
