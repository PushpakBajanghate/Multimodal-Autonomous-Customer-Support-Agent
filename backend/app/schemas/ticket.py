from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict

class TicketCreate(BaseModel):
    customer_id: int
    channel: str  # chat or voice
    intent: str
    actions_attempted: Dict[str, Any] = {}
    tool_results: Dict[str, Any] = {}
    escalation_reason: str

class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    channel: str
    intent: str
    actions_attempted: Dict[str, Any]
    tool_results: Dict[str, Any]
    escalation_reason: str
    status: str
    created_at: datetime
