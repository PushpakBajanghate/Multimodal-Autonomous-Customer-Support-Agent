"""
LLM Client for OpenAI and Google Gemini with configurable providers,
structured JSON schema extraction, dynamic conversational generation,
and intelligent contextual fallback.
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any
import httpx

from app.core.config import settings
from app.agent.schemas import AnalysisResult, IntentType, ExtractedEntities
from app.agent.prompts import INTENT_SYSTEM_PROMPT, FEW_SHOT_EXAMPLES
from app.agent.heuristics import analyze_utterance_rule_based

logger = logging.getLogger("aura.agent.llm")

# Reliable active Gemini models in order of priority
GEMINI_CANDIDATE_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash",
    "gemini-1.5-flash"
]


def _configured_api_key(value: Optional[str]) -> Optional[str]:
    """Return a real key, treating sample values in .env files as unset."""
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.upper().startswith(("PASTE_", "YOUR_", "CHANGE_")):
        return None
    return cleaned


def _clean_json_markdown(text: str) -> str:
    """Removes markdown code block delimiters from LLM output."""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    return text


def _parse_llm_json_response(raw_text: str) -> Optional[AnalysisResult]:
    """Parses LLM JSON string into validated AnalysisResult schema."""
    cleaned = _clean_json_markdown(raw_text)
    try:
        data = json.loads(cleaned)
        
        # Validate intent
        raw_intent = data.get("intent", "UNKNOWN")
        try:
            intent = IntentType(raw_intent)
        except ValueError:
            intent = IntentType.UNKNOWN

        confidence = float(data.get("confidence", 0.95))
        
        raw_entities = data.get("entities", {})
        conf_scores = raw_entities.get("confidence_scores")
        if not isinstance(conf_scores, dict):
            conf_scores = {}

        entity_fields = {
            "order_id": raw_entities.get("order_id"),
            "customer_id": raw_entities.get("customer_id"),
            "customer_name": raw_entities.get("customer_name"),
            "email": raw_entities.get("email"),
            "phone": raw_entities.get("phone"),
            "product_info": raw_entities.get("product_info"),
            "refund_reason": raw_entities.get("refund_reason"),
            "new_address": raw_entities.get("new_address"),
        }
        for field_name, val in entity_fields.items():
            if val is not None and field_name not in conf_scores:
                conf_scores[field_name] = 0.95

        entities = ExtractedEntities(
            order_id=raw_entities.get("order_id"),
            customer_id=raw_entities.get("customer_id"),
            customer_name=raw_entities.get("customer_name"),
            email=raw_entities.get("email"),
            phone=raw_entities.get("phone"),
            product_info=raw_entities.get("product_info"),
            refund_reason=raw_entities.get("refund_reason"),
            new_address=raw_entities.get("new_address"),
            relevant_dates=raw_entities.get("relevant_dates") or [],
            confidence_scores=conf_scores
        )

        is_ambiguous = bool(data.get("is_ambiguous", False))
        missing_entities = data.get("missing_entities", [])
        clarification_prompt = data.get("clarification_prompt")
        reasoning = data.get("reasoning")

        return AnalysisResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
            is_ambiguous=is_ambiguous,
            missing_entities=missing_entities,
            clarification_prompt=clarification_prompt,
            reasoning=reasoning
        )
    except Exception as e:
        logger.warning(f"Failed to parse LLM JSON response: {e}. Raw content: {raw_text}")
        return None


def call_openai_sync(
    prompt_text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> Optional[AnalysisResult]:
    """Synchronous OpenAI API call for intent analysis."""
    api_key = _configured_api_key(settings.OPENAI_API_KEY)
    if not api_key:
        return None

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": INTENT_SYSTEM_PROMPT}
    ]
    for example in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": example["input"]})
        messages.append({"role": "assistant", "content": json.dumps(example["output"])})

    if conversation_context:
        for ctx_msg in conversation_context:
            role = "assistant" if ctx_msg.get("sender") in ("agent", "assistant") else "user"
            messages.append({"role": role, "content": ctx_msg.get("text", "")})

    messages.append({"role": "user", "content": prompt_text})

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": messages,
        "temperature": settings.LLM_TEMPERATURE,
        "response_format": {"type": "json_object"}
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                body = resp.json()
                content = body["choices"][0]["message"]["content"]
                return _parse_llm_json_response(content)
            return None
    except Exception as exc:
        logger.error(f"OpenAI sync call error: {exc}")
        return None


def call_gemini_sync(
    prompt_text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> Optional[AnalysisResult]:
    """Synchronous Gemini REST API call with multi-model resilience."""
    api_key = _configured_api_key(settings.GEMINI_API_KEY)
    if not api_key:
        return None

    contents: List[Dict[str, Any]] = []
    for ex in FEW_SHOT_EXAMPLES:
        contents.append({"role": "user", "parts": [{"text": ex["input"]}]})
        contents.append({"role": "model", "parts": [{"text": json.dumps(ex["output"])}]})

    if conversation_context:
        for ctx_msg in conversation_context:
            role = "model" if ctx_msg.get("sender") in ("agent", "assistant") else "user"
            contents.append({"role": role, "parts": [{"text": ctx_msg.get("text", "")}]})

    contents.append({"role": "user", "parts": [{"text": prompt_text}]})

    payload = {
        "system_instruction": {"parts": [{"text": INTENT_SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "temperature": settings.LLM_TEMPERATURE,
            "response_mime_type": "application/json"
        }
    }

    models_to_try = [settings.GEMINI_MODEL] if settings.GEMINI_MODEL in GEMINI_CANDIDATE_MODELS else []
    for m in GEMINI_CANDIDATE_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    body = resp.json()
                    candidates = body.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        if content_parts:
                            raw_json = content_parts[0].get("text", "")
                            parsed = _parse_llm_json_response(raw_json)
                            if parsed:
                                return parsed
                elif resp.status_code in (404, 400):
                    # Try next candidate model
                    continue
        except Exception as exc:
            logger.debug(f"Gemini sync call error on {model}: {exc}")
            continue

    return None


def execute_llm_intent_pipeline(
    text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> AnalysisResult:
    """
    Executes the configured LLM pipeline (Gemini or OpenAI).
    Falls back reliably to deterministic heuristic engine if no API key is present or on failure.
    """
    provider = (settings.LLM_PROVIDER or "").lower().strip()
    result: Optional[AnalysisResult] = None

    gemini_key = _configured_api_key(settings.GEMINI_API_KEY)
    openai_key = _configured_api_key(settings.OPENAI_API_KEY)

    if provider == "gemini" and gemini_key:
        result = call_gemini_sync(text, conversation_context)
    elif provider == "openai" and openai_key:
        result = call_openai_sync(text, conversation_context)
    elif gemini_key:
        result = call_gemini_sync(text, conversation_context)
    elif openai_key:
        result = call_openai_sync(text, conversation_context)

    # If LLM execution succeeded, return result
    if result is not None:
        return result

    # Otherwise fallback to high-accuracy rule-based heuristics
    return analyze_utterance_rule_based(text, conversation_context)


def generate_conversational_llm_response(
    intent: str,
    user_message: str,
    tool_results: Optional[Dict[str, Any]] = None,
    conversation_context: Optional[List[Dict[str, Any]]] = None,
    customer_name: Optional[str] = None,
    customer_orders: Optional[List[Dict[str, Any]]] = None,
    missing_entities: Optional[List[str]] = None,
    clarification_prompt: Optional[str] = None
) -> Optional[str]:
    """
    Synthesizes a fluent, empathetic, and intelligent conversational reply using active LLM (Gemini or OpenAI).
    Adheres strictly to verified domain facts and policies.
    """
    provider = (settings.LLM_PROVIDER or "").lower().strip()
    gemini_key = _configured_api_key(settings.GEMINI_API_KEY)
    openai_key = _configured_api_key(settings.OPENAI_API_KEY)
    api_key = gemini_key if provider == "gemini" else openai_key
    if not api_key:
        api_key = gemini_key or openai_key
        if gemini_key:
            provider = "gemini"
        elif openai_key:
            provider = "openai"

    if not api_key:
        return None

    system_prompt = (
        "You are Aura, an autonomous, highly empathetic, articulate, and intelligent AI customer support assistant.\n"
        "Guidelines:\n"
        "1. Address the customer by name if known (e.g. 'Hello Alice!').\n"
        "2. If domain/tool results or active orders are provided, ALWAYS explicitly state the exact Order ID (e.g. 'Order #1'), status, tracking info, carrier, or refund/cancellation confirmation from verified_tool_results.\n"
        "3. If missing_information contains 'order_id' or an action needs an order number, explicitly ask the customer to provide their Order ID or specify which order they want help with.\n"
        "4. Keep your answer direct, empathetic, and helpful without unnecessary filler."
    )

    context_payload = {
        "customer_name": customer_name,
        "intent": intent,
        "verified_tool_results": tool_results or {},
        "customer_active_orders": customer_orders or [],
        "missing_information": missing_entities or [],
        "suggested_clarification": clarification_prompt,
        "recent_conversation": (conversation_context or [])[-8:]
    }

    user_prompt = (
        f"Context & Verified Domain Data: {json.dumps(context_payload, default=str)}\n"
        f"Customer Message: \"{user_message}\"\n\n"
        "Generate your direct, empathetic conversational response to the customer:"
    )

    # 1. Try Gemini
    if provider == "gemini" and gemini_key:
        models_to_try = [settings.GEMINI_MODEL] if settings.GEMINI_MODEL in GEMINI_CANDIDATE_MODELS else []
        for m in GEMINI_CANDIDATE_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
            payload = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 350
                }
            }
            try:
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        body = resp.json()
                        candidates = body.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
            except Exception as exc:
                logger.debug(f"Gemini conversational generation error on {model}: {exc}")
                continue

    # 2. Try OpenAI
    if provider == "openai" and openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 350
            }
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    body = resp.json()
                    return body["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.debug(f"OpenAI conversational generation error: {exc}")

    return None


def generate_natural_llm_response(
    intent: str,
    tool_results: Dict[str, Any],
    user_message: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> Optional[str]:
    """Compatibility wrapper for generate_conversational_llm_response."""
    return generate_conversational_llm_response(
        intent=intent,
        user_message=user_message,
        tool_results=tool_results,
        conversation_context=conversation_context
    )


def generate_intelligent_offline_response(
    intent: IntentType,
    user_message: str,
    tool_results: Optional[Dict[str, Any]] = None,
    customer_name: Optional[str] = None,
    customer_orders: Optional[List[Dict[str, Any]]] = None,
    missing_entities: Optional[List[str]] = None,
    clarification_prompt: Optional[str] = None
) -> str:
    """
    Intelligent contextual response generator when LLM API keys are offline/unavailable.
    Dynamically crafts personalized, contextual replies recognizing user identity and intent,
    without outputting static canned menus.
    """
    greeting = f"Hello {customer_name}! " if customer_name else "Hello! "
    msg_lower = user_message.lower().strip()

    # Ask the focused clarification produced by the intent engine rather than
    # falling through to a generic welcome response.
    if clarification_prompt:
        return clarification_prompt

    # 1. Order Tracking
    if intent == IntentType.ORDER_TRACKING:
        if tool_results and tool_results.get("status") == "success":
            t = tool_results.get("tracking") or tool_results
            order_id = t.get("order_id", "N/A")
            status_str = str(t.get("status", "in_transit")).upper()
            carrier = t.get("carrier", "Carrier Express")
            trk_num = t.get("tracking_number", "N/A")
            exp_date = t.get("expected_delivery_str", "Estimated Soon")
            days_left = t.get("estimated_days_remaining", 0)
            eta_detail = f"Estimated {days_left} day(s) remaining." if days_left > 0 else "Delivery is progressing on schedule."
            if t.get("is_delivered"):
                eta_detail = "This package has been successfully delivered."

            return (
                f"{greeting}Here is the latest tracking update for Order #{order_id}:\n\n"
                f"• Status: {status_str}\n"
                f"• Carrier: {carrier} (Tracking: {trk_num})\n"
                f"• Expected Delivery: {exp_date}\n"
                f"• Note: {eta_detail}\n\n"
                f"Please let me know if you need anything else!"
            )
        elif customer_orders and len(customer_orders) > 0:
            # If customer has active orders, show them
            recent_order = customer_orders[0]
            oid = recent_order.get("id")
            st = str(recent_order.get("status", "")).upper()
            exp = recent_order.get("expected_delivery_str", "Upcoming")
            return (
                f"{greeting}I looked up your account and found your active Order #{oid} (Status: {st}, Expected Delivery: {exp}).\n\n"
                f"Would you like full tracking details for Order #{oid}, or are you inquiring about a different order number?"
            )
        else:
            return (
                f"{greeting}I'd be glad to check your delivery timeline and order status. "
                f"Could you please provide your Order ID (for example, Order #1) so I can look up the exact delivery schedule for you?"
            )

    # 2. Refund Request
    elif intent == IntentType.REFUND_REQUEST:
        if tool_results and tool_results.get("success"):
            r = tool_results.get("refund") or tool_results
            order_id = r.get("order_id", "N/A")
            amt = float(r.get("amount", 0.0))
            return (
                f"{greeting}Your refund request for Order #{order_id} has been approved for ${amt:.2f}.\n\n"
                f"• Refund Status: Processed\n"
                f"• Expected Timeline: 3 to 5 business days back to your original payment method."
            )
        elif tool_results and not tool_results.get("success"):
            err = tool_results.get("error", "The order is not eligible for refund.")
            return f"{greeting}I checked your request, but {err}"
        else:
            return (
                f"{greeting}Our return policy allows full refunds within 30 days of delivery for delivered or cancelled items. "
                f"Please provide your Order ID and the reason for the refund so I can process this for you right away."
            )

    # 3. Order Cancellation
    elif intent == IntentType.ORDER_CANCELLATION:
        if tool_results and tool_results.get("success"):
            order_id = tool_results.get("order_id", "N/A")
            return (
                f"{greeting}Order #{order_id} has been successfully cancelled. "
                f"Any pending charges have been released and no further action is required."
            )
        elif tool_results and not tool_results.get("success"):
            err = tool_results.get("error", "The order cannot be cancelled at this stage.")
            return f"{greeting}{err}"
        else:
            return (
                f"{greeting}Orders can be cancelled while in 'placed' status prior to shipping. "
                f"Please tell me which Order ID you would like to cancel."
            )

    # 4. Address Update
    elif intent == IntentType.ADDRESS_UPDATE:
        if tool_results and tool_results.get("success"):
            order_id = tool_results.get("order_id")
            new_addr = tool_results.get("new_address", "")
            target = f"for Order #{order_id}" if order_id else "on your account"
            return f"{greeting}The destination shipping address {target} has been updated to:\n• {new_addr}"
        elif tool_results and not tool_results.get("success"):
            err = tool_results.get("error", "Unable to update shipping address.")
            return f"{greeting}{err}"
        else:
            return (
                f"{greeting}I can help update your shipping destination address. "
                f"Please provide your Order ID along with the complete new delivery address."
            )

    # 5. Password Reset
    elif intent == IntentType.PASSWORD_RESET:
        if tool_results and tool_results.get("success"):
            email = tool_results.get("email", "your account email")
            return (
                f"{greeting}A secure password reset link has been dispatched to {email}. "
                f"Please check your inbox (and spam folder) within the next 15 minutes."
            )
        else:
            return (
                f"{greeting}Please provide the email address associated with your account so I can send you a password reset link."
            )

    # 6. Ticket Creation
    elif intent == IntentType.TICKET_CREATION:
        if tool_results and tool_results.get("success"):
            tid = tool_results.get("ticket_id", "N/A")
            return (
                f"{greeting}I have created priority support ticket #{tid} for you. "
                f"A member of our human support team will review your inquiry and follow up shortly."
            )
        else:
            return (
                f"{greeting}I can open a support ticket for our human customer care team. "
                f"Please share the details of the issue you are experiencing."
            )

    # 7. Outbound Call Request
    elif intent == IntentType.OUTBOUND_CALL_REQUEST:
        if tool_results and tool_results.get("success") and tool_results.get("phone_number"):
            p = tool_results.get("phone_number")
            return (
                f"{greeting}I am initiating an outbound AI voice call to your number ({p}) right now! "
                f"Please answer your phone when it rings to speak with our AI agent."
            )
        elif tool_results and tool_results.get("status") in {"not_configured", "call_failed"}:
            reason = tool_results.get("error") or "Outbound calling is not configured."
            return (
                f"{greeting}I could not place the outbound phone call yet. "
                f"{reason}. Please configure Twilio credentials and a public HTTPS callback URL, then try again."
            )
        else:
            return (
                f"{greeting}I would be happy to give you a call! "
                f"Please provide your 10-digit phone number with country code (e.g. +91...) so I can place the call."
            )

    # 8. General / Introductions / Inquiries
    else:
        if customer_name and any(word in msg_lower for word in ["hello", "hi", "hey", "namaste"]):
            return (
                f"Hello {customer_name}! It's a pleasure to assist you. "
                f"I am Aura, your autonomous customer support assistant. How can I help you today with your orders, tracking, or account?"
            )
        elif any(w in msg_lower for w in ["hi", "hello", "hey", "good morning", "good evening"]):
            return (
                f"Hello! I am Aura, your customer support assistant. "
                f"How can I help you today with your orders, returns, tracking, or account?"
            )
        elif any(w in msg_lower for w in ["who are you", "what can you do", "help"]):
            return (
                f"I am Aura, an autonomous customer support AI. I can assist you with:\n"
                f"• Real-time order tracking and delivery ETAs\n"
                f"• Return and refund requests\n"
                f"• Order cancellations\n"
                f"• Shipping address updates\n"
                f"• Account recovery and human agent escalation\n\n"
                f"How may I assist you today?"
            )
        else:
            return (
                f"Thank you for contacting customer support. I am here to assist you with order inquiries, shipments, refunds, and account updates. "
                f"Could you please share your Order ID or describe what you need help with?"
            )

