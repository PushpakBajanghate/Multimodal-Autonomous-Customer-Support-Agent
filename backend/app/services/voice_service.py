import base64
import html
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings


DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
HINGLISH_RE = re.compile(
    r"\b(mera|meri|mujhe|haan|nahi|kya|hai|order|cancel|karna|refund|paisa|kab|kahan|bhejo)\b",
    re.IGNORECASE,
)


@dataclass
class SynthesizedAudio:
    provider: str
    language_code: str
    audio_base64: Optional[str]
    audio_mime_type: str
    fallback_to_browser: bool = False
    reason: Optional[str] = None


def detect_voice_language(text: str, requested: Optional[str] = None) -> str:
    if requested and requested != "auto":
        return requested
    if DEVANAGARI_RE.search(text) or HINGLISH_RE.search(text):
        return "hi-IN"
    return "en-IN"


def _clean_voice_text(text: str) -> str:
    cleaned = re.sub(r"[\*_`#]+", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:2500]


def synthesize_voice(text: str, language_code: Optional[str] = None, provider: Optional[str] = None) -> SynthesizedAudio:
    selected_provider = (provider or settings.VOICE_PROVIDER or "sarvam").lower()
    resolved_language = detect_voice_language(text, language_code)
    clean_text = _clean_voice_text(text)

    if selected_provider == "sarvam":
        return _synthesize_sarvam(clean_text, resolved_language)
    if selected_provider == "elevenlabs":
        return _synthesize_elevenlabs(clean_text, resolved_language)

    return SynthesizedAudio(
        provider="browser",
        language_code=resolved_language,
        audio_base64=None,
        audio_mime_type="audio/wav",
        fallback_to_browser=True,
        reason="Browser speech synthesis selected.",
    )


def _synthesize_sarvam(text: str, language_code: str) -> SynthesizedAudio:
    if not settings.SARVAM_API_KEY:
        return SynthesizedAudio("sarvam", language_code, None, "audio/wav", True, "SARVAM_API_KEY is not configured.")

    speaker = settings.SARVAM_HINDI_SPEAKER if language_code.startswith("hi") else settings.SARVAM_ENGLISH_SPEAKER
    payload = {
        "inputs": [text],
        "target_language_code": language_code,
        "speaker": speaker,
        "pace": 1.0,
        "speech_sample_rate": settings.SARVAM_SAMPLE_RATE,
        "enable_preprocessing": True,
        "model": settings.SARVAM_TTS_MODEL,
    }
    headers = {
        "api-subscription-key": settings.SARVAM_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(settings.SARVAM_TTS_URL, json=payload, headers=headers)
            response.raise_for_status()
        data = response.json()
        audios = data.get("audios") or []
        if not audios:
            raise ValueError("Sarvam response did not include audio.")
        return SynthesizedAudio("sarvam", language_code, "".join(audios), "audio/wav")
    except Exception as exc:
        return SynthesizedAudio("sarvam", language_code, None, "audio/wav", True, f"Sarvam TTS failed: {exc}")


def _synthesize_elevenlabs(text: str, language_code: str) -> SynthesizedAudio:
    if not settings.ELEVENLABS_API_KEY:
        return SynthesizedAudio("elevenlabs", language_code, None, "audio/mpeg", True, "ELEVENLABS_API_KEY is not configured.")

    url = f"{settings.ELEVENLABS_TTS_URL.rstrip('/')}/{settings.ELEVENLABS_VOICE_ID}"
    payload = {
        "text": text,
        "model_id": settings.ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.42,
            "similarity_boost": 0.82,
            "style": 0.28,
            "use_speaker_boost": True,
        },
    }
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        audio = base64.b64encode(response.content).decode("ascii")
        return SynthesizedAudio("elevenlabs", language_code, audio, "audio/mpeg")
    except Exception as exc:
        return SynthesizedAudio("elevenlabs", language_code, None, "audio/mpeg", True, f"ElevenLabs TTS failed: {exc}")


def build_twiml(message: str, action_url: str, language_code: str = "en-IN", audio_url: Optional[str] = None) -> str:
    escaped_action = html.escape(action_url, quote=True)
    escaped_message = html.escape(message)
    speech_language = "hi-IN" if language_code.startswith("hi") else "en-IN"
    prompt = f'<Play>{html.escape(audio_url)}</Play>' if audio_url else f'<Say language="{speech_language}" voice="Polly.Aditi">{escaped_message}</Say>'
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        f'<Gather input="speech" speechTimeout="auto" language="{speech_language}" action="{escaped_action}" method="POST">'
        f"{prompt}"
        '</Gather>'
        f'<Say language="{speech_language}" voice="Polly.Aditi">I did not hear anything. Please call us again when you are ready.</Say>'
        '</Response>'
    )
