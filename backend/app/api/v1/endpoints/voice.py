import base64
from typing import Dict

import httpx
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import Response
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

    callback_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}{settings.API_V1_STR}/voice/twilio/answer"
    params = {
        "conversation_id": payload.conversation_id or "",
        "language_code": payload.language_code or "auto",
        "opening_message": payload.opening_message or "Hello, this is Aura Customer Support. How can I help you today?",
    }
    calls_url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Calls.json"

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                calls_url,
                data={"To": payload.to_number, "From": settings.TWILIO_FROM_NUMBER, "Url": callback_url},
                params=params,
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
def twilio_answer(request: Request, opening_message: str = "Hello, this is Aura Customer Support. How can I help you today?", language_code: str = "auto"):
    resolved_language = detect_voice_language(opening_message, language_code)
    action_url = f"{settings.PUBLIC_BASE_URL.rstrip('/') if settings.PUBLIC_BASE_URL else str(request.base_url).rstrip('/')}{settings.API_V1_STR}/voice/twilio/gather"
    return Response(content=build_twiml(opening_message, action_url, resolved_language), media_type="application/xml")


@router.post("/twilio/gather", response_class=Response)
def twilio_gather(
    request: Request,
    SpeechResult: str = Form(default=""),
    language_code: str = Form(default="auto"),
    db: Session = Depends(get_db),
):
    from app.agent.responder import generate_agent_response

    transcript = SpeechResult.strip() or "I need help with my order."
    resolved_language = detect_voice_language(transcript, language_code)
    reply = generate_agent_response(
        db=db,
        message=transcript,
        conversation_id=0,
        customer_id=None,
        conversation_history=[],
    )
    action_url = f"{settings.PUBLIC_BASE_URL.rstrip('/') if settings.PUBLIC_BASE_URL else str(request.base_url).rstrip('/')}{settings.API_V1_STR}/voice/twilio/gather"

    audio_url = None
    audio = synthesize_voice(reply, resolved_language)
    if audio.audio_base64 and settings.PUBLIC_BASE_URL:
        audio_id = str(abs(hash(audio.audio_base64)))
        _AUDIO_CACHE[audio_id] = (base64.b64decode(audio.audio_base64), audio.audio_mime_type)
        audio_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}{settings.API_V1_STR}/voice/audio/{audio_id}"

    return Response(content=build_twiml(reply, action_url, resolved_language, audio_url), media_type="application/xml")


@router.get("/audio/{audio_id}", response_class=Response)
def get_generated_audio(audio_id: str):
    audio = _AUDIO_CACHE.get(audio_id)
    if not audio:
        return Response(status_code=404)
    content, media_type = audio
    return Response(content=content, media_type=media_type)
