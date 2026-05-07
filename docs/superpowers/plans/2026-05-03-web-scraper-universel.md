# Web Scraper Universel — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer un script interactif universel qui remplace RAW_WEB.py, download_url.py et scrape_fandom.py en un seul outil capable de scraper n'importe quelle URL.

**Architecture:** Point d'entrée `scraper.py` qui détecte le type d'URL et pose des questions adaptées, délègue à des modules spécialisés (`detector`, `downloader`, `mediawiki`, `crawler`, `exporter`). Pas de TDD — implémentation directe, script utilitaire.

**Tech Stack:** Python 3.10+, `requests`, `beautifulsoup4`, `playwright` (optionnel)

---

## Structure des fichiers

```
Scripts_Python/scraper/
├── scraper.py                        ← point d'entrée interactif
└── scraper_modules/
    ├── __init__.py                   ← vide
    ├── detector.py                   ← détecte le type d'URL
    ├── downloader.py                 ← fetch HTTP + Playwright
    ├── mediawiki.py                  ← wikitext brut + API structurée
    ├── crawler.py                    ← crawl général + MediaWiki + GitHub
    └── exporter.py                   ← sauvegarde txt/html/json/csv/images
```

---

## Task 1 : Structure du projet + `exporter.py`

**Files:**
- Create: `Scripts_Python/scraper/scraper_modules/__init__.py`
- Create: `Scripts_Python/scraper/scraper_modules/exporter.py`

- [ ] **Créer le dossier et `__init__.py` vide**

```
Scripts_Python/scraper/scraper_modules/__init__.py  ← fichier vide
```

- [ ] **Créer `exporter.py`**

```python
# scraper_modules/exporter.py
import os, json, csv, re, subprocess, sys
from pathlib import Path

DEFAULT_DEST = Path.home() / "Downloads"


def safe_name(url: str) -> str:
    name = re.split(r'[/=]', url.rstrip('/'))[-1] or "page"
    return re.sub(r'[\\/*?:"<>|]', '_', name)[:80]


def unique_path(folder: Path, filename: str) -> Path:
    path = folder / filename
    stem, suffix = Path(filename).stem, Path(filename).suffix
    i = 1
    while path.exists():
        path = folder / f"{stem}_{i}{suffix}"
        i += 1
    return path


def save_text(content: str, folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = unique_path(folder, filename)
    path.write_text(content, encoding='utf-8')
    return path


def save_bytes(content: bytes, folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = unique_path(folder, filename)
    path.write_bytes(content)
    return path


def save_json(data: dict | list, folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = unique_path(folder, filename)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def save_csv(data: list[dict], folder: Path, filename: str) -> Path | None:
    if not data:
        return None
    folder.mkdir(parents=True, exist_ok=True)
    path = unique_path(folder, filename)
    # Collecte toutes les clés, aplatit l'infobox si présente
    keys: set[str] = set()
    for item in data:
        keys.update(k for k in item if k != 'infobox')
        keys.update(item.get('infobox', {}).keys())
    fieldnames = sorted(keys)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for item in data:
            row = {k: v for k, v in item.items() if k != 'infobox'}
            row.update(item.get('infobox', {}))
            writer.writerow(row)
    return path


def open_folder(folder: Path):
    if sys.platform == 'win32':
        os.startfile(str(folder))
    elif sys.platform == 'darwin':
        subprocess.run(['open', str(folder)])
    else:
        subprocess.run(['xdg-open', str(folder)])
```

- [ ] **Commit**

```
git add scraper/scraper_modules/__init__.py scraper/scraper_modules/exporter.py
git commit -m "feat: add scraper project structure and exporter module"
```

---

## Task 2 : `detector.py` + `downloader.py`

**Files:**
- Create: `Scripts_Python/scraper/scraper_modules/detector.py`
- Create: `Scripts_Python/scraper/scraper_modules/downloader.py`

- [ ] **Créer `detector.py`**

