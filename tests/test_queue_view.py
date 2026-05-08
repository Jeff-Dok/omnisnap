import pytest


def test_import():
    from gui.queue_view import QueueView


def test_instantiation(ctk_root):
    from gui.queue_view import QueueView
    view = QueueView(
        ctk_root,
        on_close=lambda: None,
        on_edit=lambda t: None,
        on_remove=lambda t: None,
        on_add=lambda: None,
        on_clear=lambda: None,
    )
    assert view is not None


def test_refresh_empty(ctk_root):
    from gui.queue_view import QueueView
    view = QueueView(
        ctk_root,
        on_close=lambda: None,
        on_edit=lambda t: None,
        on_remove=lambda t: None,
        on_add=lambda: None,
        on_clear=lambda: None,
    )
    view.refresh([])


def test_refresh_with_tasks(ctk_root):
    from gui.queue_view import QueueView
    from core.queue import QueuedTask
    tasks = [
        QueuedTask(url="https://python.org", modes=[1, 5, 7], depth=2, cookies_path=None),
        QueuedTask(url="https://libreoffice.org", modes=[1, 2, 3, 4], depth=0, cookies_path=None),
    ]
    view = QueueView(
        ctk_root,
        on_close=lambda: None,
        on_edit=lambda t: None,
        on_remove=lambda t: None,
        on_add=lambda: None,
        on_clear=lambda: None,
    )
    view.refresh(tasks)
