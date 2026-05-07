# tests/test_runner_pages.py
import queue
from core.runner import ScraperRunner


def test_runner_done_includes_pages():
    def fake_crawl(url, modes, dest, depth, session, visited, log, cancel_event):
        visited.add("https://example.com/")
        visited.add("https://example.com/page2")

    q = queue.Queue()
    runner = ScraperRunner(
        url="https://example.com/", modes=[1], depth=0,
        log_queue=q, _crawl_fn=fake_crawl,
    )
    runner.start()
    runner._thread.join(timeout=5)

    messages = []
    while not q.empty():
        messages.append(q.get_nowait())

    done = next((m for m in messages if isinstance(m, dict) and m.get("type") == "done"), None)
    assert done is not None
    assert done["pages"] == 2