```python
# scraper_modules/detector.py
from urllib.parse import urlparse

MEDIAWIKI_DOMAINS = {
    'wikipedia.org', 'wikimedia.org', 'wiktionary.org',
    'uesp.net', 'fandom.com', 'wikia.com', 'minecraft.wiki',
    'terraria.wiki.gg', 'zelda.wiki.gg', 'wowpedia.fandom.com',
}
MEDIAWIKI_PATHS = ('/wiki/', '/w/index.php')


def detect(url: str) -> str:
    """Retourne : 'mediawiki' | 'github' | 'js' | 'general'"""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if 'github.com' in host:
        return 'github'

    for domain in MEDIAWIKI_DOMAINS:
        if domain in host:
            return 'mediawiki'

    for marker in MEDIAWIKI_PATHS:
        if marker in path:
            return 'mediawiki'

    return 'general'


def is_js_heavy(url: str) -> bool:
    """Heuristique légère : page HTML quasi-vide → probablement une SPA JS."""
    try:
        import requests
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if 'text/html' in resp.headers.get('Content-Type', ''):
            return len(resp.text.strip()) < 1500
    except Exception:
        pass
    return False
```

- [ ] **Créer `downloader.py`**

```python
# scraper_modules/downloader.py
import re, time, mimetypes
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}
TIMEOUT = 20

IMAGE_EXTS = {
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
    '.bmp', '.ico', '.tga', '.avif',
}
ASSET_EXTS = IMAGE_EXTS | {
    '.css', '.js', '.pdf', '.txt', '.json', '.xml',
    '.mp3', '.mp4', '.zip', '.woff', '.woff2', '.ttf', '.otf',
}


def fetch(url: str, session: requests.Session = None) -> requests.Response:
    s = session or requests.Session()
    resp = s.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    return soup.get_text(separator='\n', strip=True)


def extract_structured(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.strip() if soup.title else ''
    headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4'])]
    paragraphs = [
        p.get_text(strip=True) for p in soup.find_all('p')
        if len(p.get_text(strip=True)) > 30
    ]
    images = list({urljoin(url, img['src']) for img in soup.find_all('img', src=True)})
    return {
        'url': url,
        'title': title,
        'headings': headings[:20],
        'paragraphs': paragraphs[:15],
        'images': images[:30],
    }


def extract_image_urls(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, 'html.parser')
    urls: set[str] = set()
    for img in soup.find_all('img', src=True):
        urls.add(urljoin(base_url, img['src']))
    for source in soup.find_all('source', srcset=True):
        for part in source['srcset'].split(','):
            src = part.strip().split()[0]
            if src:
                urls.add(urljoin(base_url, src))
    return [u for u in urls if Path(urlparse(u).path).suffix.lower() in IMAGE_EXTS]


def download_assets(html: str, base_url: str, dest: Path, session: requests.Session):
    """Télécharge CSS, JS et images liés à la page dans dest/."""
    soup = BeautifulSoup(html, 'html.parser')
    asset_urls: set[str] = set()
    for tag in soup.find_all(['img', 'script', 'link', 'source']):
        src = tag.get('src') or tag.get('href')
        if src:
            asset_urls.add(urljoin(base_url, src))
    dest.mkdir(parents=True, exist_ok=True)
    for url in asset_urls:
        ext = Path(urlparse(url).path).suffix.lower()
        if ext not in ASSET_EXTS:
            continue
        try:
            r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            fname = re.sub(r'[\\/*?:"<>|]', '_', Path(urlparse(url).path).name or 'asset')
            (dest / fname).write_bytes(r.content)
            time.sleep(0.2)
        except Exception:
            pass


def fetch_playwright(
    url: str,
    wait_selector: str = None,
    delay: int = 2,
    viewport: tuple = (1280, 720),
) -> str:
    """Retourne le HTML de la page après exécution du JavaScript."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "Playwright n'est pas installé.\n"
            "Exécutez : pip install playwright && python -m playwright install chromium"
        )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': viewport[0], 'height': viewport[1]})
        page.goto(url, wait_until='networkidle', timeout=30000)
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=10000)
        if delay > 0:
            page.wait_for_timeout(delay * 1000)
        html = page.content()
        browser.close()
    return html


def screenshot_playwright(
    url: str,
    dest: Path,
    wait_selector: str = None,
    delay: int = 2,
    viewport: tuple = (1280, 720),
) -> Path:
    """Prend un screenshot pleine page avec Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "Playwright n'est pas installé.\n"
            "Exécutez : pip install playwright && python -m playwright install chromium"
        )
    dest.mkdir(parents=True, exist_ok=True)
    fname = re.sub(r'[\\/*?:"<>|]', '_', Path(urlparse(url).path).name or 'page') + '.png'
    out_path = dest / fname
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': viewport[0], 'height': viewport[1]})
        page.goto(url, wait_until='networkidle', timeout=30000)
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=10000)
        if delay > 0:
            page.wait_for_timeout(delay * 1000)
        page.screenshot(path=str(out_path), full_page=True)
        browser.close()
    return out_path
```

