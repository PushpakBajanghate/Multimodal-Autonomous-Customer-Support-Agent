"""
Heuristic and Rule-Based NLU Engine for Customer Support.
Handles English & Hinglish phrasing, entity extraction, confidence scoring, and ambiguity detection.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from app.agent.schemas import (
    IntentType, IntentResult, ExtractedEntities, AnalysisResult
)


EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
PHONE_REGEX = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
ORDER_ID_PATTERNS = [
    re.compile(r'(?:order\s*(?:id|#|no\.?|number)?\s*[:#-]?\s*)(\d+)', re.IGNORECASE),
    re.compile(r'#(\d+)\b'),
    re.compile(r'\border\s+(\d+)\b', re.IGNORECASE),
    re.compile(r'\b(\d{1,6})\s*(?:ka\s+order|number\s+order|cancel|track|refund|wapas)\b', re.IGNORECASE),
]

COMMON_PRODUCTS = sorted([
    "laptop", "smartphone", "phone", "headphones", "headphone", "earphones", "earbuds", "shoes", "shoe",
    "shirt", "t-shirt", "watch", "smartwatch", "bag", "backpack", "jacket", "dress",
    "monitor", "keyboard", "mouse", "camera", "tablet", "charger", "cable"
], key=len, reverse=True)

COMMON_DATE_WORDS = [
    "today", "yesterday", "tomorrow", "last week", "last monday", "last friday",
    "this morning", "aaj", "kal", "parso"
]


def extract_entities_rule_based(text: str) -> ExtractedEntities:
    """Extracts entities using regex and keyword rules with confidence scoring."""
    scores: Dict[str, float] = {}
    order_id: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    product_info: Optional[str] = None
    refund_reason: Optional[str] = None
    new_address: Optional[str] = None
    relevant_dates: List[str] = []

    # 1. Extract Order ID
    for pat in ORDER_ID_PATTERNS:
        match = pat.search(text)
        if match:
            try:
                order_id = int(match.group(1))
                scores["order_id"] = 0.98
                break
            except (ValueError, IndexError):
                pass

    # Fallback: if no order pattern matched, but there is an isolated 1-5 digit number in short query
    if order_id is None:
        standalone_num = re.search(r'\b(\d{1,5})\b', text)
        if standalone_num:
            # check if it's not part of an address or phone
            num_val = int(standalone_num.group(1))
            if num_val > 0 and len(standalone_num.group(1)) <= 5:
                order_id = num_val
                scores["order_id"] = 0.80

    # 2. Extract Email
    email_match = EMAIL_REGEX.search(text)
    if email_match:
        email = email_match.group(0)
        scores["email"] = 0.99

    # 3. Extract Phone
    phone_match = PHONE_REGEX.search(text)
    if phone_match and not email_match:
        phone = phone_match.group(0).strip()
        scores["phone"] = 0.95

    # 4. Extract Product Info
    lower_text = text.lower()
    for prod in COMMON_PRODUCTS:
        if re.search(r'\b' + re.escape(prod) + r'\b', lower_text):
            product_info = prod
            scores["product_info"] = 0.90
            break

    # 5. Extract Refund/Return Reason
    reason_patterns = [
        r'(?:because|due to|reason[:\s]+)(.*?)(?:$|\.|\n)',
        r'(?:broken|damaged|defective|faulty|not working|wrong size|wrong item|kharab|tuta hua)(.*?)(?:$|\.|\n)',
        r'(?:galat item|defective piece|quality poor)(.*?)(?:$|\.|\n)'
    ]
    for r_pat in reason_patterns:
        r_match = re.search(r_pat, text, re.IGNORECASE)
        if r_match:
            captured = r_match.group(0).strip()
            if len(captured) > 3:
                refund_reason = captured
                scores["refund_reason"] = 0.88
                break

    # 6. Extract New Address
    address_patterns = [
        r'(?:to|address to|shipping to|new address is|address badal kar)\s+([0-9A-Za-z\s,.-]{8,})',
        r'(?:address[:\s]+)([0-9A-Za-z\s,.-]{8,})'
    ]
    for a_pat in address_patterns:
        a_match = re.search(a_pat, text, re.IGNORECASE)
        if a_match:
            addr_candidate = a_match.group(1).strip()
            # Clean trailing punctuation
            addr_candidate = re.sub(r'[\.\?!]+$', '', addr_candidate)
            if len(addr_candidate) >= 8:
                new_address = addr_candidate
                scores["new_address"] = 0.92
                break

    # 7. Extract Dates
    date_regex = re.compile(r'\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b')
    date_matches = date_regex.findall(text)
    if date_matches:
        relevant_dates.extend(date_matches)
        scores["relevant_dates"] = 0.95
    else:
        for d_word in COMMON_DATE_WORDS:
            if d_word in lower_text:
                relevant_dates.append(d_word)
                scores["relevant_dates"] = 0.85

    return ExtractedEntities(
        order_id=order_id,
        email=email,
        phone=phone,
        product_info=product_info,
        refund_reason=refund_reason,
        new_address=new_address,
        relevant_dates=relevant_dates,
        confidence_scores=scores
    )


def classify_intent_rule_based(
    text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> Tuple[IntentType, float, str]:
    """Classifies intent using high-precision keyword patterns across English & Hinglish."""
    t = text.lower().strip()

    # Empty or pure greeting checks
    greetings = ["hi", "hello", "hey", "good morning", "good evening", "namaste", "hola", "sup"]
    if t in greetings or (len(t) < 15 and any(t.startswith(g) for g in greetings) and not any(w in t for w in ["order", "cancel", "track", "refund", "password", "ticket"])):
        return IntentType.UNKNOWN, 0.90, "Standard greeting without specific support intent."

    # 1. Order Cancellation (High Priority)
    cancellation_keywords = [
        "cancel my order", "cancel order", "cancel karna hai", "cancel kar do",
        "cancel kardo", "order cancel", "stop order", "cancellation", "order cancelation",
        "don't want the order", "nahi chahiye order", "cancel this", "order band karo"
    ]
    if any(kw in t for kw in cancellation_keywords):
        return IntentType.ORDER_CANCELLATION, 0.96, "Detected explicit order cancellation intent."

    # 2. Refund & Return Request
    refund_keywords = [
        "refund", "money back", "paise wapas", "return", "replace item", "wapas chahiye",
        "broken item", "damaged product", "defective", "damaged item", "faulty",
        "kharab aaya", "tuta hua", "wapas lena", "return karna"
    ]
    if any(kw in t for kw in refund_keywords):
        return IntentType.REFUND_REQUEST, 0.95, "Detected refund or return request intent."

    # 3. Address Update
    address_keywords = [
        "change address", "update address", "new address", "shipping address",
        "delivery address", "address badal", "address change", "pata badalna",
        "wrong address", "galat address"
    ]
    if any(kw in t for kw in address_keywords):
        return IntentType.ADDRESS_UPDATE, 0.96, "Detected shipping address change intent."

    # 4. Password Reset
    password_keywords = [
        "forgot password", "reset password", "password reset", "change password",
        "password bhul gaya", "login issue", "reset my pass", "cant login",
        "cannot log in", "account recovery", "reset link"
    ]
    if any(kw in t for kw in password_keywords):
        return IntentType.PASSWORD_RESET, 0.97, "Detected password reset or account recovery intent."

    # 5. Order Tracking
    tracking_keywords = [
        "track", "where is my order", "order status", "shipment", "delivery status",
        "kahan pahuncha", "kahan hai mera", "kab aayega", "parcel status",
        "eta", "when will it arrive", "tracking info", "status of order", "track order"
    ]
    if any(kw in t for kw in tracking_keywords) or (("order" in t or "parcel" in t) and ("where" in t or "status" in t or "kahan" in t or "kab" in t)):
        return IntentType.ORDER_TRACKING, 0.95, "Detected order tracking / status lookup intent."

    # 6. Ticket Creation / Human Escalation
    ticket_keywords = [
        "create ticket", "open ticket", "support ticket", "human agent", "talk to human",
        "customer care executive", "representative", "complaint", "shikayat",
        "escalate", "file a complaint", "agent se baat", "talk to agent"
    ]
    if any(kw in t for kw in ticket_keywords):
        return IntentType.TICKET_CREATION, 0.95, "Detected ticket creation or human agent escalation intent."

    # 7. Check if conversation context provides intent
    if conversation_context and len(conversation_context) > 0:
        last_msg = conversation_context[-1].get("text", "").lower()
        if "order id" in last_msg or "which order" in last_msg:
            # Customer might be answering with just an order number
            num_match = re.search(r'\b\d+\b', t)
            if num_match:
                return IntentType.ORDER_TRACKING, 0.85, "Contextual order ID response to tracking inquiry."

    # Default to UNKNOWN
    return IntentType.UNKNOWN, 0.70, "No recognized support intent keyword matched."


def analyze_utterance_rule_based(
    text: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None
) -> AnalysisResult:
    """Combines intent classification, entity extraction, and ambiguity analysis."""
    intent, confidence, reasoning = classify_intent_rule_based(text, conversation_context)
    entities = extract_entities_rule_based(text)

    # Check conversation context if order_id was previously identified
    if entities.order_id is None and conversation_context:
        for msg in reversed(conversation_context):
            ctx_entities = extract_entities_rule_based(msg.get("text", ""))
            if ctx_entities.order_id is not None:
                entities.order_id = ctx_entities.order_id
                entities.confidence_scores["order_id"] = 0.85
                break

    # Ambiguity detection
    is_ambiguous = False
    missing_entities: List[str] = []
    clarification_prompt: Optional[str] = None

    if intent in (IntentType.ORDER_TRACKING, IntentType.ORDER_CANCELLATION, IntentType.REFUND_REQUEST):
        if entities.order_id is None:
            is_ambiguous = True
            missing_entities.append("order_id")
            if intent == IntentType.ORDER_TRACKING:
                clarification_prompt = "Could you please provide your Order ID (e.g. Order #123) so I can track the delivery status for you?"
            elif intent == IntentType.ORDER_CANCELLATION:
                clarification_prompt = "Could you please specify the Order ID you would like to cancel?"
            elif intent == IntentType.REFUND_REQUEST:
                clarification_prompt = "Please share your Order ID and the reason for the return/refund so we can process your request."

    elif intent == IntentType.ADDRESS_UPDATE:
        if entities.order_id is None:
            is_ambiguous = True
            missing_entities.append("order_id")
        if entities.new_address is None:
            is_ambiguous = True
            missing_entities.append("new_address")

        if is_ambiguous:
            if "order_id" in missing_entities and "new_address" in missing_entities:
                clarification_prompt = "Please provide your Order ID along with the new shipping address you would like to update."
            elif "order_id" in missing_entities:
                clarification_prompt = "Which Order ID would you like to update the shipping address for?"
            else:
                clarification_prompt = "Please provide the complete new destination address for your order."

    elif intent == IntentType.PASSWORD_RESET:
        if entities.email is None:
            # If email is missing, ask for email
            is_ambiguous = True
            missing_entities.append("email")
            clarification_prompt = "Please provide the email address associated with your account so we can send the password reset link."

    return AnalysisResult(
        intent=intent,
        confidence=confidence,
        entities=entities,
        is_ambiguous=is_ambiguous,
        missing_entities=missing_entities,
        clarification_prompt=clarification_prompt,
        reasoning=reasoning
    )
