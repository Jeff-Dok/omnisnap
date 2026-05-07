"""
scraper.py — Web Scraper Universel
Remplace : RAW_WEB.py, download_url.py, scrape_fandom.py
Dépendances : pip install requests beautifulsoup4
Playwright (optionnel) : pip install playwright && python -m playwright install chromium
"""
import sys, http.cookiejar
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))

import requests
from scraper_modules.detector import detect, is_js_heavy
from scraper_modules.exporter import DEFAULT_DEST, open_folder, url_to_folder
from scraper_modules import crawler as _crawler
from scraper_modules.progress import make_progress
from datetime import datetime
from scraper_modules.session import (load_session, save_session, is_partial,
                                      MIN_SIZE_VIDEO_AUDIO, MIN_SIZE_DOC_ARCHIVE)

# Bannière sans emoji dans les lignes de bordure (évite le décalage)
BANNER = """
╔═════════════════════════════════════════════╗
║           WEB  SCRAPER  UNIVERSEL           ║
║   General · MediaWiki · GitHub · JS-lourd   ║
╚═════════════════════════════════════════════╝"""


# ── Helpers interactifs ───────────────────────────────────────────────────────

def _ask(prompt: str, default: str = '') -> str:
    suffix = f' [{default}]' if default else ''
    val = input(f'{prompt}{suffix} : ').strip()
    return val if val else default


def _ask_choice(question: str, options: list[tuple[int, str]], default: int = 1) -> int:
    """Affiche des choix numérotés et retourne le numéro sélectionné."""
    print(f'\n{question}')
    for num, label in options:
        print(f"  [{num}] {label}")
    raw = input(f'\n  Choix [{default}] : ').strip()
    try:
        n = int(raw)
        if any(o[0] == n for o in options):
            return n
    except ValueError:
        pass
    return default


def _ask_modes(question: str, options: list[tuple[int, str]]) -> list[int]:
    """Affiche des modes numérotés, accepte une sélection multiple (ex: 1,3)."""
    print(f'\n{question}')
    for num, label in options:
        print(f"  [{num}] {label}")
    raw = input('\n  Mode(s) (ex: 1  ou  1,3  pour plusieurs) : ').strip()
    selected = []
    for part in raw.split(','):
        try:
            n = int(part.strip())
            if any(o[0] == n for o in options):
                selected.append(n)
        except ValueError:
            pass
    return selected if selected else [options[0][0]]


def _ask_ext_filter(
    label: str,
    available: list[tuple[str, list[str], str]],
) -> set[str] | None:
    """Demande quels types de fichiers garder avec sélection numérotée.

    available = [(nom_affiché, ['.ext', ...], description), ...]
    Retourne None = tout garder.
    """
    all_label = '  '.join(name for name, _, _ in available)
    choice = _ask_choice(
        f"Types {label} à télécharger :",
        [
            (1, f"Tous  — {all_label} (recommandé)"),
            (2,  "Choisir — sélectionner par numéro"),
        ],
    )
    if choice == 1:
        return None
    options = [
        (i + 1, f"{name:<14} — {desc}")
        for i, (name, _, desc) in enumerate(available)
    ]
    selected_nums = _ask_modes(
        f"Types {label} à garder (plusieurs choix possibles) :",
        options,
    )
    exts: set[str] = set()
    for n in selected_nums:
        if 1 <= n <= len(available):
            exts.update(available[n - 1][1])
    return exts if exts else None


def _ask_depth() -> int:
    choice = _ask_choice(
        "Profondeur de crawl — combien de niveaux de liens suivre :",
        [
            (0, "Page seule   — télécharge uniquement la page demandée (recommandé)"),
            (1, "+1 niveau    — page + toutes les pages liées depuis cette page"),
            (2, "+2 niveaux   — liens + liens des liens (peut prendre du temps)"),
            (3, "+3 niveaux   — plusieurs dizaines de pages possible"),
            (4, "+4 niveaux   — attention : peut télécharger des centaines de pages"),
            (5, "+5 niveaux   — très large, réserver aux petits sites bien filtrés"),
            (9, "Personnalisé — entrer le nombre de niveaux manuellement"),
        ],
        default=0,
    )
    if choice == 9:
        raw = input("\n  Nombre de niveaux (ex: 6) : ").strip()
        try:
            n = int(raw)
            return max(0, n)
        except ValueError:
            return 0
    return choice


