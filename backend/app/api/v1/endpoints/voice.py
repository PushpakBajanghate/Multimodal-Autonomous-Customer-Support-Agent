import time
from collections import defaultdict, deque
from typing import Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor
from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.voice import (
    OutboundCallRequest,
    OutboundCallResponse,
    VoiceSynthesisRequest,
    VoiceSynthesisResponse,
)
from app.services.voice_service import build_twiml, detect_voice_language, synthesize_voice

router = APIRouter()
_AUDIO_CACHE: Dict[str, tuple[bytes, str]] = {}
_SESSION_REQUESTS: dict[str, deque[float]] = defaultdict(deque)


@router.post("/elevenlabs/session")
async def create_elevenlabs_session(request: Request, actor=Depends(get_current_actor)):
    """Mint a short-lived ElevenLabs session URL without exposing the API key."""
    # Bound anonymous customer-session token use as well as normal signed-in use.
    now = time.monotonic()
    if len(_SESSION_REQUESTS) > 1000:
        stale = [ip for ip, timestamps in _SESSION_REQUESTS.items() if not timestamps or now - timestamps[-1] >= 60]
        for ip in stale:
            _SESSION_REQUESTS.pop(ip, None)
    client_ip = request.client.host if request.client else "unknown"
    recent = _SESSION_REQUESTS[client_ip]
    while recent and now - recent[0] >= 60:
        recent.popleft()
    if len(recent) >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many voice session requests. Please wait a minute and try again.",
        )
    recent.append(now)

    if not settings.ELEVENLABS_API_KEY or not settings.ELEVENLABS_AGENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Browser voice support is not configured. Please use text support instead.",
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url",
                params={"agent_id": settings.ELEVENLABS_AGENT_ID},
                headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            )
            response.raise_for_status()
            data = response.json()
            signed_url = data.get("signed_url") if isinstance(data, dict) else None
            if not isinstance(signed_url, str) or not signed_url.startswith("wss://"):
                raise ValueError("ElevenLabs returned an invalid session URL")
    except (httpx.HTTPError, ValueError):
        # Do not relay upstream error bodies, which may contain sensitive metadata.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to the voice service. Please try text support or retry later.",
        )

    return JSONResponse({"signed_url": signed_url}, headers={"Cache-Control": "no-store"})


def _public_api_url(request: Optional[Request] = None) -> str:
    if settings.PUBLIC_BASE_URL:
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{settings.API_V1_STR}"
    if request is None:
        return settings.API_V1_STR
    return f"{str(request.base_url).rstrip('/')}{settings.API_V1_STR}"


def _with_query(url: str, **params: object) -> str:
    clean_params = {key: value for key, value in params.items() if value not in (None, "")}
    if not clean_params:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(clean_params)}"


@router.post("/synthesize", response_model=ApiResponse[VoiceSynthesisResponse])
def synthesize_speech(payload: VoiceSynthesisRequest, actor=Depends(get_current_actor)):
    audio = synthesize_voice(payload.text, payload.language_code, payload.provider)
    return ApiResponse[VoiceSynthesisResponse](
        success=True,
        status="success",
        reason=audio.reason,
        data=VoiceSynthesisResponse(
            provider=audio.provider,
            language_code=audio.language_code,
            audio_base64=audio.audio_base64,
            audio_mime_type=audio.audio_mime_type,
            fallback_to_browser=audio.fallback_to_browser,
            reason=audio.reason,
        ),
    )


@router.post("/calls/outbound", response_model=ApiResponse[OutboundCallResponse])
def start_outbound_call(payload: OutboundCallRequest, actor=Depends(get_current_actor)):
    missing = [
        name for name, value in {
            "TWILIO_ACCOUNT_SID": settings.TWILIO_ACCOUNT_SID,
            "TWILIO_AUTH_TOKEN": settings.TWILIO_AUTH_TOKEN,
            "TWILIO_FROM_NUMBER": settings.TWILIO_FROM_NUMBER,
            "PUBLIC_BASE_URL": settings.PUBLIC_BASE_URL,
        }.items() if not value
    ]
    if missing:
        return ApiResponse[OutboundCallResponse](
            success=False,
            status="not_configured",
            reason=f"Missing outbound call settings: {', '.join(missing)}",
            data=OutboundCallResponse(status="not_configured", configured=False, reason="Twilio calling is not configured."),
        )

    opening_message = payload.opening_message or "Hello, this is Aura Customer Support. How can I help you today?"
    callback_url = _with_query(
        f"{settings.PUBLIC_BASE_URL.rstrip('/')}{settings.API_V1_STR}/voice/twilio/answer",
        conversation_id=payload.conversation_id,
        language_code=payload.language_code or "auto",
        opening_message=opening_message,
    )
    calls_url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Calls.json"

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                calls_url,
                data={"To": payload.to_number, "From": settings.TWILIO_FROM_NUMBER, "Url": callback_url},
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            )
            response.raise_for_status()
        data = response.json()
        return ApiResponse[OutboundCallResponse](
            success=True,
            status="success",
            reason=None,
            data=OutboundCallResponse(call_sid=data.get("sid"), status=data.get("status", "queued"), configured=True),
        )
    except Exception as exc:
        return ApiResponse[OutboundCallResponse](
            success=False,
            status="failure",
            reason=f"Twilio call failed: {exc}",
            data=OutboundCallResponse(status="failure", configured=True, reason=str(exc)),
        )


@router.api_route("/twilio/answer", methods=["GET", "POST"], response_class=Response)
def twilio_answer(
    request: Request,
    opening_message: str = Query(default="Hello, this is Aura Customer Support. How can I help you today?"),
    language_code: str = Query(default="auto"),
    conversation_id: Optional[int] = Query(default=None),
):
    resolved_language = detect_voice_language(opening_message, language_code)
    action_url = _with_query(
        f"{_public_api_url(request)}/voice/twilio/gather",
        conversation_id=conversation_id,
        language_code=resolved_language,
    )
    return Response(content=build_twiml(opening_message, action_url, resolved_language), media_type="application/xml")


@router.post("/twilio/gather", response_class=Response)
def twilio_gather(
    request: Request,
    SpeechResult: str = Form(default=""),
    language_code: str = Query(default="auto"),
    conversation_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    from app.agent.responder import generate_agent_response

    transcript = SpeechResult.strip()
    if transcript:
        resolved_language = detect_voice_language(transcript, "auto")
    else:
        resolved_language = detect_voice_language("", language_code)
        transcript = "I could not hear you clearly. Please ask your question again."
    reply = generate_agent_response(
        db=db,
        message=transcript,
        conversation_id=conversation_id or 0,
        customer_id=None,
        conversation_history=[],
    )
    action_url = _with_query(
        f"{_public_api_url(request)}/voice/twilio/gather",
        conversation_id=conversation_id,
        language_code=resolved_language,
    )

    # Keep live call turns fast. Provider TTS can take long enough for Twilio
    # webhooks to time out, so phone calls use Twilio <Say> while the web voice
    # endpoint still uses Sarvam/ElevenLabs for generated audio.
    return Response(content=build_twiml(reply, action_url, resolved_language), media_type="application/xml")


@router.get("/audio/{audio_id}", response_class=Response)
def get_generated_audio(audio_id: str):
    audio = _AUDIO_CACHE.get(audio_id)
    if not audio:
        return Response(status_code=404)
    content, media_type = audio
    return Response(content=content, media_type=media_type)
