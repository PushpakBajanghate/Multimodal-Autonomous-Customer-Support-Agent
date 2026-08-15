from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class IntentType(str, Enum):
    ORDER_TRACKING = "ORDER_TRACKING"
    REFUND_REQUEST = "REFUND_REQUEST"
    ORDER_CANCELLATION = "ORDER_CANCELLATION"
    ADDRESS_UPDATE = "ADDRESS_UPDATE"
    PASSWORD_RESET = "PASSWORD_RESET"
    TICKET_CREATION = "TICKET_CREATION"
    UNKNOWN = "UNKNOWN"


class ExtractedEntities(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_id: Optional[int] = Field(default=None, description="Extracted numeric order ID")
    customer_id: Optional[int] = Field(default=None, description="Extracted customer ID")
    email: Optional[str] = Field(default=None, description="Extracted customer email address")
    phone: Optional[str] = Field(default=None, description="Extracted customer phone number")
    product_info: Optional[str] = Field(default=None, description="Product names, descriptions, or SKUs")
    refund_reason: Optional[str] = Field(default=None, description="Reason stated for refund or return")
    new_address: Optional[str] = Field(default=None, description="New target delivery or shipping address")
    relevant_dates: Optional[List[str]] = Field(default_factory=list, description="Dates mentioned (order date, delivery date)")
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Confidence score per extracted entity (0.0 to 1.0)")


class IntentResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intent: IntentType = Field(description="Classified intent type")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score for the intent (0.0 to 1.0)")
    raw_explanation: Optional[str] = Field(default=None, description="Brief explanation or reasoning for the classification")


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intent: IntentType = Field(description="Classified customer intent")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score for the intent")
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities, description="Extracted domain entities with confidence scores")
    is_ambiguous: bool = Field(default=False, description="Flag indicating if the user request is ambiguous or missing critical information")
    missing_entities: List[str] = Field(default_factory=list, description="List of required entity names missing to fulfill the intent")
    clarification_prompt: Optional[str] = Field(default=None, description="Suggested follow-up question to clarify the ambiguous request")
    reasoning: Optional[str] = Field(default=None, description="Reasoning behind classification and ambiguity determination")
