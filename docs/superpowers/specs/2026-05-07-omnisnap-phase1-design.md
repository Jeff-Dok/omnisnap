# OmniSnap — Phase 1 : Design

## Contexte

OmniSnap est une application Windows qui expose le scraper CLI Python (`scraper_app/`) dans une interface graphique. Elle cible aussi bien les débutants que les utilisateurs avancés.

Le scraper CLI est déjà complet (11 modes, reprise sur interruption, cookies, robots.txt). OmniSnap ne réimplémente pas la logique — il appelle les mêmes fonctions Python en passant `log=queue.put` pour capturer les sorties en temps réel.

Phase 1 livre une app `.exe` fonctionnelle : scraper une URL, voir les logs en direct, ouvrir le dossier résultat. Historique, paramètres et file d'attente arrivent en Phase 2 et 3.

---

## Stack technique

- **GUI** : CustomTkinter
- **Packaging** : PyInstaller → `dist/OmniSnap.exe`
- **Communication scraper → GUI** : `queue.Queue` + thread Python (le scraper tourne dans un thread séparé, écrit dans la queue, le thread GUI lit la queue toutes les 100 ms via `after()`)
- **Persistance** : JSON dans `%APPDATA%\OmniSnap\` (Phase 1 : dernière URL uniquement)

---

## Palette visuelle — Nuit Électrique

| Élément | Couleur |
|---------|---------|
| Fond principal | `#16213e` |
| Sidebar | `#1a1040` |
| Surfaces (cards, inputs) | `#0d0d26` |
| Bordures | `#2d2d4e` |
| Accent principal | `#00B4D8` (cyan) |
| Texte principal | `#e0e0e0` |
| Texte secondaire | `#888888` |
| Succès | `#4CAF50` |
| Avertissement | `#FF9800` |
| Erreur | `#ef5350` |

---

## Architecture des fichiers

```
scraper_app/
├── main.py                     ← point d'entrée, lance la fenêtre CTk
├── gui/
│   ├── app.py                  ← fenêtre principale (sidebar + zone centrale)
│   ├── sidebar.py              ← widget sidebar (logo + boutons nav)
│   ├── wizard.py               ← wizard 4 étapes (formulaire scrape)
│   ├── scrape_view.py          ← vue split (résumé + log) pendant et après scraping
│   └── theme.py                ← constantes de couleurs et styles CTk
├── core/
│   └── runner.py               ← lance le scraper dans un thread, gère la queue
└── build/
    └── OmniSnap.spec           ← config PyInstaller
```

Les modules `scraper_modules/` existants sont réutilisés sans modification.

---

## Composants

### Fenêtre principale (`app.py`)

- Dimensions : 900×600 px, non redimensionnable en Phase 1
- Layout : sidebar fixe 160 px à gauche + zone centrale flexible
- Gère la navigation entre vues (wizard ↔ scrape_view)
- Titre : "OmniSnap"

### Sidebar (`sidebar.py`)

- Logo "⚡ OmniSnap" en haut
- Bouton "🔍 Nouveau scrape" — actif (cyan) quand sélectionné
- Bouton "🕐 Historique" — désactivé (opacité 0.3), tooltip "Disponible en Phase 2"
- Bouton "⚙️ Paramètres" — désactivé, tooltip "Disponible en Phase 2"
- Séparateur + section "Récent" : vide en Phase 1 (prévu Phase 2)

### Wizard (`wizard.py`) — 4 étapes

**Étape 1 — URL**
- Champ texte (URL), hint : "https://exemple.com/article"
- Validation : doit commencer par `http://` ou `https://`
- Dernière URL utilisée pré-remplie depuis `%APPDATA%\OmniSnap\prefs.json`
- Bouton "Suivant →"

**Étape 2 — Contenu**
- Question : "Que voulez-vous récupérer ?"
- Hint : "Vous pouvez choisir plusieurs types."
- Options (checkbox + icône + nom + description courte) :
  - 📄 Texte propre — contenu lisible, format .txt
  - 🖼️ Images — jpg, png, webp...
  - 🎬 Vidéos — mp4, webm, mov... (ne fonctionne pas pour YouTube)
  - 🎵 Audios — mp3, wav, flac...
  - 📁 Documents — PDF, Word, Excel...
  - 📦 Archives — zip, rar, 7z...
  - 📷 Screenshot — capture pleine page (.png)
  - 🌐 HTML complet — page + assets CSS/images
- Au moins 1 sélection requise pour continuer
- Boutons "← Retour" et "Suivant →"

**Étape 3 — Options**
- Question : "Combien de pages suivre ?"
- Boutons de profondeur : 0 (cette page seulement — recommandé), +1, +2, +3
- Description contextuelle sous les boutons (ex : "Suit les liens directs de la page")
- Boutons "← Retour" et "Suivant →"

