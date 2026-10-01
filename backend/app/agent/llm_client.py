"""
Real Chatbot Conversational LLM Engine for Customer Support.
Prioritizes active, low-latency Google Gemini models with intelligent fallback,
contextual understanding, and natural human-like dialogue generation.
"""

import json
import logging
import re
import time
from typing import Optional, List, Dict, Any
import httpx

from app.core.config import settings
from app.agent.schemas import AnalysisResult, IntentType, ExtractedEntities
from app.agent.prompts import INTENT_SYSTEM_PROMPT, FEW_SHOT_EXAMPLES
from app.agent.heuristics import analyze_utterance_rule_based
from app.services.voice_service import detect_voice_language

logger = logging.getLogger("aura.agent.llm")

# Active Gemini models in tested priority order
ACTIVE_GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-3.8-flash",
    "gemma-4-26b-a4b-it"
]

_GEMINI_KEY_VALID: Optional[bool] = None
_OPENAI_KEY_VALID: Optional[bool] = None
_MODEL_COOLDOWNS: Dict[str, float] = {}


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
                conf_scores[field_name] = max(confidence, 0.85)

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
        logger.warning(f"Failed to parse LLM JSON response: {e}. Raw content: {raw_text[:200]}")
        return None


def _is_model_cooling_down(model_name: str) -> bool:
    """Checks if a model is temporarily in cooldown due to recent rate limits or 503 errors."""
    cooldown_until = _MODEL_COOLDOWNS.get(model_name, 0.0)
    return time.time() < cooldown_until


def _set_model_cooldown(model_name: str, seconds: float = 30.0):
    """Marks a model as cooling down after a rate limit or error."""
    _MODEL_COOLDOWNS[model_name] = time.time() + seconds


# ==============================================================================
# Model-Specific REST Callers
# ==============================================================================