def _ask_playwright_opts() -> dict:
    sel_choice = _ask_choice(
        "Attendre qu'un élément soit chargé avant de capturer ?",
        [
            (1, "Non — capturer dès que la page est prête (recommandé)"),
            (2, "Oui — utile si le contenu principal tarde à apparaître\n"
                "          (ex: tableau de données, carte interactive)"),
        ],
    )
    wait_selector = None
    if sel_choice == 2:
        wait_selector = input("\n  Sélecteur CSS à attendre (ex: #content, .main-table) : ").strip() or None

    delay_choice = _ask_choice(
        "Délai d'attente supplémentaire après le chargement :",
        [
            (1, "2 secondes  — suffisant pour la plupart des sites (recommandé)"),
            (2, "5 secondes  — pour les sites lents ou avec des animations"),
            (3, "Personnalisé"),
        ],
    )
    if delay_choice == 1:
        delay = 2
    elif delay_choice == 2:
        delay = 5
    else:
        try:
            delay = int(input("\n  Délai en secondes : ").strip())
        except ValueError:
            delay = 2

    vp_choice = _ask_choice(
        "Taille de la fenêtre du navigateur :",
        [
            (1, "1280x720   — standard HD (recommandé)"),
            (2, "1920x1080  — Full HD"),
            (3, "390x844    — mobile iPhone"),
            (4, "Personnalisée"),
        ],
    )
    viewports = {1: (1280, 720), 2: (1920, 1080), 3: (390, 844)}
    if vp_choice in viewports:
        viewport = viewports[vp_choice]
    else:
        raw = input("\n  Taille (format LxH, ex: 1280x720) : ").strip()
        try:
            w, h = [int(x) for x in raw.lower().split('x')]
            viewport = (w, h)
        except Exception:
            viewport = (1280, 720)

    return {'wait_selector': wait_selector, 'delay': delay, 'viewport': viewport}


def _load_cookies(session: requests.Session, cookies_path: Path) -> list[dict]:
    """Charge un fichier cookies.txt Netscape dans la session requests.
    Retourne une liste de dicts Playwright [{name, value, domain, path}].
    """
    jar = http.cookiejar.MozillaCookieJar(str(cookies_path))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception as e:
        print(f"  ⚠ Erreur lecture cookies : {e}")
        return []
    session.cookies.update(jar)
    return [
        {'name': c.name, 'value': c.value, 'domain': c.domain, 'path': c.path}
        for c in jar
    ]


def _parse_urls(raw: str) -> list[str]:
    raw = raw.strip()
    p = Path(raw)
    if raw.endswith('.txt') and p.exists():
        return [l.strip() for l in p.read_text(encoding='utf-8').splitlines()
                if l.strip() and not l.startswith('#')]
    return [u.strip() for u in raw.split(',') if u.strip()]


# ── Handlers par type ─────────────────────────────────────────────────────────

