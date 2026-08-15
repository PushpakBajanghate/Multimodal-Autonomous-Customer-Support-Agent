"""
Public Agent Interface for Intent Classification and Entity Extraction.
"""

from typing import Optional, List, Dict, Any
from app.agent.schemas import (
    IntentType, IntentResult, ExtractedEntities, AnalysisResult
)
from app.agent.llm_client import execute_llm_intent_pipeline


def analyze_utterance(
    text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> AnalysisResult:
    """
    Main unified entrypoint for analyzing a user message.
    Extracts intent, confidence score, all relevant domain entities with confidence scores,
    and flags whether the query is ambiguous or missing required fields.
    """
    if not text or not text.strip():
        return AnalysisResult(
            intent=IntentType.UNKNOWN,
            confidence=1.0,
            entities=ExtractedEntities(),
            is_ambiguous=True,
            missing_entities=[],
            clarification_prompt="Hello! How can I assist you with your orders or account today?",
            reasoning="Empty or whitespace-only input."
        )

    return execute_llm_intent_pipeline(text.strip(), conversation_context)


def classify_intent(
    text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> IntentResult:
    """
    Classifies the user input into one of:
    - ORDER_TRACKING
    - REFUND_REQUEST
    - ORDER_CANCELLATION
    - ADDRESS_UPDATE
    - PASSWORD_RESET
    - TICKET_CREATION
    - UNKNOWN
    Returns IntentResult containing intent enum, confidence (0.0 - 1.0), and reasoning.
    """
    result = analyze_utterance(text, conversation_context)
    return IntentResult(
        intent=result.intent,
        confidence=result.confidence,
        raw_explanation=result.reasoning
    )


def extract_entities(
    text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> ExtractedEntities:
    """
    Extracts structured entities from the text (order_id, email, phone, product_info,
    refund_reason, new_address, relevant_dates) with per-entity confidence scores.
    """
    result = analyze_utterance(text, conversation_context)
    return result.entities
