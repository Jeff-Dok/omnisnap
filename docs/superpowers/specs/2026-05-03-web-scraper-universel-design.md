# Web Scraper Universel — Document de Design
**Date :** 2026-05-03
**Dossier cible :** `Scripts_Python/scraper/`

---

## Objectif

Remplacer les trois scripts existants (`RAW_WEB.py`, `download_url.py`, `scrape_fandom.py`) par un seul outil interactif universel capable de scraper n'importe quelle URL — wikis MediaWiki, sites généraux, GitHub, sites JavaScript-lourds — avec des questions adaptées au type d'URL détecté.

---

## Structure des fichiers

```
Scripts_Python/scraper/
├── scraper.py                  ← point d'entrée interactif (boucle principale)
└── scraper_modules/
    ├── __init__.py
    ├── detector.py             ← détection du type d'URL
    ├── downloader.py           ← téléchargement HTTP (requests + Playwright)
    ├── crawler.py              ← crawl multi-pages avec profondeur + batch
    ├── mediawiki.py            ← wikitext brut + API structurée MediaWiki
    └── exporter.py             ← sauvegarde (txt, html, json, csv, images)
```

---

## Flux interactif

```
=== 🕷 WEB SCRAPER UNIVERSEL ===

URL(s) à scraper, chemin vers un .txt (une URL par ligne), ou 'q'/'exit' :
> [entrée utilisateur]

🔍 Détection du type d'URL...
  → [Général | MediaWiki | GitHub | JS-lourd]

[Questions spécifiques au type détecté]

⬇  Exécution...
  ✅ Fichier(s) sauvegardé(s) dans [dossier]

[Boucle — nouvelle URL ou 'q' pour quitter]
```

- La sélection multiple est supportée pour les modes : ex. `1,4` pour texte propre + JSON
- Le script boucle après chaque tâche jusqu'à `q` ou `exit`
- Le dossier de destination est demandé une seule fois par session (mémorisé jusqu'à la fin)

---

## Types d'URL et modes

### Type 1 — Site général
Détecté par défaut si aucun autre type ne correspond.

| # | Mode | Sortie |
|---|------|--------|
| 1 | Texte propre | `.txt` |
| 2 | HTML brut | `.html` |
| 3 | Téléchargement complet (HTML + assets) | dossier |
| 4 | Données structurées (titre, headings, paragraphes, images) | `.json` / `.csv` |
| 5 | Images seulement | dossier `images/` |

**Options :**
- Profondeur de crawl (0 = page seule, 1+ = suit les liens)
- Utiliser Playwright ? `[o/N]`
- Dossier de destination

---

### Type 2 — Wiki MediaWiki
Détecté si l'URL contient `/wiki/`, `/w/index.php`, ou un domaine reconnu (`wikipedia.org`, `fandom.com`, `uesp.net`, `minecraft.wiki`, etc.).

| # | Mode | Sortie |
|---|------|--------|
| 1 | Wikitext brut | `.txt` |
| 2 | Données structurées via API (infobox, description, images) | `.json` / `.csv` |
| 3 | HTML rendu | `.html` |
| 4 | Texte propre | `.txt` |
| 5 | Images seulement | dossier `images/` |

**Options spécifiques :**
- Profondeur de crawl (suit les liens vers d'autres pages du même wiki)
- Filtre sur les titres de pages (ex. : garder seulement les titres contenant "Skyrim")
- Export CSV en plus du JSON (mode 2 uniquement)
- Gestion automatique des redirections MediaWiki (`#REDIRECT [[Titre]]`)

---

### Type 3 — GitHub
Détecté si l'URL contient `github.com`.

| # | Mode | Sortie |
|---|------|--------|
| 1 | Repo complet | dossier |
| 2 | Sous-dossier seulement | dossier |
| 3 | Fichier seul | fichier |

**Options spécifiques :**
- Profondeur dans les sous-dossiers (défaut : illimité)
- Filtre d'extensions (ex. : `.py`, `.json`)
- Utilise l'API GitHub (pas de `git` requis, fonctionne sur les repos publics sans token)
- Fallback automatique `main` → `master` si la branche par défaut est inconnue

---

### Type 4 — Site interactif / JS-lourd
Détecté heuristiquement (extension `.js` dominante, absence de contenu HTML après requête simple, ou domaines connus comme les apps SPA). Playwright est **obligatoire** pour ce type.

| # | Mode | Sortie |
|---|------|--------|
| 1 | HTML après rendu JS | `.html` |
| 2 | Texte propre après rendu JS | `.txt` |
| 3 | Screenshot | `.png` |
| 4 | Données structurées après rendu | `.json` |
| 5 | Images seulement | dossier `images/` |

**Options spécifiques :**
- Attendre un sélecteur CSS avant capture (ex. : `#map-container`)
- Délai d'attente après chargement en secondes (défaut : 2s)
- Taille de la fenêtre navigateur (défaut : 1280×720)

---

## Module `detector.py`

Logique de détection dans l'ordre de priorité :

1. `github.com` dans le domaine → **GitHub**
2. `/wiki/`, `/w/index.php`, ou domaine MediaWiki connu → **MediaWiki**
3. Requête HEAD simple → si le contenu HTML est quasi-vide (< 500 chars) ou si l'utilisateur force → **JS-lourd**
4. Sinon → **Général**

---

## Module `downloader.py`

- Utilise `requests` par défaut (léger, rapide)
- Bascule sur Playwright si demandé ou si le type détecté est JS-lourd
- Si Playwright n'est pas installé : message d'erreur clair avec la commande d'installation
- Timeout configurable (défaut : 20s)
- Délai entre requêtes pour le crawl (défaut : 0.3s)
- User-Agent réaliste pour éviter les blocages basiques

---

## Module `crawler.py`

- Profondeur 0 = page seule, 1 = page + liens directs, etc.
- Reste sur le même domaine par défaut (option `--any-domain` pour lever la restriction)
- Évite les boucles via un `set` d'URLs visitées
- Supporte le mode **batch** : plusieurs URLs passées d'un coup (séparées par des virgules) ou depuis un fichier `.txt` (une URL par ligne, `#` pour commenter)

---

## Module `mediawiki.py`

- Détecte automatiquement l'URL de l'API (`/api.php` ou `/w/api.php`)
- Gestion des redirections internes (`#REDIRECT`)
- Fallback 404 : essaie `/w/` puis `/wiki/` si la première URL échoue
- Extraction de l'infobox : supporte les infoboxes portables Fandom ET les `wikitable` classiques

---

## Module `exporter.py`

- Nommage automatique des fichiers d'après la dernière partie de l'URL
- Numérotation automatique si le fichier existe déjà (ex. `page_1.txt`, `page_2.txt`)
- Ouvre le dossier de destination dans l'explorateur Windows après chaque téléchargement
- Formats supportés : `.txt`, `.html`, `.json`, `.csv`, `.png`, dossier d'images

---

## Dépendances

```
pip install requests beautifulsoup4
pip install playwright && python -m playwright install chromium
```

Playwright est **optionnel** — le script fonctionne sans lui sauf pour le type JS-lourd.

---

## Ce que ce script remplace

| Ancien script | Fonctionnalité couverte par |
|--------------|----------------------------|
| `RAW_WEB.py` | Type MediaWiki → Mode 1 (Wikitext brut) |
| `download_url.py` | Type Général → Modes 2/3, Type GitHub, crawl |
| `scrape_fandom.py` | Type MediaWiki → Mode 2 (Données structurées API) |