- [ ] **Commit**

```
git add scraper/scraper_modules/detector.py scraper/scraper_modules/downloader.py
git commit -m "feat: add URL detector and HTTP/Playwright downloader"
```

---

## Task 3 : `mediawiki.py`

**Files:**
- Create: `Scripts_Python/scraper/scraper_modules/mediawiki.py`

- [ ] **Créer `mediawiki.py`**

```python
# scraper_modules/mediawiki.py
import re, time
from urllib.parse import urlparse, unquote

import requests
from bs4 import BeautifulSoup

from .downloader import HEADERS, TIMEOUT


def detect_api_url(page_url: str) -> str:
    parsed = urlparse(page_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path
    if '/wiki/' in path:
        return f"{base}/api.php"
    if '/w/' in path:
        return f"{base}/w/api.php"
    return f"{base}/api.php"


def extract_title(page_url: str) -> str:
    parsed = urlparse(page_url)
    path = parsed.path
    for prefix in ('/wiki/', '/w/'):
        if prefix in path:
            return unquote(path.split(prefix, 1)[1].replace('_', ' '))
    return unquote(path.rstrip('/').split('/')[-1].replace('_', ' '))


def fetch_wikitext(page_url: str) -> str:
    """Récupère le wikitext brut d'une page MediaWiki."""
    parsed = urlparse(page_url)
    if '/wiki/' in parsed.path:
        raw_url = page_url.replace('/wiki/', '/w/index.php?title=') + '&action=raw'
    elif 'index.php' in parsed.path:
        raw_url = page_url + ('&action=raw' if 'action=raw' not in page_url else '')
    else:
        raw_url = page_url

    try:
        resp = requests.get(raw_url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        content = resp.text
    except requests.HTTPError as e:
        if e.response.status_code == 404 and '/w/' in raw_url:
            raw_url = raw_url.replace('/w/', '/wiki/')
            resp = requests.get(raw_url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            content = resp.text
        else:
            raise

    # Suit les redirections internes MediaWiki (#REDIRECT [[Titre]])
    match = re.match(r'#REDIRECT\s*\[\[(.*?)\]\]', content, re.IGNORECASE)
    if match:
        new_title = match.group(1).strip().replace(' ', '_')
        base = raw_url.split('index.php')[0]
        raw_url = f"{base}index.php?title={new_title}&action=raw"
        resp = requests.get(raw_url, headers=HEADERS, timeout=TIMEOUT)
        content = resp.text

    return content


def _api_get(api_url: str, params: dict, session: requests.Session) -> dict:
    params.setdefault('format', 'json')
    params.setdefault('formatversion', '2')
    resp = session.get(api_url, params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_structured(page_url: str, session: requests.Session) -> dict:
    """Extrait infobox, description et images via l'API MediaWiki officielle."""
    api_url = detect_api_url(page_url)
    title = extract_title(page_url)

    data = _api_get(api_url, {
        'action': 'parse',
        'page': title,
        'prop': 'text|images|displaytitle',
    }, session)

    parse = data.get('parse', {})
    if not parse:
        return {}

    html = parse.get('text', '')
    soup = BeautifulSoup(html, 'html.parser')
    parsed_api = urlparse(api_url)
    base = f"{parsed_api.scheme}://{parsed_api.netloc}"

    result = {
        'title': re.sub(r'<[^>]+>', '', parse.get('displaytitle') or title),
        'url': f"{base}/wiki/{title.replace(' ', '_')}",
        'infobox': {},
        'description': '',
        'images': [],
    }

    # Infobox portable (Fandom moderne)
    aside = soup.find('aside', class_=lambda x: x and 'portable-infobox' in x)
    if aside:
        infobox: dict[str, str] = {}
        title_el = aside.find(class_=lambda x: x and 'pi-title' in x)
        if title_el:
            infobox['_name'] = title_el.get_text(strip=True)
        for item in aside.find_all(class_=lambda x: x and 'pi-data' in x):
            label = item.find(class_=lambda x: x and 'pi-data-label' in x)
            value = item.find(class_=lambda x: x and 'pi-data-value' in x)
            if label and value:
                infobox[label.get_text(strip=True)] = value.get_text(' ', strip=True)
        result['infobox'] = infobox

    # Fallback wikitable classique
    if not result['infobox']:
        table = soup.find('table', class_=lambda x: x and 'infobox' in x)
        if table:
            infobox = {}
            for row in table.find_all('tr'):
                cells = row.find_all(['th', 'td'])
                if len(cells) == 2:
                    k = cells[0].get_text(strip=True)
                    v = cells[1].get_text(' ', strip=True)
                    if k and v:
                        infobox[k] = v
            result['infobox'] = infobox

    # Description (premier paragraphe substantiel)
    content_div = soup.find(class_=lambda x: x and 'mw-parser-output' in x)
    if content_div:
        for tag in content_div.find_all(['aside', 'table', 'script', 'style']):
            tag.decompose()
        paras = [p.get_text(' ', strip=True) for p in content_div.find_all('p')
                 if len(p.get_text(strip=True)) > 30]
        if paras:
            result['description'] = paras[0]

    # Image principale
    img_names = [n for n in parse.get('images', [])
                 if n.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'))]
    if img_names:
        img_url = _resolve_image(api_url, img_names[0], session)
        if img_url:
            result['images'].append(img_url)

    return result


def _resolve_image(api_url: str, filename: str, session: requests.Session) -> str:
    data = _api_get(api_url, {
        'action': 'query',
        'titles': f'File:{filename}',
        'prop': 'imageinfo',
        'iiprop': 'url',
        'iilimit': '1',
    }, session)
    for page in data.get('query', {}).get('pages', []):
        info = page.get('imageinfo', [])
        if info:
            return info[0].get('url', '')
    return ''


def get_links(api_url: str, title: str, session: requests.Session, title_filter: str = '') -> list[str]:
    """Retourne les titres des pages liées (namespace 0 seulement)."""
    SKIP = ('Special:', 'Talk:', 'User:', 'File:', 'Template:', 'Help:', 'Category:')
    links: list[str] = []
    params = {
        'action': 'query',
        'titles': title,
        'prop': 'links',
        'pllimit': '500',
        'plnamespace': '0',
    }
    while True:
        data = _api_get(api_url, params, session)
        for page in data.get('query', {}).get('pages', []):
            for link in page.get('links', []):
                t = link.get('title', '')
                if t and not any(t.startswith(p) for p in SKIP):
                    if not title_filter or title_filter.lower() in t.lower():
                        links.append(t)
        cont = data.get('continue', {})
        if 'plcontinue' not in cont:
            break
        params['plcontinue'] = cont['plcontinue']
        time.sleep(0.4)
    return links
```

