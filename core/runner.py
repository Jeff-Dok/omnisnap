# core/runner.py
import http.cookiejar
import queue
import threading
from pathlib import Path

import requests

from scraper_modules.exporter import url_to_folder, DEFAULT_DEST


class ScraperRunner:
    def __init__(
        self,
        url: str,
        modes: list[int],
        depth: int,
        log_queue: queue.Queue,
        dest_base: Path | None = None,
        cookies_path: str | None = None,
        respect_robots: bool = False,
        url_filter: str = "",
        use_playwright: bool = False,
        playwright_opts: dict | None = None,
        img_ext_filter: set | None = None,
        vid_ext_filter: set | None = None,
        aud_ext_filter: set | None = None,
        doc_ext_filter: set | None = None,
        arc_ext_filter: set | None = None,
        _crawl_fn=None,
    ):
        self.url = url
        self.modes = modes
        self.depth = depth
        self.log_queue = log_queue
        self.dest_base = Path(dest_base) if dest_base else DEFAULT_DEST
        self.cookies_path = cookies_path
        self.respect_robots = respect_robots
        self.url_filter = url_filter
        self.use_playwright = use_playwright
        self.playwright_opts = playwright_opts or {}
        self.img_ext_filter = img_ext_filter
        self.vid_ext_filter = vid_ext_filter
        self.aud_ext_filter = aud_ext_filter
        self.doc_ext_filter = doc_ext_filter
        self.arc_ext_filter = arc_ext_filter
        self._cancel_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._crawl_fn = _crawl_fn  # injectable pour tests

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("ScraperRunner is already running")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancel_event.set()

    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _run(self):
        try:
            url_dest = self.dest_base / url_to_folder(self.url)
            session = requests.Session()

            if self.cookies_path:
                self._load_cookies(session, self.cookies_path)

            visited: set = set()
            crawl_fn = self._crawl_fn or self._default_crawl
            crawl_fn(
                url=self.url,
                modes=self.modes,
                dest=url_dest,
                depth=self.depth,
                session=session,
                visited=visited,
                log=self._log,
                cancel_event=self._cancel_event,
                respect_robots=self.respect_robots,
                url_filter=self.url_filter,
                use_playwright=self.use_playwright,
                playwright_opts=self.playwright_opts,
                img_ext_filter=self.img_ext_filter,
                vid_ext_filter=self.vid_ext_filter,
                aud_ext_filter=self.aud_ext_filter,
                doc_ext_filter=self.doc_ext_filter,
                arc_ext_filter=self.arc_ext_filter,
            )

            if self._cancel_event.is_set():
                self.log_queue.put({"type": "cancelled"})
                return

            files, size_bytes = self._count_output(url_dest)
            self.log_queue.put({
                "type": "done",
                "dest": str(url_dest),
                "files": files,
                "size_bytes": size_bytes,
                "pages": len(visited),
            })

        except Exception as exc:
            self.log_queue.put({"type": "error", "message": str(exc)})

    @staticmethod
    def _default_crawl(**kwargs):
        from scraper_modules.crawler import crawl
        crawl(**kwargs)

    @staticmethod
    def _load_cookies(session: requests.Session, path: str) -> list[dict]:
        jar = http.cookiejar.MozillaCookieJar(path)
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except Exception as e:
            return []
        session.cookies.update(jar)
        return [
            {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
            for c in jar
        ]

    @staticmethod
    def _count_output(dest: Path) -> tuple[int, int]:
        if not dest.exists():
            return 0, 0
        files = [f for f in dest.rglob("*") if f.is_file()]
        return len(files), sum(f.stat().st_size for f in files)