def _handle_general(url: str, dest: Path, session: requests.Session,
                    pw_cookies: list | None = None,
                    progress=None, task_url=None,
                    session_data: dict | None = None,
                    initial_visited: set | None = None):
    engine = _ask_choice(
        "Moteur de rendu :",
        [
            (1, "requests   — rapide et léger, fonctionne pour la majorité des sites (recommandé)"),
            (2, "Playwright — simule un vrai navigateur Chrome\n"
                "               nécessaire si la page semble vide avec l'option 1"),
        ],
    )
    playwright_opts: dict = {}
    if engine == 2:
        playwright_opts = _ask_playwright_opts()
    if pw_cookies:
        playwright_opts['cookies'] = pw_cookies

    modes = _ask_modes(
        "Que voulez-vous récupérer ? (plusieurs choix possibles)",
        [
            (1, "Texte propre        — contenu lisible sans le code HTML (.txt)\n"
                "                       idéal pour lire un article ou l'analyser"),
            (2, "HTML brut           — code source complet de la page (.html)\n"
                "                       si vous voulez traiter le HTML vous-même"),
            (3, "Téléchargement complet — HTML + images + CSS + polices (dossier)\n"
                "                       copie locale que vous pouvez ouvrir sans internet"),
            (4, "Données structurées — titre, titres de section, paragraphes, images (.json)\n"
                "                       pratique pour alimenter une base de données"),
            (5, "Images seulement    — toutes les images de la page (jpg, png, svg, webp...)\n"
                "                       sauvegardées dans un sous-dossier images/"),
            (6, "Arborescence URLs   — liste tous les liens de la page avec leur hiérarchie (.txt)\n"
                "                       utile pour cartographier la structure d'un site"),
            (7, "Vidéos              — télécharge les vidéos de la page (mp4, webm...)\n"
                "                       essaie d'abord l'extraction directe, puis yt-dlp"),
            (8, "Audios              — télécharge les fichiers audio de la page (mp3, wav...)\n"
                "                       extraction directe depuis les balises et les scripts"),
            (9, "Documents           — télécharge les fichiers liés (pdf, docx, xlsx...)\n"
                "                       liens directs depuis les balises <a>"),
            (10,"Archives            — télécharge les archives liées (zip, rar, 7z...)\n"
                "                       liens directs depuis les balises <a>"),
            (11,"Screenshot          — capture d'écran de la page telle qu'affichée (.png)\n"
                "                       utilise Playwright — fonctionne même si requests est sélectionné"),
        ],
    )

    if session_data is not None:
        session_data['modes'] = sorted(modes)
        save_session(session_data)

    img_ext_filter: set | None = None
    vid_ext_filter: set | None = None
    aud_ext_filter: set | None = None
    doc_ext_filter: set | None = None
    arc_ext_filter: set | None = None
    if 5 in modes:
        img_ext_filter = _ask_ext_filter("d'images", [
            ('JPG / JPEG', ['.jpg', '.jpeg'], 'photo compressée — le plus courant'),
            ('PNG',        ['.png'],          'image avec transparence'),
            ('GIF',        ['.gif'],          'animation'),
            ('SVG',        ['.svg'],          'graphique vectoriel (logo, icône)'),
            ('WEBP',       ['.webp'],         'format moderne compressé'),
            ('BMP',        ['.bmp'],          'bitmap non compressé'),
            ('ICO',        ['.ico'],          'icône de site'),
            ('AVIF',       ['.avif'],         'format moderne haute qualité'),
        ])
    if 7 in modes:
        vid_ext_filter = _ask_ext_filter("de vidéos", [
            ('MP4',  ['.mp4'],  'le plus universel — recommandé'),
            ('WEBM', ['.webm'], 'format web ouvert'),
            ('MOV',  ['.mov'],  'QuickTime — Apple'),
            ('AVI',  ['.avi'],  'format classique Windows'),
            ('MKV',  ['.mkv'],  'conteneur flexible haute qualité'),
            ('M4V',  ['.m4v'],  'iTunes — Apple'),
            ('FLV',  ['.flv'],  'Flash Video — ancien'),
            ('OGG',  ['.ogg'],  'format ouvert'),
        ])
    if 8 in modes:
        aud_ext_filter = _ask_ext_filter("d'audios", [
            ('MP3',  ['.mp3'],  'le plus universel — recommandé'),
            ('WAV',  ['.wav'],  'non compressé — haute qualité'),
            ('FLAC', ['.flac'], 'sans perte de qualité'),
            ('AAC',  ['.aac'],  'compression moderne — YouTube, iTunes'),
            ('M4A',  ['.m4a'],  'iTunes — Apple'),
            ('WMA',  ['.wma'],  'Windows Media Audio'),
            ('OPUS', ['.opus'], 'format moderne — compression optimale'),
            ('AIFF', ['.aiff'], 'non compressé — Apple'),
        ])
    if 9 in modes:
        doc_ext_filter = _ask_ext_filter("de documents", [
            ('PDF',              ['.pdf'],         'format universel — le plus courant'),
            ('Word',             ['.doc', '.docx'],'Microsoft Word'),
            ('Excel',            ['.xls', '.xlsx'],'Microsoft Excel'),
            ('PowerPoint',       ['.ppt', '.pptx'],'Microsoft PowerPoint'),
            ('LibreOffice',      ['.odt', '.ods', '.odp'], 'suite bureautique libre'),
            ('EPUB',             ['.epub'],        'ebook — liseuses, Calibre'),
            ('MOBI',             ['.mobi'],        'ebook Kindle'),
        ])
    if 10 in modes:
        arc_ext_filter = _ask_ext_filter("d'archives", [
            ('ZIP',              ['.zip'],         'le plus universel — recommandé'),
            ('RAR',              ['.rar'],         'compression avancée'),
            ('7Z',               ['.7z'],          'compression maximale'),
            ('TAR / GZ / TGZ',   ['.tar', '.gz', '.tgz'],  'archives Unix / Linux'),
            ('BZ2 / XZ / TBZ2',  ['.bz2', '.xz', '.tbz2'], 'archives Unix compressées'),
        ])

    # Mode 6 : arborescence — profondeur obligatoire pour avoir des liens
    depth = _ask_depth()

    respect_robots = False
    if depth > 0:
        robots_choice = _ask_choice(
            "Respecter le fichier robots.txt du site ?",
            [
                (1, "Non  — ignorer les restrictions (recommandé pour usage personnel)"),
                (2, "Oui  — respecter les règles robots.txt (bonne pratique éthique)"),
            ],
        )
        respect_robots = (robots_choice == 2)

    url_filter = ''
    if depth > 0 or 6 in modes:
        filter_choice = _ask_choice(
            "Filtrer les liens à suivre lors du crawl ?",
            [
                (1, "Non — suivre tous les liens du même domaine"),
                (2, "Oui — entrer un mot-clé : seuls les liens dont l'URL contient ce mot seront suivis\n"
                    "       ex: '/articles/' pour ne crawler que la section articles\n"
                    "           'skyrim'     pour ne garder que les pages contenant 'skyrim' dans l'URL"),
            ],
        )
        if filter_choice == 2:
            url_filter = input("\n  Mot-clé à chercher dans l'URL : ").strip()

    # Mode 6 : arborescence (traitement séparé, pas dans crawl())
    if 6 in modes:
        map_depth = depth if depth > 0 else 1
        (progress.console.print if progress else print)('\n⬇  Cartographie des URLs en cours...')
        _crawler.map_urls(url=url, dest=dest, depth=map_depth,
                          session=session, url_filter=url_filter)

    # Modes 1-5 et 7 : crawl normal
    content_modes = [m for m in modes if m != 6]
    if content_modes:
        (progress.console.print if progress else print)('\n⬇  Scraping en cours...')
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


