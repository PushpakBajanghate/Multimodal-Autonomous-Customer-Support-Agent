from typing import Optional
from pydantic import BaseModel, Field


class VoiceSynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2500)
    language_code: Optional[str] = Field(default=None, description="BCP-47 code such as hi-IN or en-IN")
    provider: Optional[str] = Field(default=None, description="sarvam, elevenlabs, or browser")


class VoiceSynthesisResponse(BaseModel):
    provider: str
    language_code: str
    audio_base64: Optional[str] = None
    audio_mime_type: str = "audio/wav"
    fallback_to_browser: bool = False
    reason: Optional[str] = None


class OutboundCallRequest(BaseModel):
    to_number: str = Field(..., min_length=7, max_length=32)
    opening_message: Optional[str] = Field(default=None, max_length=1200)
    conversation_id: Optional[int] = None
    language_code: Optional[str] = Field(default=None)


class OutboundCallResponse(BaseModel):
    provider: str = "twilio"
    call_sid: Optional[str] = None
    status: str
    configured: bool
    reason: Optional[str] = None


class VoiceTurnRequest(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[int] = None
    language_code: Optional[str] = None
