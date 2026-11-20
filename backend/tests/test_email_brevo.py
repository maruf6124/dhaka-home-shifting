from app.services import email as email_service


def test_brevo_is_used_when_key_is_set(monkeypatch):
    calls = []

    class Resp:
        def raise_for_status(self):
            pass

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Resp()

    monkeypatch.setattr(email_service.settings, "brevo_api_key", "test-key")
    monkeypatch.setattr(email_service.settings, "email_from", "sender@example.com")
    monkeypatch.setattr(email_service.httpx, "post", fake_post)
    before = len(email_service.OUTBOX)

    email_service.send_email("user@example.com", "otp_signup", "bn", code="123456")

    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == email_service.BREVO_URL
    assert kwargs["headers"]["api-key"] == "test-key"
    payload = kwargs["json"]
    assert payload["sender"]["email"] == "sender@example.com"
    assert payload["to"] == [{"email": "user@example.com"}]
    assert "123456" in payload["subject"] and "123456" in payload["textContent"]
    assert len(email_service.OUTBOX) == before  # not console mode


def test_brevo_failure_does_not_raise(monkeypatch):
    def boom(url, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(email_service.settings, "brevo_api_key", "test-key")
    monkeypatch.setattr(email_service.settings, "email_from", "sender@example.com")
    monkeypatch.setattr(email_service.httpx, "post", boom)
    email_service.send_email("user@example.com", "otp_login", "en", code="654321")
