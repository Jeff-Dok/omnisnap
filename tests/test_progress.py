# tests/test_progress.py
from rich.progress import Progress


def test_make_progress_returns_progress_instance():
    from scraper_modules.progress import make_progress
    p = make_progress()
    assert isinstance(p, Progress)


def test_make_progress_has_required_columns():
    from scraper_modules.progress import make_progress
    from rich.progress import (
        SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn,
        TransferSpeedColumn, DownloadColumn, TimeRemainingColumn,
    )
    p = make_progress()
    column_types = [type(c) for c in p.columns]
    assert SpinnerColumn in column_types
    assert TextColumn in column_types
    assert BarColumn in column_types
    assert TaskProgressColumn in column_types
    assert TransferSpeedColumn in column_types
    assert DownloadColumn in column_types
    assert TimeRemainingColumn in column_types
    assert len(p.columns) == 7


from unittest.mock import MagicMock, call


def _make_mock_session(content=b"data", content_length="4"):
    session = MagicMock()
    resp = MagicMock()
    resp.headers = {"Content-Length": content_length} if content_length else {}
    resp.iter_content.return_value = [content]
    resp.raise_for_status.return_value = None
    session.get.return_value = resp
    return session


def test_download_files_no_progress_regression(tmp_path):
    """progress=None doit fonctionner exactement comme avant."""
    from scraper_modules.crawler import _download_files
    session = _make_mock_session()
    seen = set()
    count = _download_files(
        ["https://example.com/report.pdf"],
        tmp_path, session, seen, ext_filter=None, label="doc"
    )
    assert count == 1
    assert (tmp_path / "report.pdf").exists()


def test_download_files_with_progress_calls_advance(tmp_path):
    """Avec progress, add_task/advance/remove_task doivent être appelés."""
    from scraper_modules.crawler import _download_files
    session = _make_mock_session(content=b"x" * 100, content_length="100")
    seen = set()
    progress = MagicMock()
    progress.add_task.return_value = 42
    count = _download_files(
        ["https://example.com/archive.zip"],
        tmp_path, session, seen, ext_filter=None, label="archive",
        progress=progress
    )
    assert count == 1
    progress.add_task.assert_called_once_with("archive.zip", total=100)
    progress.advance.assert_called_once_with(42, 100)
    progress.remove_task.assert_called_once_with(42)


def test_download_files_no_content_length(tmp_path):
    """Sans Content-Length, total doit être None (barre indéterminée)."""
    from scraper_modules.crawler import _download_files
    session = _make_mock_session(content_length=None)
    seen = set()
    progress = MagicMock()
    progress.add_task.return_value = 0
    _download_files(
        ["https://example.com/doc.pdf"],
        tmp_path, session, seen, ext_filter=None, label="doc",
        progress=progress
    )
    progress.add_task.assert_called_once_with("doc.pdf", total=None)


def test_download_videos_with_progress(tmp_path):
    from scraper_modules.crawler import _download_videos
    session = _make_mock_session(content=b"v" * 200, content_length="200")
    progress = MagicMock()
    progress.add_task.return_value = 7
    count = _download_videos(
        ["https://cdn.example.com/clip.mp4"],
        tmp_path, session, progress=progress
    )
    assert count == 1
    progress.add_task.assert_called_once_with("clip.mp4", total=200)
    progress.remove_task.assert_called_once_with(7)
    progress.advance.assert_called_once_with(7, 200)


def test_download_audios_with_progress(tmp_path):
    from scraper_modules.crawler import _download_audios
    session = _make_mock_session(content=b"a" * 50, content_length="50")
    progress = MagicMock()
    progress.add_task.return_value = 3
    count = _download_audios(
        ["https://cdn.example.com/track.mp3"],
        tmp_path, session, progress=progress
    )
    assert count == 1
    progress.add_task.assert_called_once_with("track.mp3", total=50)
    progress.remove_task.assert_called_once_with(3)
    progress.advance.assert_called_once_with(3, 50)


def test_download_videos_no_progress_regression(tmp_path):
    from scraper_modules.crawler import _download_videos
    session = _make_mock_session()
    count = _download_videos(["https://cdn.example.com/clip.mp4"], tmp_path, session)
    assert count == 1
    assert (tmp_path / "clip.mp4").exists()


