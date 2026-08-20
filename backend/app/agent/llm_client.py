"""
LLM Client for OpenAI and Google Gemini with configurable providers,
structured JSON schema extraction, and deterministic fallback.
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
        entities = ExtractedEntities(
            order_id=raw_entities.get("order_id"),
            customer_id=raw_entities.get("customer_id"),
            email=raw_entities.get("email"),
            phone=raw_entities.get("phone"),
            product_info=raw_entities.get("product_info"),
            refund_reason=raw_entities.get("refund_reason"),
            new_address=raw_entities.get("new_address"),
            relevant_dates=raw_entities.get("relevant_dates") or [],
            confidence_scores=raw_entities.get("confidence_scores") or {}
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


async def call_openai_async(
    prompt_text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> Optional[AnalysisResult]:
    """Calls OpenAI chat completions API for intent classification and entity extraction."""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.debug("OpenAI API key not configured, falling back to heuristics.")
        return None

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": INTENT_SYSTEM_PROMPT}
    ]

    # Add few-shot examples
    for example in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": example["input"]})
        messages.append({"role": "assistant", "content": json.dumps(example["output"])})

    # Add conversation context if available
    if conversation_context:
        for ctx_msg in conversation_context:
            role = "assistant" if ctx_msg.get("sender") in ("agent", "assistant") else "user"
            messages.append({"role": role, "content": ctx_msg.get("text", "")})

    # Current user utterance
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
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                body = resp.json()
                content = body["choices"][0]["message"]["content"]
                return _parse_llm_json_response(content)
            else:
                logger.error(f"OpenAI API error {resp.status_code}: {resp.text}")
                return None
    except Exception as exc:
        logger.error(f"OpenAI connection error: {exc}")
        return None


async def call_gemini_async(
    prompt_text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> Optional[AnalysisResult]:
    """Calls Google Gemini REST API with structured JSON output."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.debug("Gemini API key not configured, falling back to heuristics.")
        return None

    model = settings.GEMINI_MODEL or "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Build multi-turn contents
    contents: List[Dict[str, Any]] = []

    # Insert few-shots
    for ex in FEW_SHOT_EXAMPLES:
        contents.append({
            "role": "user",
            "parts": [{"text": ex["input"]}]
        })
        contents.append({
            "role": "model",
            "parts": [{"text": json.dumps(ex["output"])}]
        })

    # Insert conversation context
    if conversation_context:
        for ctx_msg in conversation_context:
            role = "model" if ctx_msg.get("sender") in ("agent", "assistant") else "user"
            contents.append({
                "role": role,
                "parts": [{"text": ctx_msg.get("text", "")}]
            })

    # Current user utterance
    contents.append({
        "role": "user",
        "parts": [{"text": prompt_text}]
    })

    payload = {
        "system_instruction": {
            "parts": [{"text": INTENT_SYSTEM_PROMPT}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": settings.LLM_TEMPERATURE,
            "response_mime_type": "application/json"
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                body = resp.json()
                candidates = body.get("candidates", [])
                if candidates:
                    content_parts = candidates[0].get("content", {}).get("parts", [])
                    if content_parts:
                        raw_json = content_parts[0].get("text", "")
                        return _parse_llm_json_response(raw_json)
            else:
                logger.error(f"Gemini API error {resp.status_code}: {resp.text}")
                return None
    except Exception as exc:
        logger.error(f"Gemini connection error: {exc}")
        return None


def call_openai_sync(
    prompt_text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> Optional[AnalysisResult]:
    """Synchronous wrapper for OpenAI API."""
    api_key = settings.OPENAI_API_KEY
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
        with httpx.Client(timeout=15.0) as client:
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
    """Synchronous wrapper for Gemini REST API."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None

    model = settings.GEMINI_MODEL or "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

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

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                body = resp.json()
                candidates = body.get("candidates", [])
                if candidates:
                    content_parts = candidates[0].get("content", {}).get("parts", [])
                    if content_parts:
                        raw_json = content_parts[0].get("text", "")
                        return _parse_llm_json_response(raw_json)
            return None
    except Exception as exc:
        logger.error(f"Gemini sync call error: {exc}")
        return None


def generate_natural_llm_response(
    intent: str,
    tool_results: Dict[str, Any],
    user_message: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> Optional[str]:
    """
    Generates a grounded, natural conversational response using the active LLM.
    Strictly instructs the model to adhere to the provided tool execution output without hallucination.
    """
    provider = (settings.LLM_PROVIDER or "").lower().strip()
    system_prompt = (
        "You are Aura, an autonomous, highly professional and empathetic customer support agent. "
        "Your task is to synthesize a helpful, warm, and clear customer response based STRICTLY "
        "on the verified tool results and data provided below. Do NOT hallucinate or alter tracking numbers, "
        "dates, amounts, or policies. Keep the response concise, formatted nicely with bullet points where appropriate."
    )

    context_str = json.dumps(tool_results, default=str)
    prompt = (
        f"Customer Intent: {intent}\n"
        f"Verified Tool & Domain Results: {context_str}\n"
        f"Customer Inquiry: \"{user_message}\"\n\n"
        "Generate the final response to the customer:"
    )

    # 1. Try Gemini
    if provider == "gemini" and settings.GEMINI_API_KEY:
        try:
            model = settings.GEMINI_MODEL or "gemini-3.6-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 500
                }
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    body = resp.json()
                    candidates = body.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
        except Exception as exc:
            logger.warning(f"Gemini natural response generation failed: {exc}")

    # 2. Try OpenAI
    if provider == "openai" and settings.OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 500
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    body = resp.json()
                    return body["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning(f"OpenAI natural response generation failed: {exc}")

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

    if provider == "gemini" and settings.GEMINI_API_KEY:
        result = call_gemini_sync(text, conversation_context)
    elif provider == "openai" and settings.OPENAI_API_KEY:
        result = call_openai_sync(text, conversation_context)

    # If LLM execution succeeded, return result
    if result is not None:
        return result

    # Otherwise fallback to high-accuracy rule-based heuristics
    return analyze_utterance_rule_based(text, conversation_context)
