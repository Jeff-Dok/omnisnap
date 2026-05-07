# tests/test_runner.py
import queue
import threading
import time
from pathlib import Path
from core.runner import ScraperRunner


def _fake_crawl_ok(**kwargs):
    kwargs['log']("✓ page test")


def _fake_crawl_slow(**kwargs):
    cancel_event = kwargs.get('cancel_event')
    for _ in range(50):
        if cancel_event and cancel_event.is_set():
            return
        kwargs['log']("✓ page")
        time.sleep(0.02)


def _fake_crawl_error(**kwargs):
    raise RuntimeError("Erreur réseau simulée")


def test_runner_done_message(tmp_path):
    q = queue.Queue()
    runner = ScraperRunner(
        url="https://example.com",
        modes=[1],
        depth=0,
        dest_base=tmp_path,
        log_queue=q,
        _crawl_fn=_fake_crawl_ok,
    )
    runner.start()
    runner._thread.join(timeout=5)

    messages = []
    while not q.empty():
        messages.append(q.get_nowait())

    done = next((m for m in messages if isinstance(m, dict) and m.get("type") == "done"), None)
    assert done is not None
    assert "dest" in done


def test_runner_log_forwarded(tmp_path):
    q = queue.Queue()
    runner = ScraperRunner(
        url="https://example.com",
        modes=[1],
        depth=0,
        dest_base=tmp_path,
        log_queue=q,
        _crawl_fn=_fake_crawl_ok,
    )
    runner.start()
    runner._thread.join(timeout=5)

    messages = [m for m in list(q.queue) if isinstance(m, str)]
    assert any("page test" in m for m in messages)


def test_runner_cancel(tmp_path):
    q = queue.Queue()
    runner = ScraperRunner(
        url="https://example.com",
        modes=[1],
        depth=0,
        dest_base=tmp_path,
        log_queue=q,
        _crawl_fn=_fake_crawl_slow,
    )
    runner.start()
    time.sleep(0.05)
    runner.cancel()
    runner._thread.join(timeout=3)

    assert not runner._thread.is_alive()
    messages = list(q.queue)
    cancelled = any(isinstance(m, dict) and m.get("type") == "cancelled" for m in messages)
    assert cancelled


def test_runner_error(tmp_path):
    q = queue.Queue()
    runner = ScraperRunner(
        url="https://example.com",
        modes=[1],
        depth=0,
        dest_base=tmp_path,
        log_queue=q,
        _crawl_fn=_fake_crawl_error,
    )
    runner.start()
    runner._thread.join(timeout=5)

    messages = list(q.queue)
    error = next((m for m in messages if isinstance(m, dict) and m.get("type") == "error"), None)
    assert error is not None
    assert "Erreur réseau" in error["message"]