**Étape 4 — Lancer** _(+ Avancé optionnel)_
- Récapitulatif : URL, types sélectionnés, profondeur
- Section "Avancé (optionnel)" — réduite par défaut, bouton "▸ Options avancées" pour déplier :
  - Champ fichier cookies.txt (bouton "Parcourir...")
  - Hint : "Pour les sites nécessitant une connexion. Exportez avec l'extension 'Get cookies.txt LOCALLY'."
- Bouton principal "▶ Lancer le scraping"
- Bouton "← Retour"

### Vue scraping (`scrape_view.py`)

**Pendant le scraping — layout split :**

Zone haute (fixe, ~110 px) :
- URL scrapée (tronquée si longue)
- Tags des modes sélectionnés (ex : `📄 Texte` `🎬 Vidéos` `Profondeur +1`)
- Badge "● En cours" animé (orange pulsé)
- Compteur : "X pages · X fichiers"
- Barre de progression (indéterminée si total inconnu, déterminée si total connu)
- Bouton "⏹ Annuler"

Zone basse (flexible) :
- Titre "Journal"
- Zone log monospace (`Consolas` 10px, fond `#0a0a1a`)
  - Format : `HH:MM:SS  message`
  - Couleurs : vert pour succès (✓), cyan pour téléchargement (↓), orange pour avertissement, gris pour info
  - Auto-scroll vers le bas
- Le scraper tourne dans un thread via `runner.py`, écrit dans `queue.Queue`
- GUI lit la queue via `widget.after(100, poll_queue)`

**Après complétion :**

Zone haute transformée :
- Bannière verte : "✅ Scraping terminé !" + résumé (X pages · X fichiers · X MB)
- Bouton "📂 Ouvrir le dossier" (ouvre l'explorateur Windows sur le dossier de destination)
- Barre de progression : 100%, couleur verte

Zone basse :
- Log complet reste visible (dernière ligne en vert : "✓ Terminé — ...")
- Bouton "＋ Nouveau scrape" en bas à droite → revient à l'étape 1 du wizard

**En cas d'erreur :**
- Bannière rouge dans la zone haute : "✗ Erreur — [message]"
- Log reste visible avec les détails
- Bouton "↩ Réessayer" → revient à l'étape 4 du wizard (réglages conservés)

### Runner (`core/runner.py`)

- `ScraperRunner` : classe qui encapsule l'exécution du scraper dans un `threading.Thread`
- Appelle directement `crawl()` / `_handle_general()` (pas `main()` qui est interactif CLI) avec `log=queue.put`
- Expose `start()`, `cancel()` — `cancel()` set un `threading.Event`; `crawl()` devra vérifier cet event entre chaque page (modification mineure de `crawler.py`)
- Retourne le statut final via la queue : message spécial `{"type": "done", "stats": {...}}` ou `{"type": "error", "message": "..."}`

### Thème (`gui/theme.py`)

Constantes centralisées :
```python
BG_MAIN = "#16213e"
BG_SIDEBAR = "#1a1040"
BG_SURFACE = "#0d0d26"
BORDER = "#2d2d4e"
ACCENT = "#00B4D8"
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#888888"
SUCCESS = "#4CAF50"
WARNING = "#FF9800"
ERROR = "#ef5350"
```

---

## Flux principal

```
Lancement → wizard étape 1 (URL)
  → étape 2 (contenu)
  → étape 3 (profondeur)
  → étape 4 (récap + avancé optionnel)
  → clic "Lancer"
  → scrape_view (split log)
    → bannière verte + "Ouvrir dossier"
    → clic "Nouveau scrape" → wizard étape 1
```

---

## Persistance Phase 1

Fichier `%APPDATA%\OmniSnap\prefs.json` :
```json
{
  "last_url": "https://exemple.com/article"
}
```

Chargé au démarrage, sauvegardé après chaque scrape réussi.

---

## Ce qui n'est PAS dans Phase 1

- Historique des scrapes (Phase 2)
- Thème clair/sombre/système (Phase 2)
- Notifications Windows toast (Phase 2)
- File d'attente multi-URL (Phase 3)
- Installateur Inno Setup (Phase 3)
- Bouton "Annuler" avec dialog si file d'attente (Phase 3)

---

## Critères de succès Phase 1

1. L'app se lance sans erreur sur Windows 11
2. On peut scraper une URL et voir les logs en temps réel
3. Le bouton "Ouvrir le dossier" ouvre l'explorateur au bon endroit
4. Le bouton "Annuler" arrête proprement le scraper
5. L'app se ferme proprement (threads terminés)
6. Le `.exe` PyInstaller fonctionne sans Python installé
