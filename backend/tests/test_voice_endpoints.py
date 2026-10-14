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


def test_elevenlabs_session_requires_customer_authentication():
    response = client.post("/api/v1/voice/elevenlabs/session")

    assert response.status_code == 401


def test_elevenlabs_session_reports_missing_configuration(monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.voice.settings.ELEVENLABS_API_KEY", None)
    monkeypatch.setattr("app.api.v1.endpoints.voice.settings.ELEVENLABS_AGENT_ID", None)
    token = _customer_token()

    response = client.post(
        "/api/v1/voice/elevenlabs/session",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert "not configured" in response.json()["reason"].lower()


def test_elevenlabs_session_returns_only_signed_url(monkeypatch):
    api_key = "server-only-test-key"
    signed_url = "wss://api.elevenlabs.io/v1/convai/conversation?signature=short-lived"
    monkeypatch.setattr("app.api.v1.endpoints.voice.settings.ELEVENLABS_API_KEY", api_key)
    monkeypatch.setattr("app.api.v1.endpoints.voice.settings.ELEVENLABS_AGENT_ID", "agent_test123")

    class MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"signed_url": signed_url}

    class MockAsyncClient:
        def __init__(self, timeout):
            assert timeout == 10

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params, headers):
            assert url.endswith("/get-signed-url")
            assert params == {"agent_id": "agent_test123"}
            assert headers == {"xi-api-key": api_key}
            return MockResponse()

    monkeypatch.setattr("app.api.v1.endpoints.voice.httpx.AsyncClient", MockAsyncClient)
    token = _customer_token()

    response = client.post(
        "/api/v1/voice/elevenlabs/session",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"signed_url": signed_url}
    assert api_key not in response.text


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
