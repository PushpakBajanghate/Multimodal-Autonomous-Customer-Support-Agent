"""
Unit tests for Intent Recognition, Entity Extraction, and Ambiguity Detection.
Evaluates accuracy across English and Hinglish customer utterances.
"""

import pytest
from typing import List, Dict, Any

from app.agent import (
    classify_intent,
    extract_entities,
    analyze_utterance,
    IntentType,
    AnalysisResult
)


# Test dataset of 15 realistic customer utterances
TEST_UTTERANCES = [
    # 1. ORDER_TRACKING (English)
    {
        "text": "Where is my order #1042? When will it arrive?",
        "expected_intent": IntentType.ORDER_TRACKING,
        "expected_order_id": 1042,
        "is_ambiguous": False
    },
    # 2. ORDER_TRACKING (Hinglish)
    {
        "text": "Mera parcel kahan pahuncha hai order 9 ka delivery status batao",
        "expected_intent": IntentType.ORDER_TRACKING,
        "expected_order_id": 9,
        "is_ambiguous": False
    },
    # 3. REFUND_REQUEST (English)
    {
        "text": "I received broken headphones for order #88, please refund my money.",
        "expected_intent": IntentType.REFUND_REQUEST,
        "expected_order_id": 88,
        "expected_product": "headphones",
        "is_ambiguous": False
    },
    # 4. REFUND_REQUEST (Hinglish)
    {
        "text": "Order 15 ke paise wapas chahiye product kharab aaya tha",
        "expected_intent": IntentType.REFUND_REQUEST,
        "expected_order_id": 15,
        "is_ambiguous": False
    },
    # 5. ORDER_CANCELLATION (English)
    {
        "text": "Please cancel my order #34 immediately.",
        "expected_intent": IntentType.ORDER_CANCELLATION,
        "expected_order_id": 34,
        "is_ambiguous": False
    },
    # 6. ORDER_CANCELLATION (Hinglish - Ambiguous without Order ID)
    {
        "text": "mera order cancel karna hai",
        "expected_intent": IntentType.ORDER_CANCELLATION,
        "expected_order_id": None,
        "is_ambiguous": True,
        "expected_missing": ["order_id"]
    },
    # 7. ORDER_CANCELLATION (Hinglish - with Order ID)
    {
        "text": "Order 55 cancel kardo nahi chahiye ab",
        "expected_intent": IntentType.ORDER_CANCELLATION,
        "expected_order_id": 55,
        "is_ambiguous": False
    },
    # 8. ADDRESS_UPDATE (English)
    {
        "text": "Please change shipping address for order #19 to 742 Evergreen Terrace, Springfield",
        "expected_intent": IntentType.ADDRESS_UPDATE,
        "expected_order_id": 19,
        "is_ambiguous": False
    },
    # 9. ADDRESS_UPDATE (Ambiguous - missing both address and order ID)
    {
        "text": "Address change karna hai delivery address update kar do",
        "expected_intent": IntentType.ADDRESS_UPDATE,
        "expected_order_id": None,
        "is_ambiguous": True
    },
    # 10. PASSWORD_RESET (English)
    {
        "text": "I forgot my password, please send reset link to alex@example.com",
        "expected_intent": IntentType.PASSWORD_RESET,
        "expected_email": "alex@example.com",
        "is_ambiguous": False
    },
    # 11. PASSWORD_RESET (Hinglish)
    {
        "text": "Password bhul gaya reset link bhejo rahul@test.com",
        "expected_intent": IntentType.PASSWORD_RESET,
        "expected_email": "rahul@test.com",
        "is_ambiguous": False
    },
    # 12. TICKET_CREATION (English)
    {
        "text": "I have an issue with billing and need to talk to a human agent, open a ticket please",
        "expected_intent": IntentType.TICKET_CREATION,
        "is_ambiguous": False
    },
    # 13. TICKET_CREATION (Hinglish)
    {
        "text": "Mujhe support agent se baat karni hai complaint register karo",
        "expected_intent": IntentType.TICKET_CREATION,
        "is_ambiguous": False
    },
    # 14. UNKNOWN / Greeting (English)
    {
        "text": "Hello, how are you today?",
        "expected_intent": IntentType.UNKNOWN,
        "is_ambiguous": False
    },
    # 15. ORDER_TRACKING (Ambiguous without Order ID)
    {
        "text": "Where is my parcel? Can you track it?",
        "expected_intent": IntentType.ORDER_TRACKING,
        "expected_order_id": None,
        "is_ambiguous": True,
        "expected_missing": ["order_id"]
    }
]


