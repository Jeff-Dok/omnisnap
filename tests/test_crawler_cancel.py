import threading
import time
from pathlib import Path
import requests_mock as req_mock
from scraper_modules.crawler import crawl


def test_cancel_event_stops_crawl(tmp_path):
    cancel = threading.Event()
    visited = set()
    session = __import__('requests').Session()

    with req_mock.Mocker() as m:
        m.get("https://example.com/", text="<html><body>hello</body></html>")
        cancel.set()  # annulé d'avance
        crawl(
            url="https://example.com/",
            modes=[1],
            dest=tmp_path,
            depth=0,
            session=session,
            visited=visited,
            cancel_event=cancel,
        )

    assert len(visited) == 0  # crawl s'est arrêté avant de traiter


def test_cancel_event_none_runs_normally(tmp_path):
    visited = set()
    session = __import__('requests').Session()

    with req_mock.Mocker() as m:
        m.get("https://example.com/", text="<html><body>hello</body></html>")
        crawl(
            url="https://example.com/",
            modes=[1],
            dest=tmp_path,
            depth=0,
            session=session,
            visited=visited,
            cancel_event=None,
        )

    assert "https://example.com/" in visited