def _handle_mediawiki(url: str, dest: Path, session: requests.Session,
                      progress=None, task_url=None):
    modes = _ask_modes(
        "Que voulez-vous récupérer depuis ce wiki ? (plusieurs choix possibles)",
        [
            (1, "Wikitext brut       — le code source wiki (syntaxe [[liens]], {{templates}})\n"
                "                       utile pour réutiliser le contenu dans un autre wiki"),
            (2, "Données structurées — infobox, description, images extraits via l'API officielle\n"
                "                       format JSON, aucun risque de blocage par le site"),
            (3, "HTML rendu          — la page telle qu'affichée dans le navigateur (.html)"),
            (4, "Texte propre        — contenu lisible uniquement, sans balises (.txt)"),
            (5, "Images seulement    — toutes les images de la page (dossier images/)"),
        ],
    )
    depth = _ask_depth()

    title_filter = ''
    if depth > 0:
        print("\n  Filtre sur les titres des pages liées :")
        print("    Entrez un mot pour ne garder que les pages dont le titre le contient.")
        print("    Exemple : 'Skyrim' pour ne garder que les pages Skyrim:...")
        title_filter = input("    Filtre (vide = toutes les pages) : ").strip()

    do_csv = False
    if 2 in modes:
        csv_choice = _ask_choice(
            "Format d'export pour les données structurées :",
            [
                (1, "JSON seulement"),
                (2, "JSON + CSV  — tableau compatible Excel, pratique pour trier et filtrer"),
            ],
        )
        do_csv = (csv_choice == 2)

    (progress.console.print if progress else print)('\n⬇  Scraping MediaWiki en cours...')
    _crawler.crawl_mediawiki(url, modes=modes, dest=dest, depth=depth,
                              session=session, visited_titles=set(),
                              title_filter=title_filter, do_csv=do_csv)


