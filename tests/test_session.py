from pathlib import Path
from scraper_modules.session import is_partial, MIN_SIZE_VIDEO_AUDIO, MIN_SIZE_DOC_ARCHIVE
from scraper_modules.session import load_session, save_session


def test_is_partial_content_length_match(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"x" * 1000)
    assert not is_partial(f, content_length=1000)


def test_is_partial_content_length_mismatch(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"x" * 500)
    assert is_partial(f, content_length=1000)


def test_is_partial_no_content_length_large_enough(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"x" * MIN_SIZE_VIDEO_AUDIO)
    assert not is_partial(f, content_length=None, min_size=MIN_SIZE_VIDEO_AUDIO)


def test_is_partial_no_content_length_too_small(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"x" * 100)
    assert is_partial(f, content_length=None, min_size=MIN_SIZE_VIDEO_AUDIO)


def test_is_partial_file_not_exists(tmp_path):
    f = tmp_path / "nonexistent.mp4"
    assert not is_partial(f, content_length=None)


def test_is_partial_default_min_size(tmp_path):
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"x" * (MIN_SIZE_DOC_ARCHIVE - 1))
    assert is_partial(f, content_length=None)


def _make_session_data(url="https://example.com"):
    return {
        "url": url,
        "dest": "/tmp/example",
        "modes": [7, 8],
        "completed": False,
        "visited": ["https://example.com/"],
        "started_at": "2026-05-07T10:00:00",
        "completed_at": None,
    }


def test_load_session_no_dir(tmp_path):
    result = load_session("https://example.com", sessions_dir=tmp_path / "sessions")
    assert result is None


def test_save_and_load_session(tmp_path):
    sessions_dir = tmp_path / "sessions"
    data = _make_session_data()
    save_session(data, sessions_dir=sessions_dir)
    result = load_session("https://example.com", sessions_dir=sessions_dir)
    assert result is not None
    assert result["url"] == "https://example.com"
    assert result["visited"] == ["https://example.com/"]
    assert result["completed"] is False
    assert "_session_file" in result
    assert Path(result["_session_file"]).exists()


def test_load_session_corrupted_json(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "bad.json").write_text("not json", encoding="utf-8")
    result = load_session("https://example.com", sessions_dir=sessions_dir)
    assert result is None


def test_load_session_no_match(tmp_path):
    sessions_dir = tmp_path / "sessions"
    data = _make_session_data("https://other.com")
    save_session(data, sessions_dir=sessions_dir)
    result = load_session("https://example.com", sessions_dir=sessions_dir)
    assert result is None


def test_save_session_creates_dir(tmp_path):
    sessions_dir = tmp_path / "sessions"
    assert not sessions_dir.exists()
    save_session(_make_session_data(), sessions_dir=sessions_dir)
    assert sessions_dir.exists()
    assert len(list(sessions_dir.glob("*.json"))) == 1


def test_save_session_updates_existing(tmp_path):
    sessions_dir = tmp_path / "sessions"
    data = _make_session_data()
    save_session(data, sessions_dir=sessions_dir)
    data["visited"].append("https://example.com/page2")
    save_session(data, sessions_dir=sessions_dir)
    files = list(sessions_dir.glob("*.json"))
    assert len(files) == 1
    result = load_session("https://example.com", sessions_dir=sessions_dir)
    assert "https://example.com/page2" in result["visited"]
