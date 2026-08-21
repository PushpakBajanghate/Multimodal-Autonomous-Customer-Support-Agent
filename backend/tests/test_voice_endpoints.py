from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _customer_token() -> str:
    response = client.post("/api/v1/auth/customer-session", json={})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_voice_synthesis_falls_back_without_provider_key(monkeypatch):
    monkeypatch.setattr("app.services.voice_service.settings.SARVAM_API_KEY", None)
    token = _customer_token()

    response = client.post(
        "/api/v1/voice/synthesize",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "Mera order kahan hai?", "language_code": "auto", "provider": "sarvam"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["provider"] == "sarvam"
    assert payload["data"]["language_code"] == "hi-IN"
    assert payload["data"]["fallback_to_browser"] is True
    assert payload["data"]["audio_base64"] is None


def test_outbound_call_reports_missing_twilio_configuration(monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.voice.settings.TWILIO_ACCOUNT_SID", None)
    monkeypatch.setattr("app.api.v1.endpoints.voice.settings.TWILIO_AUTH_TOKEN", None)
    monkeypatch.setattr("app.api.v1.endpoints.voice.settings.TWILIO_FROM_NUMBER", None)
    monkeypatch.setattr("app.api.v1.endpoints.voice.settings.PUBLIC_BASE_URL", None)
    token = _customer_token()

    response = client.post(
        "/api/v1/voice/calls/outbound",
        headers={"Authorization": f"Bearer {token}"},
        json={"to_number": "+15551234567", "opening_message": "Hello from Aura"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["status"] == "not_configured"
    assert payload["data"]["configured"] is False


def test_twilio_answer_preserves_language_and_conversation_context():
    response = client.get(
        "/api/v1/voice/twilio/answer",
        params={
            "opening_message": "Namaste, main Aura customer support se bol rahi hoon.",
            "language_code": "hi-IN",
            "conversation_id": 42,
        },
    )

    assert response.status_code == 200
    body = response.text
    assert 'language="hi-IN"' in body
    assert "conversation_id=42" in body
    assert "language_code=hi-IN" in body
    assert "/api/v1/voice/twilio/gather" in body


def test_twilio_gather_switches_english_speech_to_english_language():
    response = client.post(
        "/api/v1/voice/twilio/gather?language_code=hi-IN&conversation_id=42",
        data={"SpeechResult": "hello"},
    )

    assert response.status_code == 200
    body = response.text.lower()
    assert 'language="en-in"' in body
    assert "conversation_id=42" in body
    assert "language_code=en-in" in body
    assert "aura" in body


def test_twilio_twiml_posts_empty_speech_to_gather():
    response = client.get(
        "/api/v1/voice/twilio/answer",
        params={"opening_message": "Hello from Aura", "language_code": "en-IN", "conversation_id": 7},
    )

    assert response.status_code == 200
    body = response.text
    assert 'actionOnEmptyResult="true"' in body
    assert 'timeout="8"' in body
    assert "/api/v1/voice/twilio/gather" in body


def test_twilio_gather_replies_quickly_without_provider_audio(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Provider TTS should not run inside live Twilio gather turns")

    monkeypatch.setattr("app.api.v1.endpoints.voice.synthesize_voice", fail_if_called)
    response = client.post(
        "/api/v1/voice/twilio/gather?language_code=hi-IN&conversation_id=42",
        data={"SpeechResult": "Hello"},
    )

    assert response.status_code == 200
    body = response.text
    assert "<Response>" in body
    assert "<Gather" in body
    assert "Hello" in body or "Aura" in body


def test_twilio_twiml_redirects_after_empty_speech():
    response = client.get(
        "/api/v1/voice/twilio/answer",
        params={"opening_message": "Hello from Aura", "language_code": "en-IN", "conversation_id": 7},
    )

    assert response.status_code == 200
    body = response.text
    assert "<Redirect" in body
    assert "/api/v1/voice/twilio/gather" in body
