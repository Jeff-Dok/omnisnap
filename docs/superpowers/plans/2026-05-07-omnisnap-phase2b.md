# OmniSnap Phase 2b — Notifications Toast Windows — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Envoyer une notification toast Windows quand un scraping se termine (succès ou erreur), avec un toggle ON/OFF dans les Paramètres.

**Architecture:** Nouveau module `core/notifier.py` qui wrappé `winotify`. `app.py` l'appelle depuis `_on_scrape_done()` si le setting `notifications` est activé. Les tests mockent `winotify.Notification` au niveau module pour éviter la dépendance réelle en test.

**Tech Stack:** Python 3.11, winotify>=1.0, unittest.mock, pytest

---

## Fichiers touchés

| Fichier | Action |
|---------|--------|
| `core/notifier.py` | Créer |
| `tests/test_notifier.py` | Créer |
| `core/store.py` | Modifier — ajouter `"notifications": True` dans `_DEFAULT_SETTINGS` |
| `tests/test_store.py` | Modifier — ajouter 1 test |
| `gui/settings_view.py` | Modifier — ajouter switch dans section Comportement |
| `gui/app.py` | Modifier — appeler `notify()` dans `_on_scrape_done()` + import |
| `requirements.txt` | Créer |
| `build/OmniSnap.spec` | Modifier — ajouter hiddenimports winotify |

---

## Task 1 : `core/notifier.py` — module toast (TDD)

**Files:**
- Create: `tests/test_notifier.py`
- Create: `core/notifier.py`

- [ ] **Step 1 : Écrire les 6 tests (tous en échec)**

Créer `tests/test_notifier.py` :

```python
from unittest.mock import MagicMock, patch
import core.notifier as notifier_mod


def _notify(event, url, result, notif_cls):
    with patch.object(notifier_mod, '_WINOTIFY_OK', True), \
         patch.object(notifier_mod, 'Notification', notif_cls):
        notifier_mod.notify(event, url, result)


def test_done_titre_et_message():
    mock_cls = MagicMock()
    _notify("done", "https://example.com/path", {"file_count": 42}, mock_cls)
    mock_cls.assert_called_once_with(
        app_id="OmniSnap",
        title="✅ Scraping terminé",
        msg="42 fichiers · example.com",
    )
    mock_cls.return_value.show.assert_called_once()


def test_error_titre_et_message():
    mock_cls = MagicMock()
    _notify("error", "https://example.com", {"error_msg": "Connexion refusée"}, mock_cls)
    mock_cls.assert_called_once_with(
        app_id="OmniSnap",
        title="❌ Erreur OmniSnap",
        msg="example.com — Connexion refusée",
    )
    mock_cls.return_value.show.assert_called_once()


def test_error_message_tronque_a_80_chars():
    mock_cls = MagicMock()
    long_msg = "X" * 120
    _notify("error", "https://example.com", {"error_msg": long_msg}, mock_cls)
    _, kwargs = mock_cls.call_args
    assert kwargs["msg"] == f"example.com — {'X' * 80}"


def test_netloc_extrait_de_url():
    mock_cls = MagicMock()
    _notify("done", "https://sub.domain.org/page?q=1", {"file_count": 5}, mock_cls)
    _, kwargs = mock_cls.call_args
    assert "sub.domain.org" in kwargs["msg"]


def test_pas_exception_si_notification_plante():
    mock_cls = MagicMock(side_effect=RuntimeError("winotify crashed"))
    _notify("done", "https://example.com", {"file_count": 1}, mock_cls)  # ne doit pas lever


def test_cancelled_ne_declenche_pas_toast():
    mock_cls = MagicMock()
    _notify("cancelled", "https://example.com", {}, mock_cls)
    mock_cls.assert_not_called()
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```
cd C:\Users\jnfra\OneDrive\Documents\web_projet\scraper_app
pytest tests/test_notifier.py -v
```

Attendu : `ModuleNotFoundError: No module named 'core.notifier'` ou erreur similaire.

- [ ] **Step 3 : Créer `core/notifier.py`**

```python
from urllib.parse import urlparse

try:
    from winotify import Notification
    _WINOTIFY_OK = True
except ImportError:
    Notification = None  # type: ignore
    _WINOTIFY_OK = False