def test_crawl_updates_task_url_description(tmp_path):
    """crawl() doit mettre à jour la description de task_url à chaque page visitée."""
    from unittest.mock import patch
    from scraper_modules.crawler import crawl

    html = "<html><body><p>Hello</p></body></html>"
    session = MagicMock()
    resp = MagicMock()
    resp.text = html
    resp.url = "https://example.com/"
    resp.raise_for_status.return_value = None
    session.get.return_value = resp

    progress = MagicMock()
    task_url = 5

    crawl(
        url="https://example.com/",
        modes=[1],
        dest=tmp_path,
        depth=0,
        session=session,
        visited=set(),
        progress=progress,
        task_url=task_url,
    )

    progress.update.assert_called_with(
        task_url,
        description="example.com — 1 page visitée"
    )


from scraper_modules.session import MIN_SIZE_DOC_ARCHIVE, MIN_SIZE_VIDEO_AUDIO
from scraper_modules.crawler import _download_files, _download_videos, _download_audios


def test_download_files_skips_complete_file(tmp_path):
    dest = tmp_path / "archives"
    dest.mkdir()
    out = dest / "archive.zip"
    out.write_bytes(b"x" * MIN_SIZE_DOC_ARCHIVE)
    session = MagicMock()
    count = _download_files(
        ["http://example.com/archive.zip"],
        dest, session, set(), ext_filter=None, label="archive"
    )
    assert count == 0
    session.get.assert_not_called()


def test_download_files_redownloads_partial_file(tmp_path):
    dest = tmp_path / "archives"
    dest.mkdir()
    out = dest / "archive.zip"
    out.write_bytes(b"x" * 10)
    session = MagicMock()
    r = MagicMock()
    r.headers = {}
    r.iter_content.return_value = [b"x" * MIN_SIZE_DOC_ARCHIVE]
    session.get.return_value = r
    count = _download_files(
        ["http://example.com/archive.zip"],
        dest, session, set(), ext_filter=None, label="archive"
    )
    assert count == 1
    session.get.assert_called_once()


def test_download_videos_redownloads_partial_file(tmp_path):
    dest = tmp_path / "videos"
    dest.mkdir()
    out = dest / "video.mp4"
    out.write_bytes(b"x" * 100)
    session = MagicMock()
    r = MagicMock()
    r.headers = {}
    r.iter_content.return_value = [b"x" * MIN_SIZE_VIDEO_AUDIO]
    session.get.return_value = r
    count = _download_videos(["http://example.com/video.mp4"], dest, session)
    assert count == 1
    session.get.assert_called_once()


def test_download_audios_redownloads_partial_file(tmp_path):
    dest = tmp_path / "audios"
    dest.mkdir()
    out = dest / "audio.mp3"
    out.write_bytes(b"x" * 100)
    session = MagicMock()
    r = MagicMock()
    r.headers = {}
    r.iter_content.return_value = [b"x" * MIN_SIZE_VIDEO_AUDIO]
    session.get.return_value = r
    count = _download_audios(["http://example.com/audio.mp3"], dest, session)
    assert count == 1
    session.get.assert_called_once()


from scraper_modules.crawler import crawl


def test_crawl_saves_session_after_page(tmp_path):
    session = MagicMock()
    r = MagicMock()
    r.url = "http://example.com/"
    r.text = "<html><body>Hello</body></html>"
    session.get.return_value = r

    sessions_dir = tmp_path / "sessions"
    session_data = {
        "url": "http://example.com/",
        "dest": str(tmp_path),
        "modes": [1],
        "completed": False,
        "visited": [],
        "started_at": "2026-05-07T10:00:00",
        "completed_at": None,
    }

    crawl(
        url="http://example.com/",
        modes=[1],
        dest=tmp_path,
        depth=0,
        session=session,
        visited=set(),
        session_data=session_data,
        sessions_dir=sessions_dir,
    )

    assert "http://example.com/" in session_data["visited"]
    assert sessions_dir.exists()
    assert len(list(sessions_dir.glob("*.json"))) == 1


def test_crawl_skips_visited_urls(tmp_path):
    session = MagicMock()
    crawl(
        url="http://example.com/",
        modes=[1],
        dest=tmp_path,
        depth=0,
        session=session,
        visited={"http://example.com/"},
    )
    session.get.assert_not_called()
