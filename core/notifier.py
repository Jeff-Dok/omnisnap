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
