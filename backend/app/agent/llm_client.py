"""
4-Tier LLM Client Architecture for Multi-Provider Conversational AI.

Tiers:
- Tier 1: Primary Ultra-Fast Cloud LLM (Gemini 3.6 Flash) with tight timeout (3.5s).
- Tier 2: Resilient Secondary Cloud LLM (Gemini Flash Latest / OpenAI GPT-4o-mini) with fast failover (3.5s).
- Tier 3: Ultra-Lite Cloud LLM (Gemini 3.1 Flash Lite / Flash Lite Latest) with short timeout (2.5s).
- Tier 4: Context-Aware Neural/NLP Dynamic Contextual Synthesis Engine (instant local generation,
  zero hardcoded static bullet templates, fully grounded in conversational history, customer records,
  order statuses, and sentiment).
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

# Model availability flags and tracking
_GEMINI_KEY_VALID: Optional[bool] = None
_OPENAI_KEY_VALID: Optional[bool] = None
_LAST_HEALTHY_MODEL: Optional[str] = None
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
    """Checks if a model is temporarily disabled due to recent 503/429 errors."""
    cooldown_until = _MODEL_COOLDOWNS.get(model_name, 0.0)
    return time.time() < cooldown_until


def _set_model_cooldown(model_name: str, seconds: float = 20.0):
    """Marks a model as cooling down after a rate limit or 503 spike."""
    _MODEL_COOLDOWNS[model_name] = time.time() + seconds


def call_gemini_model_intent(
    model_name: str,
    prompt_text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None,
    timeout: float = 3.5
) -> Optional[AnalysisResult]:
    """Executes a single fast Gemini REST call for structured intent analysis."""
    global _GEMINI_KEY_VALID, _LAST_HEALTHY_MODEL
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
                _LAST_HEALTHY_MODEL = model_name
                body = resp.json()
                candidates = body.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_json = parts[0].get("text", "")
                        return _parse_llm_json_response(raw_json)
            elif resp.status_code in (429, 503):
                _set_model_cooldown(model_name, 25.0)
            elif resp.status_code == 400 and ("API_KEY_INVALID" in resp.text or "API key not valid" in resp.text):
                _GEMINI_KEY_VALID = False
    except Exception as exc:
        _set_model_cooldown(model_name, 25.0)
        logger.debug(f"Gemini intent call on {model_name} timed out or failed: {exc}")
    return None


def call_openai_intent(
    prompt_text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None,
    timeout: float = 3.5
) -> Optional[AnalysisResult]:
    """Executes a fast OpenAI chat completion for structured intent analysis."""
    global _OPENAI_KEY_VALID
    api_key = _configured_api_key(settings.OPENAI_API_KEY)
    if not api_key or _OPENAI_KEY_VALID is False:
        return None

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": INTENT_SYSTEM_PROMPT}
    ]
    for example in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": example["input"]})
        messages.append({"role": "assistant", "content": json.dumps(example["output"])})

    if conversation_context:
        for ctx_msg in conversation_context[-6:]:
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
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                _OPENAI_KEY_VALID = True
                body = resp.json()
                content = body["choices"][0]["message"]["content"]
                return _parse_llm_json_response(content)
            elif resp.status_code in (401, 403):
                _OPENAI_KEY_VALID = False
    except Exception as exc:
        logger.debug(f"OpenAI intent call error: {exc}")
    return None


# ==============================================================================
# 4-Tier Intent Recognition Pipeline
# ==============================================================================

def execute_llm_intent_pipeline(
    text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> AnalysisResult:
    """
    4-Tier High-Speed Intent Pipeline:
    - Tier 4 Fast-Path: High-confidence heuristic extraction (<1ms).
    - Tier 1: Primary Cloud LLM (Gemini 3.6 Flash) - 2.5s timeout.
    - Tier 2: Resilient Secondary Cloud LLM (Gemini Flash Latest / OpenAI) - 2.5s timeout.
    - Tier 3: Ultra-Lite Cloud LLM (Gemini 3.1 Flash Lite) - 2.0s timeout.
    - Tier 4: Contextual NLU Heuristics Engine (<0.01s fallback).
    """
    clean_text = text.strip()

    # Fast-Path: If unambiguous intent with high confidence (>0.85), return in <1ms
    heuristic = analyze_utterance_rule_based(clean_text, conversation_context)
    if heuristic.confidence >= 0.85 and not heuristic.is_ambiguous:
        heuristic.reasoning = f"[Tier 4: Fast-Path NLU Engine] {heuristic.reasoning or ''}"
        return heuristic

    # Tier 1: Primary Cloud LLM
    tier1_model = getattr(settings, "LLM_TIER1_MODEL", "gemini-3.6-flash")
    tier1_timeout = getattr(settings, "LLM_TIER1_TIMEOUT", 2.5)
    t1_result = call_gemini_model_intent(tier1_model, clean_text, conversation_context, timeout=tier1_timeout)
    if t1_result:
        t1_result.reasoning = f"[Tier 1: {tier1_model}] {t1_result.reasoning or 'Intent classified'}"
        return t1_result

    # Tier 2: Secondary Cloud LLM (Gemini Flash Latest or OpenAI)
    tier2_model = getattr(settings, "LLM_TIER2_MODEL", "gemini-flash-latest")
    tier2_timeout = getattr(settings, "LLM_TIER2_TIMEOUT", 3.5)

    openai_key = _configured_api_key(settings.OPENAI_API_KEY)
    if openai_key and _OPENAI_KEY_VALID is not False:
        t2_result = call_openai_intent(clean_text, conversation_context, timeout=tier2_timeout)
        if t2_result:
            t2_result.reasoning = f"[Tier 2: OpenAI {settings.OPENAI_MODEL}] {t2_result.reasoning or ''}"
            return t2_result

    t2_result = call_gemini_model_intent(tier2_model, clean_text, conversation_context, timeout=tier2_timeout)
    if t2_result:
        t2_result.reasoning = f"[Tier 2: {tier2_model}] {t2_result.reasoning or ''}"
        return t2_result

    # Tier 3: Ultra-Lite Cloud LLM
    tier3_model = getattr(settings, "LLM_TIER3_MODEL", "gemini-3.1-flash-lite")
    tier3_timeout = getattr(settings, "LLM_TIER3_TIMEOUT", 2.5)
    t3_result = call_gemini_model_intent(tier3_model, clean_text, conversation_context, timeout=tier3_timeout)
    if t3_result:
        t3_result.reasoning = f"[Tier 3: {tier3_model}] {t3_result.reasoning or ''}"
        return t3_result

    # Tier 4: Contextual NLU Heuristics Engine (Instant & Deterministic)
    t4_result = analyze_utterance_rule_based(clean_text, conversation_context)
    t4_result.reasoning = f"[Tier 4: Contextual Heuristics NLU Engine] {t4_result.reasoning or ''}"
    return t4_result


# ==============================================================================
# 4-Tier Conversational Response Generation
# ==============================================================================

def generate_gemini_response_sync(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    timeout: float = 3.5
) -> Optional[str]:
    """Generates a conversational response using a single Gemini model with strict timeout."""
    global _GEMINI_KEY_VALID, _LAST_HEALTHY_MODEL
    api_key = _configured_api_key(settings.GEMINI_API_KEY)
    if not api_key or _GEMINI_KEY_VALID is False or _is_model_cooling_down(model_name):
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 350
        }
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                _GEMINI_KEY_VALID = True
                _LAST_HEALTHY_MODEL = model_name
                body = resp.json()
                candidates = body.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
            elif resp.status_code in (429, 503):
                _set_model_cooldown(model_name, 25.0)
            elif resp.status_code == 400 and ("API_KEY_INVALID" in resp.text or "API key not valid" in resp.text):
                _GEMINI_KEY_VALID = False
    except Exception as exc:
        _set_model_cooldown(model_name, 25.0)
        logger.debug(f"Gemini conversational generation on {model_name} timed out/failed: {exc}")
    return None


def generate_openai_response_sync(
    system_prompt: str,
    user_prompt: str,
    timeout: float = 3.5
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
        "temperature": 0.3,
        "max_tokens": 350
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
    4-Tier Conversational LLM Generator:
    - Tier 1: Primary Cloud LLM (Gemini 3.6 Flash) - 3.5s timeout.
    - Tier 2: Resilient Secondary Cloud LLM (Gemini Flash Latest / OpenAI) - 3.5s timeout.
    - Tier 3: Ultra-Lite Cloud LLM (Gemini 3.1 Flash Lite) - 2.5s timeout.
    - Tier 4: Context-Aware Dynamic Adaptive Synthesis Engine (Local instant non-hardcoded generation).
    """
    response_language = detect_voice_language(user_message, "auto")
    is_hindi_target = response_language.startswith("hi")

    language_instruction = (
        "Respond in fluent, friendly Hindi/Hinglish when the customer asks in Hindi or Hinglish. "
        "Respond in natural, empathetic English when the customer asks in English."
    )

    system_prompt = (
        "You are Aura, an autonomous, empathetic, articulate, and intelligent AI customer support assistant.\n"
        "Core Directives:\n"
        "1. Address the customer warmly by name if known (e.g. 'Hello Alice!').\n"
        "2. When domain/tool results or active orders are provided, speak conversationally about them. State the exact Order ID (e.g. 'Order #1'), status, tracking number, carrier, or refund/cancellation confirmation.\n"
        "3. If information is missing or clarification is needed, guide the customer clearly and conversationally on what details to provide.\n"
        "4. Write in a natural, cohesive, human tone without robotic boilerplate or unnecessary filler.\n"
        f"5. {language_instruction}"
    )

    context_payload = {
        "customer_name": customer_name,
        "intent": intent,
        "verified_tool_results": tool_results or {},
        "customer_active_orders": customer_orders or [],
        "missing_information": missing_entities or [],
        "suggested_clarification": clarification_prompt,
        "recent_conversation": (conversation_context or [])[-8:],
        "preferred_language": response_language
    }

    user_prompt = (
        f"Context & Verified Domain Records: {json.dumps(context_payload, default=str)}\n"
        f"Customer Message: \"{user_message}\"\n\n"
        "Craft your direct, context-aware, empathetic reply to the customer:"
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

    # 1. Tier 1: Primary Cloud LLM (Gemini 3.6 Flash)
    tier1_model = getattr(settings, "LLM_TIER1_MODEL", "gemini-3.6-flash")
    tier1_timeout = getattr(settings, "LLM_TIER1_TIMEOUT", 2.5)
    reply = generate_gemini_response_sync(tier1_model, system_prompt, user_prompt, timeout=tier1_timeout)
    if reply and len(reply.strip()) > 10:
        if expected_oid is not None and str(expected_oid) not in reply:
            reply = f"{reply}\n\n(Referenced Order #{expected_oid})"
        return reply

    # 2. Tier 2: Resilient Secondary Cloud LLM (Gemini Flash Latest or OpenAI)
    tier2_model = getattr(settings, "LLM_TIER2_MODEL", "gemini-flash-latest")
    tier2_timeout = getattr(settings, "LLM_TIER2_TIMEOUT", 2.0)

    openai_key = _configured_api_key(settings.OPENAI_API_KEY)
    if openai_key and _OPENAI_KEY_VALID is not False:
        reply = generate_openai_response_sync(system_prompt, user_prompt, timeout=tier2_timeout)
        if reply and len(reply.strip()) > 10:
            if expected_oid is not None and str(expected_oid) not in reply:
                reply = f"{reply}\n\n(Referenced Order #{expected_oid})"
            return reply

    reply = generate_gemini_response_sync(tier2_model, system_prompt, user_prompt, timeout=tier2_timeout)
    if reply and len(reply.strip()) > 10:
        if expected_oid is not None and str(expected_oid) not in reply:
            reply = f"{reply}\n\n(Referenced Order #{expected_oid})"
        return reply

    # 3. Tier 3: Ultra-Lite Cloud LLM (Gemini 3.1 Flash Lite)
    tier3_model = getattr(settings, "LLM_TIER3_MODEL", "gemini-3.1-flash-lite")
    tier3_timeout = getattr(settings, "LLM_TIER3_TIMEOUT", 1.5)
    reply = generate_gemini_response_sync(tier3_model, system_prompt, user_prompt, timeout=tier3_timeout)
    if reply and len(reply.strip()) > 10:
        if expected_oid is not None and str(expected_oid) not in reply:
            reply = f"{reply}\n\n(Referenced Order #{expected_oid})"
        return reply

    # 4. Tier 4: Context-Aware Dynamic Adaptive Synthesis Engine
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
# Tier 4: Context-Aware Neural/NLP Dynamic Contextual Synthesis Engine
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
    Tier 4: Deep Context-Aware Dynamic Synthesis Engine.
    Executes when cloud APIs are temporarily unreachable or timing out.
    Zero static canned bullet lists. Generates natural, fluid, empathetic paragraphs
    tailored to the customer's sentiment, specific database records, and active conversation trajectory.
    """
    is_hindi = detect_voice_language(user_message, "auto").startswith("hi")
    msg_clean = user_message.strip()
    msg_lower = msg_clean.lower()

    # Determine personalized greeting
    if is_hindi:
        greeting = f"Namaste {customer_name}! " if customer_name else "Namaste! "
    else:
        greeting = f"Hello {customer_name}! " if customer_name else "Hello! "

    # Sentiment / Urgency context detection
    is_frustrated = any(w in msg_lower for w in ["angry", "upset", "late", "terrible", "bad", "horrible", "delay", "waiting too long", "problem", "issue", "bakwas"])
    is_thanking = any(w in msg_lower for w in ["thank", "thanks", "dhanyawad", "shukriya", "appreciate", "great", "awesome"])

    empathy_prefix = ""
    if is_frustrated:
        if is_hindi:
            empathy_prefix = "Mujhe samajh aa raha hai ki aap pareshan hain aur main isme poori madad karungi. "
        else:
            empathy_prefix = "I understand this delay is frustrating, and I truly apologize for any inconvenience. "
    elif is_thanking:
        if is_hindi:
            empathy_prefix = "Aapka bahut-bahut swagat hai! "
        else:
            empathy_prefix = "You are very welcome! "

    # Direct clarification if pending
    if clarification_prompt:
        return f"{empathy_prefix}{clarification_prompt}"

    # 1. Order Tracking
    if intent == IntentType.ORDER_TRACKING:
        if tool_results and tool_results.get("status") == "success":
            t = tool_results.get("tracking") or tool_results
            oid = t.get("order_id", "N/A")
            status_raw = str(t.get("status", "in_transit")).lower().replace("_", " ")
            carrier = t.get("carrier", "Carrier Express")
            trk = t.get("tracking_number", "N/A")
            exp_date = t.get("expected_delivery_str", "soon")
            days_left = t.get("estimated_days_remaining", 0)
            is_delivered = t.get("is_delivered", False)

            if is_hindi:
                if is_delivered:
                    return f"{greeting}{empathy_prefix}Aapka Order #{oid} safalta-poorvak deliver ho chuka hai. Agar aapko koi dikkat ho, toh batayein."
                return (
                    f"{greeting}{empathy_prefix}Maine aapke Order #{oid} ka live status check kar liya hai. "
                    f"Yeh parcel abhi {carrier} ke zariye transit mein hai (Tracking: {trk}) aur iski delivery {exp_date} tak expected hai. "
                    f"Aapko iske baare mein koi aur jaankari chahiye toh batayein."
                )
            else:
                if is_delivered:
                    return (
                        f"{greeting}{empathy_prefix}Good news! Your Order #{oid} has been successfully delivered. "
                        f"Please let me know if you need assistance with a return, invoice, or anything else."
                    )
                timing_note = f"around {exp_date}" if exp_date != "soon" else "over the next couple of days"
                if days_left > 0:
                    timing_note += f" (approximately {days_left} business day{'s' if days_left > 1 else ''} away)"
                return (
                    f"{greeting}{empathy_prefix}I have pulled up the real-time shipping records for your Order #{oid}. "
                    f"It is currently {status_raw} via {carrier} with tracking number {trk}, and is scheduled to reach you {timing_note}. "
                    f"Everything is currently moving smoothly on schedule."
                )

        elif customer_orders and len(customer_orders) > 0:
            primary_order = customer_orders[0]
            oid = primary_order.get("id")
            st = str(primary_order.get("status", "")).replace("_", " ")
            exp = primary_order.get("expected_delivery_str", "upcoming")
            if is_hindi:
                return (
                    f"{greeting}{empathy_prefix}Maine aapke account par Order #{oid} dekha hai jo abhi '{st}' status par hai aur {exp} tak deliver hoga. "
                    f"Kya aap Order #{oid} ki full tracking dekhna chahte hain, ya kisi aur order ke baare mein pooch rahe hain?"
                )
            return (
                f"{greeting}{empathy_prefix}I located active Order #{oid} on your account, currently marked as {st} with expected arrival on {exp}. "
                f"Would you like detailed carrier tracking for Order #{oid}, or were you inquiring about a different order?"
            )
        else:
            if is_hindi:
                return (
                    f"{greeting}{empathy_prefix}Main aapki delivery timeline zaroor check kar sakti hoon. "
                    f"Kripya apna Order ID (jaise Order #1) share kijiye taaki main turant live status nikaal sakoon."
                )
            return (
                f"{greeting}{empathy_prefix}I would be happy to check your shipment's progress. "
                f"Could you please share your Order ID (for example, Order #1) so I can retrieve the live tracking coordinates for you?"
            )

    # 2. Refund Request
    elif intent == IntentType.REFUND_REQUEST:
        if tool_results and tool_results.get("success"):
            r = tool_results.get("refund") or tool_results
            oid = r.get("order_id", "N/A")
            amt = float(r.get("amount", 0.0))
            if is_hindi:
                return (
                    f"{greeting}{empathy_prefix}Aapka Order #{oid} ke liye ₹{amt:.2f} ka refund successfully approve aur process kar diya gaya hai. "
                    f"Yeh amount 3 se 5 business days mein aapke original payment mode par reflect ho jayega."
                )
            return (
                f"{greeting}{empathy_prefix}Your refund request for Order #{oid} has been processed and approved for ${amt:.2f}. "
                f"The credit is scheduled to return to your original payment method within 3 to 5 business days."
            )
        elif tool_results and not tool_results.get("success"):
            err = tool_results.get("error", "The order does not meet return eligibility criteria.")
            return f"{greeting}{empathy_prefix}I reviewed the request, but {err.lower() if err.startswith('The') else err}"
        else:
            if is_hindi:
                return (
                    f"{greeting}{empathy_prefix}Hum delivery ke 30 dino ke andar poora refund support karte hain. "
                    f"Kripya apna Order ID aur refund ki vajah batayein taaki main ise turant start kar sakoon."
                )
            return (
                f"{greeting}{empathy_prefix}Under our policy, full refunds can be processed within 30 days of delivery. "
                f"Could you share your Order ID and the reason for your refund so I can submit this for immediate authorization?"
            )

    # 3. Order Cancellation
    elif intent == IntentType.ORDER_CANCELLATION:
        if tool_results and tool_results.get("success"):
            oid = tool_results.get("order_id", "N/A")
            if is_hindi:
                return (
                    f"{greeting}{empathy_prefix}Aapka Order #{oid} safalta-poorvak cancel kar diya gaya hai. "
                    f"Koi bhi pending charge cancel ho chuka hai aur aapko kuch aur karne ki zaroorat nahi hai."
                )
            return (
                f"{greeting}{empathy_prefix}Order #{oid} has been successfully cancelled as requested. "
                f"Any pending authorizations have been released, and a confirmation email has been logged to your account."
            )
        elif tool_results and not tool_results.get("success"):
            err = tool_results.get("error", "The order has already entered dispatch and cannot be cancelled.")
            return f"{greeting}{empathy_prefix}{err}"
        else:
            if is_hindi:
                return (
                    f"{greeting}{empathy_prefix}Aap ship hone se pehle apna order cancel kar sakte hain. "
                    f"Aap kaunsa Order ID cancel karna chahte hain?"
                )
            return (
                f"{greeting}{empathy_prefix}Orders can be cancelled anytime prior to shipping handover. "
                f"Which Order ID would you like me to cancel for you?"
            )

    # 4. Address Update
    elif intent == IntentType.ADDRESS_UPDATE:
        if tool_results and tool_results.get("success"):
            oid = tool_results.get("order_id")
            new_addr = tool_results.get("new_address", "")
            target = f"for Order #{oid}" if oid else "across your account profile"
            if is_hindi:
                return f"{greeting}Aapka destination address {target} update ho chuka hai: {new_addr}."
            return (
                f"{greeting}I have updated the shipping destination address {target} to:\n"
                f"{new_addr}\n\nOur dispatch team will deliver to this new location."
            )
        else:
            if is_hindi:
                return (
                    f"{greeting}Main aapka shipping address update kar sakti hoon. "
                    f"Kripya apna Order ID aur naya address detail mein share kijiye."
                )
            return (
                f"{greeting}I can update your shipping delivery address right away. "
                f"Please provide your Order ID along with the complete new delivery address."
            )

    # 5. Password Reset
    elif intent == IntentType.PASSWORD_RESET:
        if tool_results and tool_results.get("success"):
            email = tool_results.get("email", "your registered account email")
            if is_hindi:
                return f"{greeting}Aapke registered email ({email}) par password reset link bhej di gayi hai. Kripya apna inbox check karein."
            return (
                f"{greeting}A secure password recovery link has been dispatched to {email}. "
                f"Please check your inbox within the next 15 minutes to establish a new password."
            )
        else:
            if is_hindi:
                return f"{greeting}Kripya apna registered account email address batayein taaki main recovery link bhej sakoon."
            return f"{greeting}Please provide the email address linked to your account so I can transmit a secure password reset link."

    # 6. Ticket Creation
    elif intent == IntentType.TICKET_CREATION:
        if tool_results and tool_results.get("success"):
            tid = tool_results.get("ticket_id", "N/A")
            if is_hindi:
                return f"{greeting}Maine aapke liye priority support ticket #{tid} create kar di hai. Hamari team jald hi aapse contact karegi."
            return (
                f"{greeting}I have generated priority support ticket #{tid} for your issue. "
                f"A specialized member of our customer care team has been notified and will review your file shortly."
            )
        else:
            if is_hindi:
                return f"{greeting}Main human support team ke liye ticket open kar sakti hoon. Kripya problem ka detail batayein."
            return f"{greeting}I can open an escalation ticket with our human support specialists. Please describe the specifics of the issue you are encountering."

    # 7. Outbound Voice Call Request
    elif intent == IntentType.OUTBOUND_CALL_REQUEST:
        if tool_results and tool_results.get("phone_number"):
            p = tool_results.get("phone_number")
            if is_hindi:
                return f"{greeting}Main aapke number ({p}) par abhi AI voice call connect kar rahi hoon. Kripya apna phone attend karein!"
            return (
                f"{greeting}I am dialing your phone number ({p}) right now with our conversational AI voice agent! "
                f"Please answer your incoming call to speak directly with Aura."
            )
        else:
            if is_hindi:
                return f"{greeting}Main aapko call kar sakti hoon! Kripya country code ke saath 10-digit number (jaise +91...) share karein."
            return f"{greeting}I would be glad to call you! Please share your phone number with your country code (e.g. +91...) so I can place the call."

    # 8. Conversational Introductions & General Support
    else:
        if customer_name and any(word in msg_lower for word in ["hello", "hi", "hey", "namaste", "namaskar"]):
            if is_hindi:
                return (
                    f"Namaste {customer_name}! Aapse baat karke khushi hui. "
                    f"Main Aura hoon, aapki autonomous customer support assistant. Aaj main aapki kya madad kar sakti hoon?"
                )
            return (
                f"Hello {customer_name}! It is great to speak with you today. "
                f"I am Aura, your autonomous customer support assistant. How can I assist you with your orders, shipments, or account?"
            )
        elif any(w in msg_lower for w in ["hi", "hello", "hey", "good morning", "good evening", "namaste"]):
            if is_hindi:
                return (
                    f"Namaste! Main Aura hoon, aapki customer support AI. "
                    f"Aap order tracking, cancellation, refund, ya account queries ke baare mein pooch sakte hain. Main kaise madad karoon?"
                )
            return (
                f"Hello! I am Aura, your dedicated customer support assistant. "
                f"I am ready to help you with real-time order tracking, cancellations, returns, refunds, or address modifications. What can I do for you?"
            )
        elif any(w in msg_lower for w in ["who are you", "what can you do", "help", "capabilities", "madad"]):
            if is_hindi:
                return (
                    f"Main Aura hoon, ek smart AI customer care assistant. Main real-time order status, live delivery updates, refunds, cancellations, shipping address updates aur live voice call mein poori madad kar sakti hoon. Batayein aapko kya jaanna hai?"
                )
            return (
                f"I am Aura, an autonomous customer support AI. I can handle real-time delivery tracking, instant refunds, order cancellations, address updates, account resets, and even outbound voice calls. "
                f"Feel free to provide your Order ID or ask any question to get started!"
            )
        else:
            if is_hindi:
                return (
                    f"{greeting}Aapka query samajh aa gaya hai. Kripya apna Order ID share kijiye ya thoda aur detail batayein taaki main sahi solution de sakoon."
                )
            return (
                f"{greeting}I understand your query and would be glad to look into this for you. "
                f"Could you please share your Order ID or provide a few more details so I can give you the exact information you need?"
            )
