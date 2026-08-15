from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="Customer message text")
    conversation_id: Optional[int] = Field(default=None, description="Existing conversation session ID")
    channel: Optional[str] = Field(default="chat", description="Communication channel: chat or voice")

class ConversationMessageRead(BaseModel):
    id: int
    conversation_id: int
    sender: str  # "user" or "agent"
    message_text: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    conversation_id: int
    user_message_id: int
    agent_message_id: int
    reply: str
    created_at: datetime

class ConversationRead(BaseModel):
    id: int
    customer_id: Optional[int] = None
    channel: str
    status: str
    started_at: datetime
    messages: List[ConversationMessageRead] = []

    class Config:
        from_attributes = True