def _handle_github(url: str, dest: Path, session: requests.Session):
    dl_choice = _ask_choice(
        "Que voulez-vous télécharger depuis ce repo GitHub ?",
        [
            (1, "Tous les fichiers   — télécharge tout le contenu du repo ou du dossier"),
            (2, "Filtrer par type    — choisir quels types de fichiers garder\n"
                "                       ex: uniquement les .py, ou uniquement les .md"),
        ],
    )

    print("\n  Profondeur dans les sous-dossiers :")
    print("    0 = seulement le dossier racine")
    print("    1 = racine + 1 niveau de sous-dossiers")
    print("    Laissez vide pour tout télécharger (illimité)")
    depth_raw = input("  Profondeur [illimitée] : ").strip()
    depth = int(depth_raw) if depth_raw.isdigit() else 999

    ext_filter: list[str] = []
    if dl_choice == 2:
        print("\n  Extensions à garder (séparées par des virgules) :")
        print("    Exemples : .py  /  .md,.txt  /  .json,.csv,.xlsx")
        raw = input("  Extensions : ").strip()
        ext_filter = [e.strip() for e in raw.split(',') if e.strip()]

    print('\n⬇  Téléchargement GitHub en cours...')
    _crawler.crawl_github(url=url, dest=dest, depth=depth,
                           session=session, ext_filter=ext_filter)