- [ ] **Commit**

```
git add scraper/scraper_modules/mediawiki.py
git commit -m "feat: add MediaWiki module (wikitext + structured API)"
```

---

## Task 4 : `crawler.py`

**Files:**
- Create: `Scripts_Python/scraper/scraper_modules/crawler.py`

- [ ] **Créer `crawler.py`**

```python
# scraper_modules/crawler.py
import re, time
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from .downloader import (fetch, extract_text, extract_structured,
                         extract_image_urls, download_assets, HEADERS, TIMEOUT)
from .exporter import save_text, save_json, save_csv, save_bytes


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', '_', name)[:80]


def _base_name(url: str) -> str:
    return _safe(urlparse(url).path.rstrip('/').split('/')[-1] or 'page')


def _extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, 'html.parser')
    links: set[str] = set()
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith(('#', 'javascript:', 'mailto:')):
            continue
        full = urljoin(base_url, href).split('#')[0]
        if full.startswith('http'):
            links.add(full)
    return list(links)


def _same_domain(url: str, base: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


def _download_images(img_urls: list[str], dest: Path, session: requests.Session) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for img_url in img_urls:
        try:
            r = session.get(img_url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            fname = _safe(Path(urlparse(img_url).path).name or 'img')
            (dest / fname).write_bytes(r.content)
            count += 1
            time.sleep(0.2)
        except Exception:
            pass
    return count


# ── Crawl général ─────────────────────────────────────────────────────────────

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
):
    if url in visited or current_depth > depth:
        return
    visited.add(url)

    try:
        if use_playwright:
            from .downloader import fetch_playwright
            html = fetch_playwright(url, **(playwright_opts or {}))
        else:
            resp = fetch(url, session)
            html = resp.text
    except Exception as e:
        print(f"  ✗ {url} : {e}")
        return

    name = _base_name(url)

    for mode in modes:
        if mode == 1:
            path = save_text(extract_text(html), dest, f"{name}.txt")
            print(f"  ✅ {path.name}")

        elif mode == 2:
            path = save_text(html, dest, f"{name}.html")
            print(f"  ✅ {path.name}")

        elif mode == 3:
            folder = dest / name
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'index.html').write_text(html, encoding='utf-8')
            download_assets(html, url, folder, session)
            print(f"  ✅ Dossier {folder.name}/")

        elif mode == 4:
            path = save_json(extract_structured(html, url), dest, f"{name}.json")
            print(f"  ✅ {path.name}")

        elif mode == 5:
            img_urls = extract_image_urls(html, url)
            count = _download_images(img_urls, dest / f"{name}_images", session)
            print(f"  ✅ {count} image(s) → {name}_images/")

    if current_depth < depth:
        for child_url in _extract_links(html, url):
            if child_url not in visited and _same_domain(child_url, url):
                time.sleep(delay)
                crawl(url=child_url, modes=modes, dest=dest, depth=depth,
                      session=session, visited=visited, delay=delay,
                      current_depth=current_depth + 1,
                      use_playwright=use_playwright, playwright_opts=playwright_opts)


# ── Crawl MediaWiki ───────────────────────────────────────────────────────────

def crawl_mediawiki(
    page_url: str,
    modes: list[int],
    dest: Path,
    depth: int,
    session: requests.Session,
    visited_titles: set,
    title_filter: str = '',
    do_csv: bool = False,
    delay: float = 0.4,
    current_depth: int = 0,
    _all_structured: list | None = None,
):
    from .mediawiki import (detect_api_url, extract_title, fetch_wikitext,
                            fetch_structured, get_links)

    title = extract_title(page_url)
    if title in visited_titles:
        return
    visited_titles.add(title)

    if _all_structured is None:
        _all_structured = []

    api_url = detect_api_url(page_url)
    safe = _safe(title.replace(' ', '_'))
    page_dest = dest / safe
    page_dest.mkdir(parents=True, exist_ok=True)

    indent = '  ' * current_depth
    print(f"{indent}[→] {title}")

    for mode in modes:
        try:
            if mode == 1:
                wikitext = fetch_wikitext(page_url)
                path = save_text(wikitext, page_dest, f"{safe}.txt")
                print(f"{indent}  ✅ Wikitext: {path.name}")

            elif mode == 2:
                data = fetch_structured(page_url, session)
                if data:
                    path = save_json(data, page_dest, f"{safe}.json")
                    print(f"{indent}  ✅ JSON: {path.name}")
                    _all_structured.append(data)

            elif mode == 3:
                resp = fetch(page_url, session)
                path = save_text(resp.text, page_dest, f"{safe}.html")
                print(f"{indent}  ✅ HTML: {path.name}")

            elif mode == 4:
                resp = fetch(page_url, session)
                path = save_text(extract_text(resp.text), page_dest, f"{safe}.txt")
                print(f"{indent}  ✅ Texte: {path.name}")

            elif mode == 5:
                resp = fetch(page_url, session)
                img_urls = extract_image_urls(resp.text, page_url)
                count = _download_images(img_urls, page_dest / 'images', session)
                print(f"{indent}  ✅ {count} image(s)")

        except Exception as e:
            print(f"{indent}  ✗ Mode {mode}: {e}")

    time.sleep(delay)

    if current_depth < depth:
        children = sorted(set(get_links(api_url, title, session, title_filter)) - visited_titles)
        print(f"{indent}  ↪ {len(children)} liens")
        parsed_api = urlparse(api_url)
        base = f"{parsed_api.scheme}://{parsed_api.netloc}"
        for child_title in children:
            child_url = f"{base}/wiki/{child_title.replace(' ', '_')}"
            time.sleep(delay)
            crawl_mediawiki(
                page_url=child_url, modes=modes, dest=dest, depth=depth,
                session=session, visited_titles=visited_titles,
                title_filter=title_filter, do_csv=do_csv, delay=delay,
                current_depth=current_depth + 1, _all_structured=_all_structured,
            )

    # Export CSV global une seule fois (au niveau racine)
    if current_depth == 0 and do_csv and _all_structured:
        csv_path = save_csv(_all_structured, dest, 'all.csv')
        if csv_path:
            print(f"  📊 CSV → {csv_path.name}")


# ── Crawl GitHub ──────────────────────────────────────────────────────────────

def crawl_github(
    url: str,
    dest: Path,
    depth: int,
    session: requests.Session,
    ext_filter: list[str] | None = None,
):
    parsed = urlparse(url)
    parts = parsed.path.strip('/').split('/')
    if len(parts) < 2:
        print(f"  ✗ URL GitHub invalide: {url}")
        return

    owner, repo = parts[0], parts[1]
    if len(parts) > 3 and parts[2] in ('tree', 'blob'):
        branch = parts[3]
        sub_path = '/'.join(parts[4:]) if len(parts) > 4 else ''
    else:
        branch = 'main'
        sub_path = ''

    _github_dir(owner, repo, branch, sub_path, dest / owner / repo,
                depth, 0, session, ext_filter or [])


def _github_dir(owner, repo, branch, path, dest, max_depth, current_depth, session, ext_filter):
    if current_depth > max_depth:
        return

    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    resp = None
    for br in [branch, 'main', 'master']:
        resp = session.get(api_url, params={'ref': br}, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            break
        if resp.status_code != 404:
            print(f"  ✗ GitHub API {resp.status_code}")
            return

    if resp is None or resp.status_code != 200:
        print(f"  ✗ Repo inaccessible")
        return

    entries = resp.json()
    if not isinstance(entries, list):
        entries = [entries]

    for entry in entries:
        if entry.get('type') == 'file' and entry.get('download_url'):
            name = entry.get('name', 'file')
            if ext_filter and not any(name.endswith(e) for e in ext_filter):
                continue
            out = dest / _safe(name)
            dest.mkdir(parents=True, exist_ok=True)
            if out.exists():
                print(f"  [skip] {name}")
                continue
            try:
                r = session.get(entry['download_url'], headers=HEADERS, timeout=TIMEOUT)
                r.raise_for_status()
                out.write_bytes(r.content)
                print(f"  ✅ {name}")
                time.sleep(0.2)
            except Exception as e:
                print(f"  ✗ {name}: {e}")

        elif entry.get('type') == 'dir' and current_depth < max_depth:
            print(f"  [dir] {entry['name']}/")
            _github_dir(owner, repo, branch, entry['path'],
                        dest / _safe(entry['name']),
                        max_depth, current_depth + 1, session, ext_filter)
```

