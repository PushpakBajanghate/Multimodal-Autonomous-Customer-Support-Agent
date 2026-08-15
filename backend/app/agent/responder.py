"""
Agent Response Engine: Orchestrates NLU intent analysis, domain service execution,
and intelligent conversational responses.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.agent.intent import analyze_utterance
from app.agent.schemas import IntentType, AnalysisResult
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
    and returns a contextual, dynamic agent response.
    """
    # 1. Run LLM / NLU Intent Recognition & Entity Extraction
    analysis: AnalysisResult = analyze_utterance(
        text=message,
        conversation_context=conversation_history
    )

    intent = analysis.intent
    entities = analysis.entities
    resolved_customer_id = customer_id or 1

    # 2. Check for Ambiguity / Incomplete Parameters
    if analysis.is_ambiguous and analysis.clarification_prompt:
        return analysis.clarification_prompt

    # 3. Dispatch to Domain Logic based on Intent
    if intent == IntentType.ORDER_TRACKING:
        order_id = entities.order_id
        if order_id is None:
            return "Could you please specify your Order ID so I can look up the tracking information?"

        success, error, tracking = get_order_tracking(db, order_id)
        if not success or not tracking:
            return f"I looked up Order #{order_id}, but {error or 'it was not found in our system'}. Please double check the order number."

        status_str = tracking["status"].upper()
        carrier = tracking.get("carrier", "Carrier Express")
        trk_num = tracking.get("tracking_number", "N/A")
        exp_date = tracking["expected_delivery"].strftime("%B %d, %Y") if tracking.get("expected_delivery") else "Pending"
        
        days_left = tracking.get("estimated_days_remaining", 0)
        eta_note = f"Estimated {days_left} day(s) remaining." if days_left > 0 else "Delivery is on schedule."
        if tracking.get("is_delivered"):
            eta_note = "Package has been successfully delivered."

        return (
            f"Here is the tracking status for Order #{order_id}:\n"
            f"• Status: {status_str}\n"
            f"• Carrier: {carrier} (Tracking: {trk_num})\n"
            f"• Expected Delivery: {exp_date}\n"
            f"• Details: {eta_note}"
        )

    elif intent == IntentType.REFUND_REQUEST:
        order_id = entities.order_id
        if order_id is None:
            return "Please provide your Order ID and the reason for refund so I can process it for you."

        reason = entities.refund_reason or message
        success, error, refund = process_refund(db, order_id, reason=reason)
        if not success or not refund:
            return f"Unable to process refund for Order #{order_id}:\n{error}"

        return (
            f"Your refund request for Order #{order_id} has been APPROVED for ${refund.amount:.2f}.\n"
            f"• Refund Status: {refund.status.capitalize()}\n"
            f"• Reason Recorded: {refund.reason}\n"
            f"The funds will be credited back to your original payment method within 3 to 5 business days."
        )

    elif intent == IntentType.ORDER_CANCELLATION:
        order_id = entities.order_id
        if order_id is None:
            return "Please tell me which Order ID you would like to cancel."

        reason = entities.refund_reason or message
        success, error, cancellation = process_cancellation(db, order_id, reason=reason)
        if not success or not cancellation:
            return f"Unable to cancel Order #{order_id}:\n{error}"

        return (
            f"Order #{order_id} has been successfully CANCELLED.\n"
            f"• Status: {cancellation.status.capitalize()}\n"
            f"• Confirmation: Any pending charges for this order have been voided/refunded."
        )

    elif intent == IntentType.ADDRESS_UPDATE:
        order_id = entities.order_id
        new_addr = entities.new_address

        if not new_addr:
            return "Please provide the complete new delivery address you would like to set."

        success, error, addr_req = request_address_change(
            db=db,
            customer_id=resolved_customer_id,
            new_address=new_addr,
            order_id=order_id
        )
        if not success or not addr_req:
            return f"Unable to update shipping address:\n{error}"

        target = f"for Order #{order_id}" if order_id else "on your account"
        return (
            f"The shipping destination address {target} has been updated successfully.\n"
            f"• New Address: {new_addr}\n"
            f"• Request Status: {addr_req.status.capitalize()}"
        )

    elif intent == IntentType.PASSWORD_RESET:
        email = entities.email
        success, error, reset_req = request_password_reset(db=db, customer_id=resolved_customer_id)
        if not success or not reset_req:
            return f"Unable to initiate password reset:\n{error}"

        target_email = email or "your registered account email"
        return (
            f"A secure password reset link has been dispatched to {target_email}.\n"
            f"Please check your inbox (and spam folder) within the next 15 minutes to reset your password."
        )

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
        if not success or not ticket:
            return f"Could not create support ticket: {error}"

        return (
            f"I have opened a priority support ticket #{ticket.id} for you.\n"
            f"• Topic: Customer Support Escalation\n"
            f"• Status: Open\n"
            f"A human support representative has been assigned and will follow up with you shortly."
        )

    else:
        # UNKNOWN or General Conversation
        return (
            f"Hello! I am Aura, your autonomous customer support assistant.\n"
            f"I can help you with:\n"
            f"• Tracking order delivery status\n"
            f"• Processing refunds and returns\n"
            f"• Cancelling active orders\n"
            f"• Updating shipping addresses\n"
            f"• Password reset and human support tickets\n\n"
            f"How may I help you today?"
        )