def _handle_js(url: str, dest: Path, session: requests.Session,
               pw_cookies: list | None = None, progress=None, task_url=None):
    from scraper_modules.downloader import (fetch_playwright, screenshot_playwright,
                                             extract_text, extract_structured,
                                             extract_image_urls, HEADERS, TIMEOUT)
    from scraper_modules.exporter import save_text, save_json
    from scraper_modules.crawler import _safe, _download_images
    import time

    modes = _ask_modes(
        "Que voulez-vous récupérer depuis ce site interactif ? (plusieurs choix possibles)",
        [
            (1, "HTML après rendu    — le code HTML une fois le JavaScript exécuté (.html)"),
            (2, "Texte propre        — contenu lisible extrait après rendu JavaScript (.txt)"),
            (3, "Screenshot          — capture d'écran de la page telle qu'affichée (.png)"),
            (4, "Données structurées — titre, sections, paragraphes, images (.json)"),
            (5, "Images seulement    — toutes les images détectées après rendu (dossier images/)"),
            (6, "Vidéos              — télécharge les vidéos après rendu JS\n"
                "                       essaie d'abord l'extraction directe, puis yt-dlp"),
            (7, "Audios              — télécharge les fichiers audio après rendu JS\n"
                "                       extraction directe depuis les balises et les scripts"),
            (8, "Documents           — télécharge les fichiers liés (pdf, docx, xlsx...)"),
            (9, "Archives            — télécharge les archives liées (zip, rar, 7z...)"),
        ],
    )

    img_ext_filter: set | None = None
    vid_ext_filter: set | None = None
    aud_ext_filter: set | None = None
    doc_ext_filter: set | None = None
    arc_ext_filter: set | None = None
    if 5 in modes:
        img_ext_filter = _ask_ext_filter("d'images", [
            ('JPG / JPEG', ['.jpg', '.jpeg'], 'photo compressée — le plus courant'),
            ('PNG',        ['.png'],          'image avec transparence'),
            ('GIF',        ['.gif'],          'animation'),
            ('SVG',        ['.svg'],          'graphique vectoriel (logo, icône)'),
            ('WEBP',       ['.webp'],         'format moderne compressé'),
            ('BMP',        ['.bmp'],          'bitmap non compressé'),
            ('ICO',        ['.ico'],          'icône de site'),
            ('AVIF',       ['.avif'],         'format moderne haute qualité'),
        ])
    if 6 in modes:
        vid_ext_filter = _ask_ext_filter("de vidéos", [
            ('MP4',  ['.mp4'],  'le plus universel — recommandé'),
            ('WEBM', ['.webm'], 'format web ouvert'),
            ('MOV',  ['.mov'],  'QuickTime — Apple'),
            ('AVI',  ['.avi'],  'format classique Windows'),
            ('MKV',  ['.mkv'],  'conteneur flexible haute qualité'),
            ('M4V',  ['.m4v'],  'iTunes — Apple'),
            ('FLV',  ['.flv'],  'Flash Video — ancien'),
            ('OGG',  ['.ogg'],  'format ouvert'),
        ])
    if 7 in modes:
        aud_ext_filter = _ask_ext_filter("d'audios", [
            ('MP3',  ['.mp3'],  'le plus universel — recommandé'),
            ('WAV',  ['.wav'],  'non compressé — haute qualité'),
            ('FLAC', ['.flac'], 'sans perte de qualité'),
            ('AAC',  ['.aac'],  'compression moderne — YouTube, iTunes'),
            ('M4A',  ['.m4a'],  'iTunes — Apple'),
            ('WMA',  ['.wma'],  'Windows Media Audio'),
            ('OPUS', ['.opus'], 'format moderne — compression optimale'),
            ('AIFF', ['.aiff'], 'non compressé — Apple'),
        ])
    if 8 in modes:
        doc_ext_filter = _ask_ext_filter("de documents", [
            ('PDF',        ['.pdf'],         'format universel — le plus courant'),
            ('Word',       ['.doc', '.docx'],'Microsoft Word'),
            ('Excel',      ['.xls', '.xlsx'],'Microsoft Excel'),
            ('PowerPoint', ['.ppt', '.pptx'],'Microsoft PowerPoint'),
            ('LibreOffice',['.odt', '.ods', '.odp'], 'suite bureautique libre'),
            ('EPUB',       ['.epub'],        'ebook — liseuses, Calibre'),
            ('MOBI',       ['.mobi'],        'ebook Kindle'),
        ])
    if 9 in modes:
        arc_ext_filter = _ask_ext_filter("d'archives", [
            ('ZIP',             ['.zip'],         'le plus universel — recommandé'),
            ('RAR',             ['.rar'],         'compression avancée'),
            ('7Z',              ['.7z'],          'compression maximale'),
            ('TAR / GZ / TGZ',  ['.tar', '.gz', '.tgz'],  'archives Unix / Linux'),
            ('BZ2 / XZ / TBZ2', ['.bz2', '.xz', '.tbz2'], 'archives Unix compressées'),
        ])

    opts = _ask_playwright_opts()
    if pw_cookies:
        opts['cookies'] = pw_cookies
    base_name = _safe(url.rstrip('/').split('/')[-1] or 'page')

    if progress and task_url is not None:
        progress.update(task_url, description=f"{urlparse(url).netloc} — rendu JS")
    out = progress.console.print if progress else print
    out('\n⬇  Chargement Playwright en cours...')
    try:
        if 3 in modes:
            path = screenshot_playwright(url, dest, **opts)
            print(f"  ✅ Screenshot: {path.name}")

        if any(m in modes for m in [1, 2, 4, 5, 6, 7, 8, 9]):
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
                count = _download_images(img_urls, dest / "images", session,
                                         ext_filter=img_ext_filter)
                print(f"  ✅ {count} image(s) → images/")
            if 6 in modes:
                from scraper_modules.downloader import (extract_video_urls as _extract_vids,
                                                        extract_video_page_urls as _extract_vid_pages)
                from scraper_modules.crawler import _download_videos, _download_ytdlp
                vid_urls = _extract_vids(html, url)
                vid_dest = dest / "videos"
                if vid_urls:
                    count = _download_videos(vid_urls, vid_dest, session,
                                             ext_filter=vid_ext_filter,
                                             progress=progress)
                    print(f"  ✅ {count} vidéo(s) directe(s) → videos/")
                else:
                    page_urls = _extract_vid_pages(html, url)
                    if page_urls:
                        print(f"  ⚠ Aucune vidéo directe — {len(page_urls)} page(s) vidéo détectée(s), tentative yt-dlp...")
                        success = 0
                        for vpage in page_urls:
                            print(f"    → {vpage}")
                            if _download_ytdlp(vpage, vid_dest):
                                success += 1
                        if not success:
                            print(f"  ✗ Aucune vidéo récupérée.")
                    else:
                        print(f"  ⚠ Aucune vidéo directe — tentative yt-dlp...")
                        if not _download_ytdlp(url, vid_dest):
                            print(f"  ✗ Aucune vidéo récupérée.")
            if 7 in modes:
                from scraper_modules.downloader import extract_audio_urls as _extract_auds
                from scraper_modules.crawler import _download_audios
                aud_urls = _extract_auds(html, url)
                aud_dest = dest / "audios"
                if aud_urls:
                    count = _download_audios(aud_urls, aud_dest, session,
                                             ext_filter=aud_ext_filter,
                                             progress=progress)
                    print(f"  ✅ {count} audio(s) → audios/")
                else:
                    print(f"  ⚠ Aucun audio trouvé sur cette page.")
            if 8 in modes:
                from scraper_modules.downloader import extract_document_urls as _extract_docs
                from scraper_modules.crawler import _download_documents
                doc_urls = _extract_docs(html, url)
                doc_dest = dest / "documents"
                if doc_urls:
                    count = _download_documents(doc_urls, doc_dest, session,
                                                ext_filter=doc_ext_filter,
                                                progress=progress)
                    print(f"  ✅ {count} document(s) → documents/")
                else:
                    print(f"  ⚠ Aucun document trouvé sur cette page.")
            if 9 in modes:
                from scraper_modules.downloader import extract_archive_urls as _extract_arcs
                from scraper_modules.crawler import _download_archives
                arc_urls = _extract_arcs(html, url)
                arc_dest = dest / "archives"
                if arc_urls:
                    count = _download_archives(arc_urls, arc_dest, session,
                                               ext_filter=arc_ext_filter,
                                               progress=progress)
                    print(f"  ✅ {count} archive(s) → archives/")
                else:
                    print(f"  ⚠ Aucune archive trouvée sur cette page.")

    except ImportError as e:
        print(f'\n❌ {e}')