- [ ] **Commit**

```
git add scraper/scraper_modules/crawler.py
git commit -m "feat: add crawler for general sites, MediaWiki and GitHub"
```

---

## Task 5 : `scraper.py` — point d'entrée interactif

**Files:**
- Create: `Scripts_Python/scraper/scraper.py`

- [ ] **Créer `scraper.py`**

```python
"""
scraper.py — Web Scraper Universel
Remplace : RAW_WEB.py, download_url.py, scrape_fandom.py
Dépendances : pip install requests beautifulsoup4
Playwright (optionnel) : pip install playwright && python -m playwright install chromium
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import requests
from scraper_modules.detector import detect, is_js_heavy
from scraper_modules.exporter import DEFAULT_DEST, open_folder
from scraper_modules import crawler as _crawler

BANNER = """
╔══════════════════════════════════════════════╗
║        🕷   WEB SCRAPER UNIVERSEL   🕷        ║
║  Général · MediaWiki · GitHub · JS-lourd     ║
╚══════════════════════════════════════════════╝"""


# ── Helpers interactifs ───────────────────────────────────────────────────────

def _ask(prompt: str, default: str = '') -> str:
    suffix = f' [{default}]' if default else ''
    val = input(f'{prompt}{suffix} : ').strip()
    return val if val else default


def _ask_bool(prompt: str, default: bool = False) -> bool:
    suffix = '[O/n]' if default else '[o/N]'
    val = input(f'{prompt} {suffix} : ').strip().lower()
    return (val in ('o', 'oui', 'y', 'yes')) if val else default


def _ask_modes(options: list[tuple[int, str]]) -> list[int]:
    print()
    for num, label in options:
        print(f"  [{num}] {label}")
    raw = input('\nMode(s) (ex: 1 ou 1,3) : ').strip()
    selected = []
    for part in raw.split(','):
        try:
            n = int(part.strip())
            if any(o[0] == n for o in options):
                selected.append(n)
        except ValueError:
            pass
    return selected if selected else [options[0][0]]


def _ask_depth() -> int:
    raw = _ask('Profondeur de crawl (0 = page seule, 1 = page + liens, …)', '0')
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _parse_urls(raw: str) -> list[str]:
    raw = raw.strip()
    p = Path(raw)
    if raw.endswith('.txt') and p.exists():
        return [l.strip() for l in p.read_text(encoding='utf-8').splitlines()
                if l.strip() and not l.startswith('#')]
    return [u.strip() for u in raw.split(',') if u.strip()]


# ── Handlers par type ─────────────────────────────────────────────────────────

def _handle_general(url: str, dest: Path, session: requests.Session):
    use_playwright = _ask_bool('Utiliser Playwright (rendu JS) ?', False)
    playwright_opts: dict = {}
    if use_playwright:
        sel = _ask('Attendre un sélecteur CSS (vide = aucun)', '')
        delay = int(_ask("Délai d'attente (secondes)", '2'))
        playwright_opts = {'wait_selector': sel or None, 'delay': delay}

    modes = _ask_modes([
        (1, 'Texte propre (.txt)'),
        (2, 'HTML brut (.html)'),
        (3, 'Téléchargement complet — HTML + assets (dossier)'),
        (4, 'Données structurées — JSON'),
        (5, 'Images seulement (dossier images/)'),
    ])
    depth = _ask_depth()

    print('\n⬇  Scraping en cours...')
    _crawler.crawl(url=url, modes=modes, dest=dest, depth=depth,
                   session=session, visited=set(),
                   use_playwright=use_playwright, playwright_opts=playwright_opts)


def _handle_mediawiki(url: str, dest: Path, session: requests.Session):
    modes = _ask_modes([
        (1, 'Wikitext brut (.txt)'),
        (2, 'Données structurées via API — JSON'),
        (3, 'HTML rendu (.html)'),
        (4, 'Texte propre (.txt)'),
        (5, 'Images seulement (dossier images/)'),
    ])
    depth = _ask_depth()
    title_filter = _ask('Filtre sur les titres (vide = tous)', '') if depth > 0 else ''
    do_csv = _ask_bool('Exporter aussi en CSV ?', False) if 2 in modes else False

    print('\n⬇  Scraping MediaWiki en cours...')
    _crawler.crawl_mediawiki(url, modes=modes, dest=dest, depth=depth,
                              session=session, visited_titles=set(),
                              title_filter=title_filter, do_csv=do_csv)


def _handle_github(url: str, dest: Path, session: requests.Session):
    modes = _ask_modes([
        (1, 'Tout télécharger'),
        (2, 'Filtrer par extension'),
    ])
    depth_raw = _ask('Profondeur dans les sous-dossiers (vide = illimitée)', '')
    depth = int(depth_raw) if depth_raw.isdigit() else 999

    ext_filter: list[str] = []
    if 2 in modes:
        raw = _ask('Extensions séparées par des virgules (ex: .py,.json)', '')
        ext_filter = [e.strip() for e in raw.split(',') if e.strip()]

    print('\n⬇  Téléchargement GitHub en cours...')
    _crawler.crawl_github(url=url, dest=dest, depth=depth,
                           session=session, ext_filter=ext_filter)


def _handle_js(url: str, dest: Path, session: requests.Session):
    from scraper_modules.downloader import (fetch_playwright, screenshot_playwright,
                                             extract_text, extract_structured,
                                             extract_image_urls, HEADERS, TIMEOUT)
    from scraper_modules.exporter import save_text, save_json
    from scraper_modules.crawler import _safe, _download_images
    import time

    modes = _ask_modes([
        (1, 'HTML après rendu JS (.html)'),
        (2, 'Texte propre après rendu JS (.txt)'),
        (3, 'Screenshot (.png)'),
        (4, 'Données structurées après rendu — JSON'),
        (5, 'Images seulement (dossier images/)'),
    ])
    sel = _ask('Attendre un sélecteur CSS (vide = aucun)', '')
    delay = int(_ask("Délai d'attente après chargement (secondes)", '2'))
    vp_raw = _ask('Taille fenêtre (LxH)', '1280x720')
    try:
        w, h = [int(x) for x in vp_raw.lower().split('x')]
    except Exception:
        w, h = 1280, 720

    opts = {'wait_selector': sel or None, 'delay': delay, 'viewport': (w, h)}
    base_name = _safe(url.rstrip('/').split('/')[-1] or 'page')

    print('\n⬇  Chargement Playwright en cours...')
    try:
        if 3 in modes:
            path = screenshot_playwright(url, dest, **opts)
            print(f"  ✅ Screenshot: {path.name}")

        if any(m in modes for m in [1, 2, 4, 5]):
            html = fetch_playwright(url, **opts)

            if 1 in modes:
                path = save_text(html, dest, f"{base_name}.html")
                print(f"  ✅ HTML: {path.name}")
            if 2 in modes:
                path = save_text(extract_text(html), dest, f"{base_name}.txt")
                print(f"  ✅ Texte: {path.name}")
            if 4 in modes:
                path = save_json(extract_structured(html, url), dest, f"{base_name}.json")
                print(f"  ✅ JSON: {path.name}")
            if 5 in modes:
                img_urls = extract_image_urls(html, url)
                count = _download_images(img_urls, dest / f"{base_name}_images", session)
                print(f"  ✅ {count} image(s) → {base_name}_images/")

    except ImportError as e:
        print(f'\n❌ {e}')


# ── Boucle principale ─────────────────────────────────────────────────────────

def main():
    print(BANNER)

    dest_raw = _ask(f'\nDossier de destination', str(DEFAULT_DEST))
    dest = Path(dest_raw)
    dest.mkdir(parents=True, exist_ok=True)

    session = requests.Session()

    while True:
        print()
        raw = input("URL(s), fichier .txt ou 'q'/'exit' : ").strip()

        if raw.lower() in ('q', 'exit', 'quitter', 'quit'):
            print('\nAu revoir !\n')
            break

        if not raw:
            continue

        urls = _parse_urls(raw)
        if not urls:
            print('  ⚠ Aucune URL valide.')
            continue

        for url in urls:
            if not url.startswith('http'):
                url = 'https://' + url

            print(f'\n{"─" * 50}')
            url_type = detect(url)

            # Propose Playwright si la page semble JS-lourde
            if url_type == 'general' and is_js_heavy(url):
                print('  ⚠ Contenu semble généré par JavaScript.')
                if _ask_bool('Passer en mode JS-lourd (Playwright) ?', True):
                    url_type = 'js'

            type_labels = {
                'mediawiki': '🔖 Wiki MediaWiki',
                'github':    '🐙 GitHub',
                'js':        '⚡ Site interactif JS',
                'general':   '🌐 Site général',
            }
            print(f"\n🔍 Détection → {type_labels.get(url_type, url_type)}")

            try:
                if url_type == 'mediawiki':
                    _handle_mediawiki(url, dest, session)
                elif url_type == 'github':
                    _handle_github(url, dest, session)
                elif url_type == 'js':
                    _handle_js(url, dest, session)
                else:
                    _handle_general(url, dest, session)

                open_folder(dest)

            except KeyboardInterrupt:
                print('\n  Interrompu (Ctrl+C).')
            except Exception as e:
                print(f'\n  ❌ Erreur : {e}')


if __name__ == '__main__':
    main()
```