def call_gemini_model_intent(
    model_name: str,
    prompt_text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None,
    timeout: float = 4.0
) -> Optional[AnalysisResult]:
    """Executes a fast Gemini REST call for structured intent analysis."""
    global _GEMINI_KEY_VALID
    api_key = _configured_api_key(settings.GEMINI_API_KEY)
    if not api_key or _GEMINI_KEY_VALID is False or _is_model_cooling_down(model_name):
        return None

    contents: List[Dict[str, Any]] = []
    for ex in FEW_SHOT_EXAMPLES:
        contents.append({"role": "user", "parts": [{"text": ex["input"]}]})
        contents.append({"role": "model", "parts": [{"text": json.dumps(ex["output"])}]})

    if conversation_context:
        for ctx_msg in conversation_context[-6:]:
            role = "model" if ctx_msg.get("sender") in ("agent", "assistant") else "user"
            contents.append({"role": role, "parts": [{"text": ctx_msg.get("text", "")}]})

    contents.append({"role": "user", "parts": [{"text": prompt_text}]})

    payload = {
        "system_instruction": {"parts": [{"text": INTENT_SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json"
        }
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                _GEMINI_KEY_VALID = True
                body = resp.json()
                candidates = body.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_json = parts[0].get("text", "")
                        return _parse_llm_json_response(raw_json)
            elif resp.status_code in (429, 503):
                _set_model_cooldown(model_name, 30.0)
            elif resp.status_code == 400 and ("API_KEY_INVALID" in resp.text or "API key not valid" in resp.text):
                _GEMINI_KEY_VALID = False
    except Exception as exc:
        _set_model_cooldown(model_name, 30.0)
        logger.debug(f"Gemini intent call on {model_name} timed out or failed: {exc}")
    return None


def generate_gemini_response_sync(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    timeout: float = 5.0
) -> Optional[str]:
    """Generates a real conversational response using a single Gemini model."""
    global _GEMINI_KEY_VALID
    api_key = _configured_api_key(settings.GEMINI_API_KEY)
    if not api_key or _GEMINI_KEY_VALID is False or _is_model_cooling_down(model_name):
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 400
        }
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                _GEMINI_KEY_VALID = True
                body = resp.json()
                candidates = body.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
            elif resp.status_code in (429, 503):
                _set_model_cooldown(model_name, 30.0)
            elif resp.status_code == 400 and ("API_KEY_INVALID" in resp.text or "API key not valid" in resp.text):
                _GEMINI_KEY_VALID = False
    except Exception as exc:
        _set_model_cooldown(model_name, 30.0)
        logger.debug(f"Gemini conversational generation on {model_name} timed out/failed: {exc}")
    return None


def generate_openai_response_sync(
    system_prompt: str,
    user_prompt: str,
    timeout: float = 5.0
) -> Optional[str]:
    """Generates a conversational response using OpenAI with strict timeout."""
    global _OPENAI_KEY_VALID
    api_key = _configured_api_key(settings.OPENAI_API_KEY)
    if not api_key or _OPENAI_KEY_VALID is False:
        return None

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                _OPENAI_KEY_VALID = True
                body = resp.json()
                return body["choices"][0]["message"]["content"].strip()
            elif resp.status_code in (401, 403):
                _OPENAI_KEY_VALID = False
    except Exception as exc:
        logger.debug(f"OpenAI response generation error: {exc}")
    return None


# ==============================================================================
# Public Intent Pipeline
# ==============================================================================

def execute_llm_intent_pipeline(
    text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> AnalysisResult:
    """
    Analyzes user message for intent and entities.
    Fast-paths clear regex matches, then iterates active Gemini models.
    """
    clean_text = text.strip()

    # Fast-Path: Unambiguous intent patterns in <1ms
    heuristic = analyze_utterance_rule_based(clean_text, conversation_context)
    if heuristic.confidence >= 0.85 and not heuristic.is_ambiguous:
        heuristic.reasoning = f"[Fast-Path NLU] {heuristic.reasoning or ''}"
        return heuristic

    # Try active Gemini models in priority order
    for model_name in ACTIVE_GEMINI_MODELS:
        res = call_gemini_model_intent(model_name, clean_text, conversation_context, timeout=3.5)
        if res:
            res.reasoning = f"[{model_name}] {res.reasoning or 'Intent classified'}"
            return res

    # OpenAI fallback if available
    openai_key = _configured_api_key(settings.OPENAI_API_KEY)
    if openai_key and _OPENAI_KEY_VALID is not False:
        from app.agent.prompts import INTENT_SYSTEM_PROMPT, FEW_SHOT_EXAMPLES
        try:
            with httpx.Client(timeout=3.5) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={
                        "model": settings.OPENAI_MODEL,
                        "messages": [{"role": "system", "content": INTENT_SYSTEM_PROMPT}, {"role": "user", "content": clean_text}],
                        "response_format": {"type": "json_object"}
                    }
                )
                if resp.status_code == 200:
                    parsed = _parse_llm_json_response(resp.json()["choices"][0]["message"]["content"])
                    if parsed:
                        return parsed
        except Exception:
            pass

    heuristic.reasoning = f"[Heuristics NLU Engine] {heuristic.reasoning or ''}"
    return heuristic


# ==============================================================================
# Real Chatbot Conversational Response Generator
# ==============================================================================

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
    Generates genuine, context-aware chatbot answers powered directly by active LLM models.
    Grounded on verified database data, previous conversation turns, and customer context.
    """
    response_language = detect_voice_language(user_message, "auto")
    is_hindi_target = response_language.startswith("hi")

    language_instruction = (
        "Respond in fluent, warm, conversational Hindi/Hinglish when the customer asks in Hindi or Hinglish. "
        "Respond in natural, empathetic English when the customer asks in English."
    )

    system_prompt = (
        "You are Aura, an empathetic, conversational, articulate, and genuinely helpful AI customer support chatbot (powered by Google Gemini).\n\n"
        "Core Directives:\n"
        "1. Speak naturally like a real human customer support agent in conversational chatbot style.\n"
        "2. Address the customer warmly by their actual name from the context (e.g. 'Hi Komal'). If they introduce themselves, acknowledge it gracefully.\n"
        "3. GROUND YOUR ANSWER ON VERIFIED DATABASE RECORDS:\n"
        "   - If the customer asks for account info, present their name, email, and order summary conversationally.\n"
        "   - Always mention the customer's name when providing order information.\n"
        "   - If an order is CANCELLED: kindly explain that the order was cancelled, apologize, and ask if they would like help reordering.\n"
        "   - If an order is DELIVERED: confirm delivery with carrier and tracking info.\n"
        "   - If an order is IN TRANSIT or PLACED: share the live tracking coordinates, carrier name, tracking number, and expected delivery date with warmth.\n"
        "   - If refund was approved: state the refund amount and 3-5 business day timeline.\n"
        "   - If delivery was rescheduled: confirm the new date warmly.\n"
        "4. If clarification or an Order ID is needed, guide the customer clearly and conversationally.\n"
        "5. NEVER output robotic bullet lists, rigid form menus, or canned boilerplate. Talk directly to the user as a real conversational assistant.\n"
        f"6. {language_instruction}"
    )

    context_payload = {
        "customer_name": customer_name,
        "intent": intent,
        "verified_database_records": tool_results or {},
        "customer_active_orders": customer_orders or [],
        "missing_information": missing_entities or [],
        "suggested_clarification": clarification_prompt,
        "recent_conversation": (conversation_context or [])[-8:],
        "preferred_language": response_language
    }

    user_prompt = (
        f"Verified Database Context: {json.dumps(context_payload, default=str)}\n\n"
        f"Customer Message: \"{user_message}\"\n\n"
        "Respond conversationally to the customer as Aura:"
    )

    # Resolve expected order ID if tool execution took place
    expected_oid = None
    if tool_results and tool_results.get("status") == "success":
        expected_oid = (
            tool_results.get("order_id")
            or (tool_results.get("order") or {}).get("id")
            or (tool_results.get("tracking") or {}).get("order_id")
            or (tool_results.get("refund") or {}).get("order_id")
            or (tool_results.get("cancellation") or {}).get("order_id")
        )

    # 1. Try active Gemini models in priority order
    for model_name in ACTIVE_GEMINI_MODELS:
        reply = generate_gemini_response_sync(model_name, system_prompt, user_prompt, timeout=5.0)
        if reply and len(reply.strip()) > 10:
            if expected_oid is not None and str(expected_oid) not in reply:
                reply = f"{reply}\n\n(Referenced Order #{expected_oid})"
            return reply

    # 2. Try OpenAI fallback if configured
    openai_key = _configured_api_key(settings.OPENAI_API_KEY)
    if openai_key and _OPENAI_KEY_VALID is not False:
        reply = generate_openai_response_sync(system_prompt, user_prompt, timeout=5.0)
        if reply and len(reply.strip()) > 10:
            if expected_oid is not None and str(expected_oid) not in reply:
                reply = f"{reply}\n\n(Referenced Order #{expected_oid})"
            return reply

    # 3. Dynamic Contextual Synthesis Engine (Local fallback only when cloud network is completely unavailable)
    return generate_intelligent_offline_response(
        intent=IntentType(intent) if isinstance(intent, str) and intent in [e.value for e in IntentType] else IntentType.UNKNOWN,
        user_message=user_message,
        tool_results=tool_results,
        customer_name=customer_name,
        customer_orders=customer_orders,
        missing_entities=missing_entities,
        clarification_prompt=clarification_prompt
    )


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


# ==============================================================================
# Context-Aware Dynamic Synthesis Engine (Local Fallback)
# ==============================================================================

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
    Dynamic contextual synthesis engine for offline/network loss scenarios.
    100% conversational paragraphs with zero robotic bullet lists or hardcoded menus.
    Correctly recognizes cancellation status, delivery status, and user sentiment.
    """
    is_hindi = detect_voice_language(user_message, "auto").startswith("hi")
    msg_clean = user_message.strip()
    msg_lower = msg_clean.lower()

    if is_hindi:
        greeting = f"Namaste {customer_name}! " if customer_name else "Namaste! "
    else:
        greeting = f"Hi {customer_name}! " if customer_name else "Hello! "

    if clarification_prompt:
        return clarification_prompt

    # 1. Order Tracking / Inquiries
    if intent == IntentType.ORDER_TRACKING:
        if tool_results and tool_results.get("status") == "success":
            t = tool_results.get("tracking") or tool_results
            oid = t.get("order_id", "N/A")
            raw_st = str(t.get("status", "")).lower()
            carrier = t.get("carrier", "our shipping carrier")
            trk = t.get("tracking_number", "")
            exp_date = t.get("expected_delivery_str", "soon")
            is_delivered = t.get("is_delivered", False)

            # Context Check: CANCELLED
            if "cancel" in raw_st:
                if is_hindi:
                    return f"{greeting}Maine aapka Order #{oid} check kiya hai, aur yeh order actually cancel ho chuka hai, isliye yeh deliver nahi hoga. Main iski vajah check karne ya naya order place karne mein aapki madad kar sakti hoon."
                return f"{greeting}I looked into Order #{oid} for you, and it appears this order was actually cancelled, so it won't be arriving. I apologize for any confusion! Would you like me to check why it was cancelled, or help you place a new order for these items?"

            # Context Check: DELIVERED
            if is_delivered or "deliver" in raw_st:
                if is_hindi:
                    return f"{greeting}Aapka Order #{oid} safalta-poorvak deliver ho chuka hai ({carrier}, Tracking: {trk}). Agar aapko item milne mein koi dikkat ho ya return/refund chahiye, toh mujhe batayein."
                return f"{greeting}Good news! Your Order #{oid} was already delivered via {carrier} (tracking #{trk}). If you had trouble locating the package or need help with a return or refund, please let me know and I'll be glad to help!"

            # Context Check: IN TRANSIT / ON THE WAY
            if is_hindi:
                return f"{greeting}Aapka Order #{oid} abhi {carrier} ke zariye transit mein hai (Tracking: {trk}) aur {exp_date} tak deliver hone ki ummeed hai. Package schedule ke hisaab se sahi chal raha hai!"
            return f"{greeting}I checked on your Order #{oid} for you! The package is currently in transit with {carrier} under tracking number {trk}, and is scheduled to reach you around {exp_date}. Everything is progressing smoothly on schedule!"

        elif customer_orders and len(customer_orders) > 0:
            primary_order = customer_orders[0]
            oid = primary_order.get("id")
            st = str(primary_order.get("status", "")).lower()
            exp = primary_order.get("expected_delivery_str", "upcoming")
            if "cancel" in st:
                return f"{greeting}I found Order #{oid} on your account, but it is currently marked as cancelled. Were you asking about this order, or did you have another order number in mind?"
            return f"{greeting}I found active Order #{oid} on your account, which is currently {st} and scheduled for delivery around {exp}. Would you like live tracking details for this order, or are you inquiring about a different one?"
        else:
            return f"{greeting}I'd be glad to track your package! Could you please share your Order ID (like Order #1) so I can pull up the live shipment details for you?"

    # 2. Refund Request
    elif intent == IntentType.REFUND_REQUEST:
        if tool_results and tool_results.get("success"):
            r = tool_results.get("refund") or tool_results
            oid = r.get("order_id", "N/A")
            amt = float(r.get("amount", 0.0))
            if is_hindi:
                return f"{greeting}Aapke Order #{oid} ke liye ₹{amt:.2f} ka refund approve ho chuka hai. Yeh amount 3 se 5 business days mein aapke bank account mein reflect ho jayega."
            return f"{greeting}Great news! Your refund for Order #{oid} has been approved for ${amt:.2f}. The credit will be sent back to your original payment method within 3 to 5 business days."
        elif tool_results and not tool_results.get("success"):
            err = tool_results.get("error", "The order is not eligible for refund.")
            return f"{greeting}I took a look at your refund request, but {err.lower() if err.startswith('The') else err}. Let me know if you would like me to connect you with our support team."
        else:
            return f"{greeting}We provide full refunds within 30 days of delivery. Could you please share your Order ID and the reason for the refund so I can submit this for you right away?"

    # 3. Order Cancellation
    elif intent == IntentType.ORDER_CANCELLATION:
        if tool_results and tool_results.get("success"):
            oid = tool_results.get("order_id", "N/A")
            if is_hindi:
                return f"{greeting}Aapka Order #{oid} safalta-poorvak cancel kar diya gaya hai. Kisi bhi payment charge ko release kar diya gaya hai."
            return f"{greeting}I have successfully cancelled Order #{oid} for you! Any pending charges have been released, and you'll receive a confirmation email shortly."
        elif tool_results and not tool_results.get("success"):
            err = tool_results.get("error", "This order cannot be cancelled as it has already shipped.")
            return f"{greeting}I checked on that cancellation for you, but {err.lower() if err.startswith('This') else err}"
        else:
            return f"{greeting}Orders can be cancelled anytime before they are shipped out. Which Order ID would you like me to cancel for you?"

    # 4. Address Update
    elif intent == IntentType.ADDRESS_UPDATE:
        if tool_results and tool_results.get("success"):
            oid = tool_results.get("order_id")
            new_addr = tool_results.get("new_address", "")
            target = f"for Order #{oid}" if oid else "on your account"
            return f"{greeting}I have updated your shipping destination address {target} to: {new_addr}. Our dispatch team has been notified!"
        else:
            return f"{greeting}I can definitely help update your delivery address! Please provide your Order ID along with the new shipping address."

    # 5. Password Reset
    elif intent == IntentType.PASSWORD_RESET:
        if tool_results and tool_results.get("success"):
            email = tool_results.get("email", "your account email")
            return f"{greeting}A secure password reset link has just been sent to {email}. Please check your inbox and follow the link within the next 15 minutes."
        else:
            return f"{greeting}I can send you a password reset link right away. Could you share the email address associated with your account?"

    # 6. Ticket Escalation
    elif intent == IntentType.TICKET_CREATION:
        if tool_results and tool_results.get("success"):
            tid = tool_results.get("ticket_id", "N/A")
            return f"{greeting}I have created priority support ticket #{tid} for you. A member of our specialist team will review your inquiry and reach out shortly."
        else:
            return f"{greeting}I'd be glad to open a support ticket with our human support team. Could you please share the details of what you're experiencing?"

    # 7. Outbound Voice Call
    elif intent == IntentType.OUTBOUND_CALL_REQUEST:
        if tool_results and tool_results.get("phone_number"):
            p = tool_results.get("phone_number")
            return f"{greeting}I am dialing your number ({p}) right now! Please pick up when your phone rings to speak live with our AI voice agent."
        else:
            return f"{greeting}I would love to give you a call! Please provide your phone number with your country code (e.g. +91...) so I can connect with you."

    # 8. Greetings & General Inquiries
    else:
        if customer_name and any(word in msg_lower for word in ["hello", "hi", "hey", "namaste", "namaskar"]):
            if is_hindi:
                return f"Namaste {customer_name}! Aapse baat karke bahut achha laga. Main Aura hoon. Aaj main aapki kis tarah madad kar sakti hoon?"
            return f"Hi {customer_name}! It's great to chat with you today. I'm Aura, your AI customer support assistant. How can I help you with your orders, tracking, or account?"
        elif any(w in msg_lower for w in ["hi", "hello", "hey", "good morning", "good evening"]):
            if is_hindi:
                return "Namaste! Main Aura hoon, aapki customer care AI assistant. Main order tracking, refund, cancellation, ya account queries mein aapki madad kar sakti hoon. Batayein aapko kya jaanna hai?"
            return "Hello! I'm Aura, your AI customer support assistant. I'm here to help with real-time order tracking, cancellations, refunds, or address updates. What can I do for you today?"
        elif any(w in msg_lower for w in ["who are you", "what can you do", "help"]):
            return "I am Aura, an autonomous AI customer support chatbot. I can help you track shipments in real time, process refunds, cancel orders, update addresses, and answer any customer service questions. How can I assist you right now?"
        else:
            return f"{greeting}I'm here and ready to help! Could you share your Order ID or give me a few details on what you need assistance with?"
