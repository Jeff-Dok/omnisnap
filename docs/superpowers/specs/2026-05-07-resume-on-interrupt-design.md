# Spec — Reprise sur interruption

**Date :** 2026-05-07  
**Projet :** Scraper CLI Python  
**Statut :** Approuvé

---

## Objectif

Permettre au scraper de reprendre intelligemment après une interruption (Ctrl+C, erreur réseau, crash) :
- **Skip de session** : éviter de re-crawler des pages déjà traitées
- **Détection de partiels** : re-télécharger les fichiers tronqués lors d'une reprise

---

## Architecture

### Nouveau fichier

**`scraper_modules/session.py`**  
Expose trois fonctions :
- `load_session(url, modes, sessions_dir) -> dict | None` — charge la session correspondante depuis `sessions/`
- `save_session(data: dict, sessions_dir: Path) -> None` — écrit le fichier JSON de session
- `is_partial(path: Path, content_length: int | None, min_size: int) -> bool` — détecte un fichier partiel

### Dossier de sessions

**`scraper_app/sessions/`**  
Un fichier JSON par run, nommé `{YYYY-MM-DDTHHMMSS}_{netloc}.json`.  
Centralisé dans l'app (pas dans le dossier de téléchargement) pour faciliter l'intégration UI OmniSnap.

### Fichiers modifiés

| Fichier | Changement |
|---|---|
| `scraper.py` | Charge la session avant chaque URL, skip ou reconstitue `visited`, sauvegarde session dans `finally:` |
| `scraper_modules/crawler.py` | Sauvegarde session après chaque page, détecte partiels avant skip `if out.exists()` |
| `scraper_modules/session.py` | **Nouveau** — load / save / is_partial |
| `tests/test_session.py` | **Nouveau** — tests unitaires |

---

## Format du fichier session

```json
{
  "url": "https://python.org",
  "dest": "C:\\Users\\jnfra\\Downloads\\Scraper\\python.org_downloads",
  "modes": [7, 8],
  "completed": false,
  "visited": ["https://python.org/", "https://python.org/docs/"],
  "started_at": "2026-05-07T10:00:00",
  "completed_at": null
}
```

**Règle de correspondance :** match sur `url` + `modes` triés. Modes différents = nouvelle session.

---

## Comportement

### Au démarrage de chaque URL (dans `scraper.py`)

1. Chercher un fichier session dans `scraper_app/sessions/` dont `url` + `modes` correspondent
2. **Session `completed: true`** → skip le crawl, scanner le dossier `dest` pour fichiers partiels, avancer la barre globale
3. **Session `completed: false`** → reconstituer le set `visited` depuis la liste, reprendre le crawl
4. **Aucune session** → comportement normal, créer un nouveau fichier session

### Pendant le crawl (dans `crawler.py`)

Après chaque page visitée : `save_session()` met à jour `visited` sur disque.

### À la fin d'une URL

`completed: true` + `completed_at` écrits dans le JSON.

### Ctrl+C

Le `finally:` dans `scraper.py` appelle `save_session()` avec `completed: false` → session sauvegardée.

---

## Détection des fichiers partiels

`is_partial(path, content_length, min_size) -> bool` :

1. Si `content_length` connu → `path.stat().st_size != content_length` → partiel
2. Si `content_length` inconnu → `path.stat().st_size < min_size` → partiel

### Valeurs `min_size` par type

| Type | Min size |
|---|---|
| Vidéo / Audio | 65 536 octets (64 KB) |
| Document / Archive | 1 024 octets (1 KB) |

Quand partiel détecté : suppression + re-téléchargement.

**Images exclues** : pas de détection de partiels (trop petites et trop nombreuses).

---

## Gestion des erreurs et cas limites

| Cas | Comportement |
|---|---|
| Dossier `sessions/` inexistant | Créé automatiquement au premier run |
| Fichier session corrompu (JSON invalide) | Ignoré silencieusement → nouveau run normal |
| `dest` pointe vers un dossier supprimé | Session ignorée → nouveau run |
| Ctrl+C en plein crawl | `finally:` sauvegarde session avec `completed: false` |
| Ctrl+C en plein téléchargement | Fichier partiel → détecté + re-téléchargé au prochain run |
| `progress=None` | Fonctionne sans rich — zéro régression |
| Même URL, modes différents | Nouvelle session créée |
| `depth=0` | `visited = [url]`, `completed: true` immédiat |

---

## Principe de rétrocompatibilité

Le chargement de session est optionnel. Si aucune session n'existe, le comportement est identique à avant. Aucune signature de fonction existante n'est modifiée de façon incompatible.

---

## Intégration future OmniSnap

Le dossier `scraper_app/sessions/` est conçu pour être lu par l'UI OmniSnap :
- Lister l'historique des runs (un fichier = un run)
- Afficher le statut (`completed`, `started_at`, `url`)
- Supprimer un fichier session depuis l'UI pour forcer un re-scrape

---

## Dépendances

Aucune dépendance supplémentaire — stdlib uniquement (`json`, `pathlib`, `datetime`).