- [ ] **Commit**

```
git add scraper/scraper.py
git commit -m "feat: add interactive entry point (scraper.py) with all URL types"
```

---

## Task 6 : Vérification manuelle + commit final

**Files:** aucun nouveau fichier

- [ ] **Installer les dépendances**

```
pip install requests beautifulsoup4
# Optionnel pour les sites JS :
pip install playwright && python -m playwright install chromium
```

- [ ] **Tester un site général**

```
python scraper.py
# Entrer : https://www.jeuxvideo.com/
# Mode : 1 (texte propre), profondeur : 0
# Vérifier que le .txt est créé dans le dossier de destination
```

- [ ] **Tester un wiki MediaWiki**

```
python scraper.py
# Entrer : https://en.uesp.net/wiki/Skyrim:Alchemy
# Mode : 1,2 (wikitext + JSON), profondeur : 0
# Vérifier .txt et .json créés
```

- [ ] **Tester GitHub**

```
python scraper.py
# Entrer : https://github.com/torvalds/linux
# Mode : 2 (filtrer extensions), .md uniquement, profondeur : 1
# Vérifier les fichiers téléchargés
```

- [ ] **Commit final**

```
git add .
git commit -m "feat: web scraper universel complet — remplace RAW_WEB, download_url, scrape_fandom"
```