# ── Boucle principale ─────────────────────────────────────────────────────────

def main():
    print(BANNER)

    print("\n  Dossier de destination — les fichiers téléchargés seront sauvegardés ici.")
    print(f"  Appuyez sur Entrée pour utiliser le dossier par défaut.")
    dest_raw = _ask('  Chemin', str(DEFAULT_DEST))
    dest = Path(dest_raw)
    dest.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ Dossier : {dest}")

    session = requests.Session()

    pw_cookies: list = []
    cookies_choice = _ask_choice(
        "Charger des cookies de session (pour les sites nécessitant une connexion) ?",
        [
            (1, "Non  — accès public, pas besoin de connexion (recommandé)"),
            (2, "Oui  — charger un fichier cookies.txt exporté depuis votre navigateur\n"
                "         Extension recommandée : 'Get cookies.txt LOCALLY' (Chrome/Firefox)"),
        ],
    )
    if cookies_choice == 2:
        print("\n  Entrez le chemin vers votre fichier cookies.txt.")
        print("  Exemple : C:\\Users\\Moi\\Downloads\\cookies.txt")
        cookies_raw = input("  Chemin : ").strip().strip('"')
        cookies_path = Path(cookies_raw)
        if cookies_path.exists():
            pw_cookies = _load_cookies(session, cookies_path)
            print(f"  ✓ {len(pw_cookies)} cookie(s) chargé(s)")
        else:
            print(f"  ⚠ Fichier introuvable : {cookies_path}")

    while True:
        print(f'\n{"─" * 47}')
        print("  Entrez une URL, un fichier .txt (liste d'URLs),")
        print("  ou 'q' / 'exit' pour quitter.")
        print("  Plusieurs URLs : séparez-les par des virgules.")
        print()
        raw = input("  > ").strip()

        if raw.lower() in ('q', 'exit', 'quitter', 'quit'):
            print('\n  Au revoir !\n')
            break

        if not raw:
            continue

        urls = _parse_urls(raw)
        if not urls:
            print('  ⚠ Aucune URL valide détectée.')
            continue

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

                existing_session = load_session(url)
                if existing_session and existing_session.get('dest') != str(url_dest):
                    existing_session = None
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
                        existing_session['completed'] = False
                        existing_session['completed_at'] = None
                        initial_visited = set(existing_session.get('visited', []))
                        session_data = existing_session
                        save_session(session_data)

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
                        try:
                            save_session(session_data)
                        except Exception as _e:
                            (progress.console.print if progress else print)(
                                f"  ⚠ Session non sauvegardée : {_e}")
                    if task_url is not None:
                        progress.update(task_url, visible=False)
                    progress.advance(task_global)


if __name__ == '__main__':
    main()
