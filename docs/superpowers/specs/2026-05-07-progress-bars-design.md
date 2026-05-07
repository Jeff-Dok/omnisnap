# Spec — Barres de progression (rich)

**Date :** 2026-05-07  
**Projet :** Scraper CLI Python  
**Statut :** Approuvé

---

## Objectif

Ajouter des barres de progression visuelles au CLI scraper :
- **Barre globale** : avancement sur la liste d'URLs saisies par l'utilisateur
- **Ligne URL en cours** : spinner + compteur de pages crawlées dynamique
- **Barre unitaire** : progression par fichier lourd téléchargé (vidéo / audio / doc / archive)

**Librairie choisie :** `rich` (`pip install rich`)

---

## Architecture

### Fichier nouveau

**`scraper_modules/progress.py`**  
Expose une fonction `make_progress()` qui retourne un objet `rich.progress.Progress` préconfiguré avec les colonnes :
- Spinner animé
- Description (nom fichier ou URL)
- Barre de progression
- Pourcentage
- Vitesse de transfert
- Taille transférée
- Temps restant estimé (ETA)

### Fichiers modifiés

| Fichier | Changement |
|---|---|
| `scraper.py` | Crée le Progress, ouvre le context manager, passe `progress` + `task_global` aux handlers, avance la barre globale après chaque URL complète |
| `crawler.py` | `crawl()` reçoit `progress` + `task_url` optionnels → met à jour le compteur de pages ; `_download_videos()`, `_download_audios()`, `_download_files()` reçoivent `progress` optionnel → créent une barre unitaire par fichier |
| `scraper_modules/progress.py` | **Nouveau** — factory `make_progress()` |

---

## Comportement visuel

Panneau rich affiché en bas du terminal pendant tout le scraping :

```
Scraping global  ━━━━━━━━━━━━━━━━━━━━━━━━  2/3  66%
⠸ python.org  —  18 pages visitées
video_intro.mp4  ━━━━━━━━━━━━░░░░░░░░░░░  52%  1.8 MB/s  eta 0:00:12
```

### Barre globale
- `total = len(urls)` — connu dès le début
- Avance de 1 quand une URL est entièrement traitée
- Description fixe : `Scraping global`

### Ligne URL en cours
- Task rich avec spinner animé
- Description = nom de domaine + compteur de pages crawlées, ex : `python.org — 18 pages visitées`
- Mise à jour à chaque page visitée dans `crawl()`
- Masquée (`visible=False`) dès l'URL terminée

### Barre unitaire (fichiers lourds)
- Créée au début de chaque téléchargement (vidéo / audio / doc / archive)
- `total = Content-Length` du header HTTP si disponible, sinon `None` (barre indéterminée)
- Description = nom du fichier
- Supprimée dès le fichier terminé
- **Images exclues** : trop petites et trop nombreuses, pas de barre unitaire

---

## Gestion des erreurs et cas limites

| Cas | Comportement |
|---|---|
| `Content-Length` absent | Barre indéterminée : spinner + vitesse + octets transférés, sans % ni ETA |
| `Ctrl+C` | Context manager rich ferme proprement l'affichage avant le message d'interruption |
| Erreur de téléchargement | Barre unitaire supprimée, message via `progress.console.print()` |
| `progress=None` | Toutes les fonctions fonctionnent comme avant — zéro régression |
| Fichier déjà téléchargé (skip) | Aucune barre créée, message silencieux |
| 1 seule URL, depth=0, mode texte/HTML | Barre globale `1/1` → 100% immédiatement, aucune barre unitaire |

---

## Principe de rétrocompatibilité

`progress` est `None` par défaut dans **toutes** les signatures modifiées. Le code existant fonctionne sans changement si `progress` n'est pas fourni. Les blocs rich sont tous gardés derrière un `if progress:`.

---

## Dépendance

```
pip install rich
```

À ajouter dans la documentation d'installation du projet.
