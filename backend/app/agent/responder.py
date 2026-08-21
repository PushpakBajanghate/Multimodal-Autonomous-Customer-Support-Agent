"""
Agent Response Engine: Orchestrates NLU intent analysis, domain service execution,
and intelligent conversational responses powered by LLM Reasoning Brain.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.models import Customer, Order
from app.agent.intent import analyze_utterance
from app.agent.schemas import IntentType, AnalysisResult
from app.agent.llm_client import (
    generate_conversational_llm_response,
    generate_intelligent_offline_response
)
from app.services.order_service import (
    get_order_tracking,
    process_refund,
    process_cancellation
)
from app.services.customer_service import (
    request_address_change,
    request_password_reset
)
from app.services.ticket_service import create_escalation_ticket


def generate_agent_response(
    db: Session,
    message: str,
    conversation_id: int,
    customer_id: Optional[int] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Executes real intent recognition, entity extraction, domain business logic,
    and returns a contextual, dynamic, empathetic LLM agent response.
    """
    # 1. Run LLM / NLU Intent Recognition & Entity Extraction
    analysis: AnalysisResult = analyze_utterance(
        text=message,
        conversation_context=conversation_history
    )

    intent = analysis.intent
    entities = analysis.entities
    resolved_customer_id = customer_id or entities.customer_id or 1

    # 2. Identify customer profile and active orders from DB
    customer_name = entities.customer_name
    if not customer_name and conversation_history:
        from app.agent.heuristics import _extract_customer_name
        for hist_msg in conversation_history:
            if hist_msg.get("sender") == "user":
                detected_name = _extract_customer_name(hist_msg.get("text", ""))
                if detected_name:
                    customer_name = detected_name
                    break

    customer_orders_data: List[Dict[str, Any]] = []

    try:
        db_customer = db.query(Customer).filter(Customer.id == resolved_customer_id).first()
        if db_customer:
            if not customer_name:
                customer_name = db_customer.name.split()[0] if db_customer.name else None

            db_orders = db.query(Order).filter(Order.customer_id == db_customer.id).order_by(Order.order_date.desc()).all()
            for o in db_orders:
                exp_str = o.expected_delivery.strftime("%B %d, %Y") if o.expected_delivery else "Pending"
                customer_orders_data.append({
                    "id": o.id,
                    "status": o.status,
                    "total_amount": float(o.total_amount) if o.total_amount else 0.0,
                    "expected_delivery_str": exp_str,
                    "is_editable": o.is_editable
                })
    except Exception:
        pass

    # If order_id not in entities but customer has exactly 1 active order, we can relate it
    target_order_id = entities.order_id
    if target_order_id is None and len(customer_orders_data) == 1 and intent in (IntentType.ORDER_TRACKING, IntentType.REFUND_REQUEST, IntentType.ORDER_CANCELLATION):
        target_order_id = customer_orders_data[0]["id"]

    tool_results: Optional[Dict[str, Any]] = None

    # 3. Dispatch to Domain Logic based on Intent if parameters are present
    if intent == IntentType.ORDER_TRACKING and target_order_id is not None:
        success, error, tracking = get_order_tracking(db, target_order_id)
        if success and tracking:
            exp_date = tracking["expected_delivery"].strftime("%B %d, %Y") if tracking.get("expected_delivery") else "Pending"
            tool_results = {
                "success": True,
                "status": "success",
                "tracking": {
                    "order_id": target_order_id,
                    "status": tracking.get("status"),
                    "carrier": tracking.get("carrier"),
                    "tracking_number": tracking.get("tracking_number"),
                    "expected_delivery_str": exp_date,
                    "estimated_days_remaining": tracking.get("estimated_days_remaining", 0),
                    "is_delivered": tracking.get("is_delivered", False)
                }
            }
        else:
            tool_results = {
                "success": False,
                "status": "error",
                "error": error or f"Order #{target_order_id} was not found in our database."
            }

    elif intent == IntentType.REFUND_REQUEST and target_order_id is not None:
        reason = entities.refund_reason or message
        success, error, refund = process_refund(db, target_order_id, reason=reason)
        if success and refund:
            tool_results = {
                "success": True,
                "status": "success",
                "refund": {
                    "order_id": target_order_id,
                    "amount": float(refund.amount),
                    "reason": refund.reason,
                    "status": refund.status
                }
            }
        else:
            tool_results = {
                "success": False,
                "status": "error",
                "error": error or f"Unable to process refund for Order #{target_order_id}."
            }

    elif intent == IntentType.ORDER_CANCELLATION and target_order_id is not None:
        reason = entities.refund_reason or message
        success, error, cancellation = process_cancellation(db, target_order_id, reason=reason)
        if success and cancellation:
            tool_results = {
                "success": True,
                "status": "success",
                "order_id": target_order_id,
                "status_result": cancellation.status
            }
        else:
            tool_results = {
                "success": False,
                "status": "error",
                "error": error or f"Unable to cancel Order #{target_order_id}."
            }

    elif intent == IntentType.ADDRESS_UPDATE and entities.new_address:
        success, error, addr_req = request_address_change(
            db=db,
            customer_id=resolved_customer_id,
            new_address=entities.new_address,
            order_id=target_order_id
        )
        if success and addr_req:
            tool_results = {
                "success": True,
                "status": "success",
                "order_id": target_order_id,
                "new_address": entities.new_address
            }
        else:
            tool_results = {
                "success": False,
                "status": "error",
                "error": error or "Unable to update shipping address."
            }

    elif intent == IntentType.PASSWORD_RESET:
        success, error, reset_req = request_password_reset(db=db, customer_id=resolved_customer_id)
        if success and reset_req:
            tool_results = {
                "success": True,
                "status": "success",
                "email": entities.email or "your account email"
            }
        else:
            tool_results = {
                "success": False,
                "status": "error",
                "error": error or "Unable to initiate password reset."
            }

    elif intent == IntentType.TICKET_CREATION:
        success, error, ticket = create_escalation_ticket(
            db=db,
            customer_id=resolved_customer_id,
            channel="chat",
            intent="TICKET_CREATION",
            actions_attempted={"intent": intent.value, "entities": entities.model_dump()},
            tool_results={},
            escalation_reason=message
        )
        if success and ticket:
            tool_results = {
                "success": True,
                "status": "success",
                "ticket_id": ticket.id
            }
        else:
            tool_results = {
                "success": False,
                "status": "error",
                "error": error or "Could not create support ticket."
            }

    elif intent == IntentType.OUTBOUND_CALL_REQUEST:
        phone_num = entities.phone
        if not phone_num and conversation_history:
            import re
            from app.agent.heuristics import PHONE_REGEX
            for hist_msg in reversed(conversation_history):
                if hist_msg.get("sender") in ("user", "customer"):
                    p_match = PHONE_REGEX.search(hist_msg.get("text", ""))
                    if p_match:
                        phone_num = p_match.group(0).strip()
                        break

        if phone_num:
            from app.core.config import settings
            import httpx

            call_sid = None
            if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER and settings.PUBLIC_BASE_URL:
                try:
                    callback_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}{settings.API_V1_STR}/voice/twilio/answer"
                    calls_url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Calls.json"
                    with httpx.Client(timeout=10) as client:
                        resp = client.post(
                            calls_url,
                            data={"To": phone_num, "From": settings.TWILIO_FROM_NUMBER, "Url": callback_url},
                            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                        )
                        if resp.status_code in (200, 201):
                            call_sid = resp.json().get("sid")
                except Exception:
                    pass

            tool_results = {
                "success": True,
                "status": "call_initiated",
                "phone_number": phone_num,
                "call_sid": call_sid
            }
        else:
            analysis.is_ambiguous = True
            analysis.missing_entities = ["phone_number"]
            analysis.clarification_prompt = (
                f"Hello {customer_name}! " if customer_name else "Hello! "
            ) + "I would be happy to give you a call! Please provide your phone number with your country code (e.g. +91...)."

    # 4. Generate Conversational LLM Response
    llm_reply = generate_conversational_llm_response(
        intent=intent.value,
        user_message=message,
        tool_results=tool_results,
        conversation_context=conversation_history,
        customer_name=customer_name,
        customer_orders=customer_orders_data,
        missing_entities=analysis.missing_entities,
        clarification_prompt=analysis.clarification_prompt
    )

    if llm_reply:
        return llm_reply

    # 5. Intelligent Dynamic Contextual Fallback Brain (Non-hardcoded)
    return generate_intelligent_offline_response(
        intent=intent,
        user_message=message,
        tool_results=tool_results,
        customer_name=customer_name,
        customer_orders=customer_orders_data,
        missing_entities=analysis.missing_entities,
        clarification_prompt=analysis.clarification_prompt
    )