def test_intent_classification_and_accuracy():
    """Evaluates intent classification accuracy across all 15 benchmark utterances."""
    correct_intents = 0
    total = len(TEST_UTTERANCES)
    results = []

    for item in TEST_UTTERANCES:
        text = item["text"]
        expected = item["expected_intent"]
        res = classify_intent(text)

        is_match = (res.intent == expected)
        if is_match:
            correct_intents += 1

        results.append({
            "text": text,
            "expected": expected.value,
            "predicted": res.intent.value,
            "confidence": res.confidence,
            "matched": is_match
        })

    accuracy = (correct_intents / total) * 100.0
    print(f"\n==========================================")
    print(f"INTENT CLASSIFICATION ACCURACY: {correct_intents}/{total} ({accuracy:.2f}%)")
    print(f"==========================================")

    for r in results:
        status_icon = "[PASS]" if r["matched"] else "[FAIL]"
        print(f"{status_icon} [{r['predicted']} (conf: {r['confidence']:.2f})] Expected: {r['expected']} | '{r['text']}'")

    assert accuracy >= 90.0, f"Accuracy {accuracy:.2f}% below required 90% threshold"
    assert correct_intents == total, f"Expected 100% accuracy on canonical benchmark set"


def test_entity_extraction_accuracy():
    """Tests extraction of order_id, email, product_info, and ambiguity detection."""
    for item in TEST_UTTERANCES:
        text = item["text"]
        analysis: AnalysisResult = analyze_utterance(text)

        # Check intent
        assert analysis.intent == item["expected_intent"], f"Intent mismatch for '{text}'"

        # Check order_id if specified
        if "expected_order_id" in item:
            assert analysis.entities.order_id == item["expected_order_id"], (
                f"Order ID mismatch for '{text}': got {analysis.entities.order_id}, expected {item['expected_order_id']}"
            )
            if item["expected_order_id"] is not None:
                assert "order_id" in analysis.entities.confidence_scores
                assert analysis.entities.confidence_scores["order_id"] > 0.70

        # Check email if specified
        if "expected_email" in item:
            assert analysis.entities.email == item["expected_email"], f"Email mismatch for '{text}'"
            assert "email" in analysis.entities.confidence_scores
            assert analysis.entities.confidence_scores["email"] > 0.90

        # Check product if specified
        if "expected_product" in item:
            assert analysis.entities.product_info == item["expected_product"], f"Product mismatch for '{text}'"

        # Check ambiguity flag
        if "is_ambiguous" in item:
            assert analysis.is_ambiguous == item["is_ambiguous"], (
                f"Ambiguity flag mismatch for '{text}': got {analysis.is_ambiguous}, expected {item['is_ambiguous']}"
            )
            if item["is_ambiguous"]:
                assert analysis.clarification_prompt is not None


def test_hinglish_cancellation_ambiguity():
    """Specific test for Hinglish 'mera order cancel karna hai' requirement."""
    res = analyze_utterance("mera order cancel karna hai")
    assert res.intent == IntentType.ORDER_CANCELLATION
    assert res.entities.order_id is None
    assert res.is_ambiguous is True
    assert "order_id" in res.missing_entities
    assert res.clarification_prompt is not None


def test_product_cancellation_request_is_not_a_generic_query():
    res = analyze_utterance("I want to cancel my Nike shoes order")
    assert res.intent == IntentType.ORDER_CANCELLATION
    assert res.entities.product_info == "shoes"
    assert res.entities.new_address is None
    assert res.is_ambiguous is True
    assert "order_id" in res.missing_entities


def test_contextual_conversation_entity_resolution():
    """Tests extracting order_id across multi-turn conversation context."""
    context = [
        {"sender": "user", "text": "Can you check my order?"},
        {"sender": "agent", "text": "Sure, which order ID?"},
        {"sender": "user", "text": "It is order #402"}
    ]
    # Follow-up utterance
    res = analyze_utterance("cancel this order please", conversation_context=context)
    assert res.intent == IntentType.ORDER_CANCELLATION
    assert res.entities.order_id == 402
    assert res.is_ambiguous is False
