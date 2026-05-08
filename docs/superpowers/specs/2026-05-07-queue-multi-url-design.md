# File d'attente multi-URL (Phase 3) — Design Spec

## Objectif

Permettre à l'utilisateur d'ajouter des tâches de scraping pendant qu'une tâche est en cours d'exécution. Les tâches s'exécutent automatiquement l'une après l'autre, chacune avec ses propres paramètres (URL, modes, profondeur, cookies).

---

## Architecture

### Fichiers nouveaux

| Fichier | Responsabilité |
|---|---|
| `core/queue.py` | `QueuedTask` dataclass + `QueueManager` (logique pure, sans GUI) |
| `gui/queue_view.py` | Panel liste des tâches en attente |
| `tests/test_queue.py` | Tests unitaires de `QueueManager` |

### Fichiers modifiés

| Fichier | Changement |
|---|---|
| `gui/sidebar.py` | Méthode `update_badge(count, show_see_list)` + callback `on_badge_click` |
| `gui/scrape_view.py` | Bouton "➕ Ajouter une tâche" à côté d'Annuler, visible seulement pendant le scrape actif |
| `gui/wizard.py` | Mode `enqueue` : `set_enqueue_mode()`, bouton step 4 conditionnel |
| `gui/app.py` | Orchestration : câble badge, queue_view, wizard mode, auto-start |

### Ce qui ne change pas

- `core/store.py` — la file n'est pas persistée (volatile, perdue à la fermeture)
- `core/runner.py`, `core/notifier.py` — aucun changement

---

## Modèle de données

### `QueuedTask`

```python
from dataclasses import dataclass

@dataclass
class QueuedTask:
    id: str           # uuid4, généré à la création
    url: str
    modes: list[int]
    depth: int
    cookies_path: str | None
```

### `QueueManager`

```python
class QueueManager:
    def add(self, task: QueuedTask) -> None      # ajoute en fin de file
    def remove(self, task_id: str) -> None       # supprime par id
    def clear(self) -> None                      # vide la file
    def next(self) -> QueuedTask | None          # pop index 0, None si vide
    def all(self) -> list[QueuedTask]            # copie lecture seule
    def count(self) -> int
```

---

## Flux utilisateur

### Ajouter une tâche pendant un scrape

1. ScrapeView visible → bouton **"➕ Ajouter une tâche"** visible à côté d'Annuler (dans la zone header, masqué dès que le scrape se termine)
2. Clic → `App._show_wizard_enqueue()` → Wizard reset + `set_enqueue_mode(True)`
3. Wizard step 4 : bouton **"➕ Ajouter aux tâches en attente"** remplace "▶ Lancer"
4. Confirmation → `App._enqueue(url, modes, depth, cookies_path)`
5. `QueueManager.add(QueuedTask(...))` → `App._refresh_badge()`
6. `App._show_scrape_view()` → retour au log en cours

### Badge sidebar

- `count == 0` → badge masqué
- `count > 0, show_see_list=True` (ScrapeView active) → badge vert : chiffre + "Tâche(s) en attente" + "▼ Voir la liste" (cliquable)
- `count > 0, show_see_list=False` (QueueView active) → badge vert : chiffre + "Tâche(s) en attente" seulement (bordure épaisse active)

`App` passe le flag `show_see_list` — Sidebar ne décide pas elle-même.

### Voir et gérer la file

1. Clic badge ou "▼ Voir la liste" → `App._show_queue_view()`
2. QueueView visible : liste des tâches + actions par tâche
   - **✎ Modifier** : `QueueManager.remove(id)` + wizard prefill en mode enqueue → nouvelle tâche ajoutée en fin de file
   - **✕ Supprimer** : `QueueManager.remove(id)` → refresh
   - **➕ Ajouter une autre URL** : `App._show_wizard_enqueue()`
   - **🗑 Vider la file** : `QueueManager.clear()` → badge disparaît
3. Bouton **"✕ Fermer"** en haut à droite → `App._show_scrape_view()`

### Auto-start à la fin d'un scrape

Dans `App._on_scrape_done()`, après sauvegarde historique :

```python
next_task = self._queue.next()
if next_task:
    self._launch_queued(next_task)
```

Déclenché pour **tous les statuts** : `done`, `error`, `cancelled`. Si le user annule la tâche en cours, la suivante démarre quand même. Pour tout stopper, il faut vider la file avant d'annuler.

---

## Comportements de bord

| Situation | Comportement |
|---|---|
| File vide à la fin d'un scrape | `next()` → `None`, rien ne se passe, comportement actuel inchangé |
| Modifier une tâche en attente | Supprime l'ancienne, ajoute la nouvelle en fin de file (pas de réordonnancement) |
| Scrape auto-start pendant que QueueView est ouverte | `_launch_queued()` appelle `_show_scrape_view()`, QueueView cachée, badge repasse en mode `show_see_list=True` |
| Bouton "➕ Ajouter" cliqué depuis QueueView | Ferme QueueView, ouvre Wizard mode enqueue, retour à ScrapeView après enqueue (pas à QueueView) |
| App fermée avec file non vide | File perdue — comportement acceptable en v1 |

---

## Tests

`tests/test_queue.py` couvre la logique pure de `QueueManager` :
- `add` → `count` augmente, `all()` retourne la tâche
- `remove` par id → tâche absente, count -1
- `remove` id inexistant → silencieux
- `next` → retourne et retire le premier élément
- `next` sur file vide → `None`
- `clear` → count == 0, `all()` == []
- Ordre FIFO : add A, add B → `next()` retourne A

Les comportements GUI (badge, auto-start, navigation) sont validés manuellement — trop coûteux à mocker avec CustomTkinter.