def notify(event: str, url: str, result: dict) -> None:
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
            raw = result.get("error_msg") or "Erreur inconnue"
            toast = Notification(
                app_id="OmniSnap",
                title="❌ Erreur OmniSnap",
                msg=f"{netloc} — {raw[:80]}",
            )
        else:
            return
        toast.show()
    except Exception:
        pass
```

- [ ] **Step 4 : Vérifier que les 6 tests passent**

```
pytest tests/test_notifier.py -v
```

Attendu : 6 PASSED

- [ ] **Step 5 : Commiter**

```
git add core/notifier.py tests/test_notifier.py
git commit -m "feat: core/notifier.py — toast Windows via winotify"
```

---

## Task 2 : `core/store.py` — ajouter clé `notifications`

**Files:**
- Modify: `core/store.py:8`
- Modify: `tests/test_store.py`

- [ ] **Step 1 : Ajouter le test (en échec)**

Ouvrir `tests/test_store.py` et ajouter après `test_settings_defaults` :

```python
def test_settings_defaults_notifications(store):
    assert store.get_settings()["notifications"] is True
```

- [ ] **Step 2 : Vérifier que le test échoue**

```
pytest tests/test_store.py::test_settings_defaults_notifications -v
```

Attendu : FAIL — `KeyError: 'notifications'`

- [ ] **Step 3 : Ajouter la clé dans `_DEFAULT_SETTINGS`**

Dans `core/store.py`, ligne 8, remplacer :

```python
_DEFAULT_SETTINGS: dict = {"theme": "dark", "dest_dir": "", "auto_open": False}
```

par :

```python
_DEFAULT_SETTINGS: dict = {"theme": "dark", "dest_dir": "", "auto_open": False, "notifications": True}
```

- [ ] **Step 4 : Vérifier que tous les tests store passent**

```
pytest tests/test_store.py -v
```

Attendu : tous PASSED (les tests existants ne brisent pas — ils ne vérifient pas l'absence de clés inconnues)

- [ ] **Step 5 : Commiter**

```
git add core/store.py tests/test_store.py
git commit -m "feat: store — clé notifications activée par défaut"
```

---

## Task 3 : `gui/settings_view.py` — toggle Notifications

**Files:**
- Modify: `gui/settings_view.py`

Pas de test automatisé — c'est du code GUI pur. Tester visuellement après Task 4.

- [ ] **Step 1 : Ajouter `_switch_notif` dans `_build()`**

Dans `gui/settings_view.py`, dans la méthode `_build()`, après le bloc du switch `_switch_auto` (autour de la ligne 82, avant `self._div(body)`), ajouter ce bloc :

```python
        notif_row = ctk.CTkFrame(body, fg_color="transparent")
        notif_row.pack(fill="x", pady=(0, 16))
        notif_info = ctk.CTkFrame(notif_row, fg_color="transparent")
        notif_info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(notif_info, text="Notifications Windows",
                     font=T.FONT_NORMAL, text_color=T.TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(
            notif_info,
            text="Avertissement en bas à droite de l'écran quand un scraping se termine",
            font=T.FONT_SMALL, text_color=T.TEXT_DIM, anchor="w",
        ).pack(fill="x")
        self._switch_notif = ctk.CTkSwitch(
            notif_row, text="",
            fg_color=T.BORDER, progress_color=T.ACCENT,
            command=self._on_notif_toggle,
        )
        self._switch_notif.pack(side="right", padx=(16, 0))
```

- [ ] **Step 2 : Ajouter `_on_notif_toggle()` comme méthode de la classe**

Après `_on_auto_toggle`, ajouter :

```python
    def _on_notif_toggle(self) -> None:
        self._store.save_settings({"notifications": bool(self._switch_notif.get())})
```

- [ ] **Step 3 : Mettre à jour `refresh()`**

Dans la méthode `refresh()`, après la ligne `self._switch_auto.deselect()`, ajouter :

```python
        if settings.get("notifications", True):
            self._switch_notif.select()
        else:
            self._switch_notif.deselect()
```

- [ ] **Step 4 : Commiter**

```
git add gui/settings_view.py
git commit -m "feat: settings — toggle notifications Windows"
```

---

## Task 4 : `gui/app.py` — brancher `notify()`

**Files:**
- Modify: `gui/app.py`

- [ ] **Step 1 : Ajouter l'import**

En haut de `gui/app.py`, après `from core.store import AppStore`, ajouter :

```python
from core.notifier import notify
```

- [ ] **Step 2 : Appeler `notify()` dans `_on_scrape_done()`**

Dans `_on_scrape_done()`, après `self._store.add_entry(entry)` (ligne ~118), ajouter :

```python
        if self._store.get_settings().get("notifications", True):
            notify(result["status"], result["url"], result)
```

Le bloc `_on_scrape_done` doit ressembler à ceci après modification :

```python
    def _on_scrape_done(self, result: dict):
        entry = {
            "id": str(uuid.uuid4()),
            "url": result["url"],
            "modes": result["modes"],
            "depth": result["depth"],
            "status": result["status"],
            "date": datetime.datetime.now().isoformat(timespec="seconds"),
            "pages": result.get("pages", 0),
            "file_count": result.get("file_count", 0),
            "size_mb": result.get("size_mb", 0.0),
            "dest_path": result.get("dest_path", ""),
            "error_msg": result.get("error_msg"),
        }
        self._store.add_entry(entry)
        if self._store.get_settings().get("notifications", True):
            notify(result["status"], result["url"], result)
        if result["status"] == "done" and self._store.get_settings().get("auto_open"):
            dest = entry["dest_path"]
            if dest:
                try:
                    os.startfile(dest)
                except Exception:
                    pass
```

- [ ] **Step 3 : Lancer tous les tests**

```
pytest tests/ -v
```

Attendu : 46 + 7 (6 notifier + 1 store) = **53 PASSED**

- [ ] **Step 4 : Commiter**

```
git add gui/app.py
git commit -m "feat: app — déclencher notify() à la fin du scraping"
```

---

## Task 5 : Dépendances + PyInstaller spec

**Files:**
- Create: `requirements.txt`
- Modify: `build/OmniSnap.spec`

- [ ] **Step 1 : Créer `requirements.txt`**

Créer à la racine du projet (`scraper_app/requirements.txt`) :

```
customtkinter>=5.2.0
requests>=2.31.0
beautifulsoup4>=4.12.0
winotify>=1.0
```

*(playwright et yt-dlp sont optionnels — ne pas les inclure ici)*

- [ ] **Step 2 : Installer winotify**

```
pip install winotify
```

Attendu : `Successfully installed winotify-1.0` (ou version plus récente)

- [ ] **Step 3 : Ajouter `winotify` et `core.notifier` dans `build/OmniSnap.spec`**

Dans `build/OmniSnap.spec`, dans la liste `hiddenimports`, ajouter après `'gui.theme'` :

```python
        'core.notifier',
        'core.store',
        'core.runner',
        'gui.history_view',
        'gui.settings_view',
        'winotify',
```

*(remplacer entièrement le bloc hiddenimports existant)*

Le bloc complet doit être :

```python
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._imagingtk',
        'scraper_modules.crawler',
        'scraper_modules.downloader',
        'scraper_modules.exporter',
        'scraper_modules.detector',
        'scraper_modules.session',
        'scraper_modules.mediawiki',
        'scraper_modules.progress',
        'core.runner',
        'core.store',
        'core.notifier',
        'gui.app',
        'gui.sidebar',
        'gui.wizard',
        'gui.scrape_view',
        'gui.history_view',
        'gui.settings_view',
        'gui.theme',
        'winotify',
    ],
```

- [ ] **Step 4 : Lancer tous les tests une dernière fois**

```
pytest tests/ -v
```

Attendu : **53 PASSED**

- [ ] **Step 5 : Commiter**

```
git add requirements.txt build/OmniSnap.spec
git commit -m "chore: winotify dans requirements.txt et OmniSnap.spec"
```

- [ ] **Step 6 : Push**

```
git push
```

---

## Vérification manuelle finale

Lancer l'app en dev :

```
python main.py
```

1. Faire un scrape rapide (ex. `https://example.com`, mode Texte, profondeur 0)
2. Vérifier qu'un toast apparaît en bas à droite avec `✅ Scraping terminé` et le nombre de fichiers
3. Aller dans Paramètres → Comportement → désactiver "Notifications Windows"
4. Refaire un scrape → vérifier qu'aucun toast n'apparaît
5. Réactiver → vérifier que le toast revient
