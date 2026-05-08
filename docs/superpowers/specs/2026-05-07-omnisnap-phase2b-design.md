# OmniSnap Phase 2b — Notifications Toast Windows

**Date :** 2026-05-07  
**Statut :** Approuvé  
**Scope :** Notifications Windows toast à la fin d'un scraping

---

## Objectif

Envoyer une notification toast Windows à l'utilisateur quand un scraping se termine (succès ou erreur), même si l'application est minimisée ou en arrière-plan.

---

## Bibliothèque retenue : `winotify`

- Bibliothèque Python légère (~50 KB), pas de dépendance lourde
- Envoie de vrais toasts Windows 10/11 via l'API WinRT
- Compatible PyInstaller (bundlable dans l'exe existant)
- Try/except silencieux : si `winotify` échoue, le scraping ne crashe pas

---

## Événements déclencheurs

| Événement | Déclenche un toast ? |
|-----------|----------------------|
| `done`    | Oui                  |
| `error`   | Oui                  |
| `cancelled` | Non                |

---

## Contenu des toasts

| Événement | Titre | Message |
|-----------|-------|---------|
| `done`    | `✅ Scraping terminé` | `{n} fichiers · {netloc}` |
| `error`   | `❌ Erreur OmniSnap`  | `{netloc} — {message[:80]}` |

- `netloc` = domaine extrait de l'URL via `urllib.parse.urlparse` (ex. `example.com`)
- Message d'erreur tronqué à 80 caractères
- `app_id` = `"OmniSnap"` — nom affiché dans le centre de notifications Windows

---

## Architecture

### Nouveau fichier

**`core/notifier.py`**

```python
from urllib.parse import urlparse
try:
    from winotify import Notification
    _WINOTIFY_OK = True
except ImportError:
    _WINOTIFY_OK = False


def notify(event: str, url: str, result: dict) -> None:
    """Envoie un toast Windows si winotify est disponible. Silencieux en cas d'échec."""
    if not _WINOTIFY_OK:
        return
    try:
        netloc = urlparse(url).netloc or url[:40]
        if event == "done":
            n = result.get("file_count", 0)
            toast = Notification(
                app_id="OmniSnap",
                title="✅ Scraping terminé",
                msg=f"{n} fichiers · {netloc}",
            )
        elif event == "error":
            msg = result.get("error_msg", "Erreur inconnue")[:80]
            toast = Notification(
                app_id="OmniSnap",
                title="❌ Erreur OmniSnap",
                msg=f"{netloc} — {msg}",
            )
        else:
            return
        toast.show()
    except Exception:
        pass
```

### Fichiers modifiés

**`core/store.py`**
- Ajouter `"notifications": True` dans `_DEFAULT_SETTINGS`

**`gui/settings_view.py`**
- Ajouter un switch `CTkSwitch` "Notifications Windows" dans la section **Comportement**, sous le switch "Ouvrir le dossier"
- Label principal : `"Notifications Windows"`
- Label secondaire : `"Avertissement en bas à droite de l'écran quand un scraping se termine"`
- Connecté à `store.save_settings({"notifications": bool})`

**`gui/app.py`**
- Importer `core.notifier.notify`
- Dans `_on_scrape_done()`, après `self._store.add_entry(entry)` :
  ```python
  if self._store.get_settings().get("notifications", True):
      notify(result["status"], result["url"], result)
  ```

---

## Tests (`tests/test_notifier.py`, 6 tests)

| # | Test |
|---|------|
| 1 | Toast `done` : titre et message corrects |
| 2 | Toast `error` : titre et message corrects |
| 3 | Message d'erreur tronqué à 80 chars |
| 4 | Aucun toast si `notifications=False` (vérifié via mock dans app.py) |
| 5 | `netloc` correctement extrait de l'URL |
| 6 | Aucune exception propagée si `winotify` lève une erreur |

Les tests mockent `winotify.Notification` via `unittest.mock.patch`.

---

## Dépendances

```
winotify>=1.0
```

Ajouter dans `requirements.txt` et dans la section `hiddenimports` ou `datas` du `.spec` PyInstaller si nécessaire.

---

## Phases suivantes

- **Phase 3** : File d'attente multi-URL + installateur Inno Setup  
  *(bouton "Ouvrir le dossier" dans le toast pourra être ajouté via `windows-toasts` à ce moment)*
