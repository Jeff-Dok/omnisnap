# Brainstorming — Scraper App Windows
**Date :** 2026-05-04  
**Statut :** En cours — design validé, spec et plan à faire

---

## Contexte

Transformer `scraper.py` (script CLI Python) en une vraie application Windows installable, avec une interface graphique. Point de départ de ce dossier `scraper_app/`.

---

## Décisions prises

### Stack technique
- **GUI :** CustomTkinter (Python natif, UI moderne thème sombre)
- **Packaging :** PyInstaller → dossier `dist/scraper/` avec tout bundlé
- **Installateur :** Inno Setup → `Scraper_Setup.exe` (Program Files, menu Démarrer, désinstallation propre)
- **Tout bundlé dans l'installateur** : Python runtime, Playwright, yt-dlp, toutes les dépendances — l'utilisateur n'installe rien manuellement

### Interface — Dashboard avec sidebar
```
┌─────────────────────────────────────────────────┐
│ Sidebar gauche    │ Zone principale              │
│                   │                              │
│ • Nouveau scrape  │ [Formulaire URL + modes]     │
│ • Historique      │                              │
│ • Paramètres      │ ┌── Tabs ──────────────────┐ │
│                   │ │ Log en direct            │ │
│ ── Récents ──     │ │ Aperçu résultats         │ │
│ uesp.net/...      │ │ Fichiers sauvegardés     │ │
│ fandom.com/...    │ └──────────────────────────┘ │
│ github.com/...    │                              │
│ [Voir tout]       │                              │
└─────────────────────────────────────────────────┘
```

### Features incluses
| Feature | Détail |
|---|---|
| Persistance dernière sélection | Modes + profondeur + filtre sauvegardés automatiquement |
| Log en temps réel | Timestamps + codes couleur (vert/jaune/bleu) + barre de progression |
| Aperçu intégré | Tabs : Log / Aperçu résultats / Fichiers sauvegardés |
| Historique sidebar | 3 entrées récentes + bouton "Voir tout" |
| Historique complet | ~30 entrées + bouton "Relancer" par entrée + bouton "Vider l'historique" |
| Annuler scrape | Direct si seul ; dialog (actuel / tout) si file d'attente |
| File d'attente | Option simple : bouton "+ Ajouter à la file", suppression par item, pas de drag-and-drop |
| Notifications Windows | Toast Windows quand un scrape se termine |
| Thème | Clair / Sombre / Système (dans paramètres) |

### Paramètres (section Général uniquement)
- Dossier de sortie par défaut
- Thème (clair / sombre / système)
- Ouvrir le dossier automatiquement après scraping (toggle)
- Notifications Windows (toggle)

### Valeurs fixées dans le code
- Timeout par requête : **30 secondes**
- Délai entre requêtes : **1 seconde**
- Historique max : **30 entrées**
- Sidebar récents : **3 entrées**

### Architecture des fichiers (à créer)
```
scraper_app/
├── scraper.py                  ← CLI existant (inchangé)
├── scraper_modules/            ← modules existants (inchangés)
│   ├── __init__.py
│   ├── detector.py
│   ├── downloader.py
│   ├── crawler.py
│   ├── mediawiki.py
│   └── exporter.py
├── gui/                        ← À CRÉER
│   ├── app.py                  ← fenêtre principale CTk
│   ├── sidebar.py              ← navigation gauche
│   └── panels/
│       ├── scrape_panel.py     ← formulaire URL + modes
│       ├── log_panel.py        ← log temps réel
│       ├── preview_panel.py    ← aperçu résultats
│       └── history_panel.py   ← historique complet
├── main.py                     ← À CRÉER (point d'entrée app)
├── build/                      ← À CRÉER
│   ├── scraper.spec            ← config PyInstaller
│   └── installer.iss           ← script Inno Setup
├── docs/                       ← existant (specs + plans CLI)
└── BRAINSTORM.md               ← ce fichier
```

### Flux technique clé
- Le scraping tourne dans un **thread séparé** (pas le thread UI)
- Une **Queue Python** (thread-safe) transmet les messages de log au `log_panel` en temps réel
- L'historique est stocké en **JSON** dans `AppData/Local/ScraperApp/history.json`
- Les paramètres sont stockés en **JSON** dans `AppData/Local/ScraperApp/settings.json`

---

## Prochaines étapes

1. Écrire le document de spec complet (`docs/superpowers/specs/2026-05-04-scraper-app-windows-design.md`)
2. Invoquer `writing-plans` pour créer le plan d'implémentation détaillé
3. Implémenter : `main.py` → `gui/app.py` → panels → build scripts

---

## Ce qui reste à décider (lors d'une prochaine session)

- Icône de l'application (à fournir)
- Nom exact de l'application (`Web Scraper` ? `ScraperApp` ? autre ?)
- Couleur d'accent du thème (par défaut CustomTkinter bleu — changer ?)
