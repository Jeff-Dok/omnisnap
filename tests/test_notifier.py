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
