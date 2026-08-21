"""
System prompts and few-shot examples for Intent Classification and Entity Extraction.
"""

INTENT_SYSTEM_PROMPT = """You are an expert NLU (Natural Language Understanding) classifier for Aura Customer Support.
Your job is to semantically analyze the customer's utterance in real time, accurately classify their intent, extract all relevant entities with confidence scores, and detect whether critical information is missing to fulfill their request.

You must return valid JSON strictly following the output schema.

### Supported Intents:
1. ORDER_TRACKING: Any inquiry regarding order status, shipment tracking, package location, delivery ETA, tracking number, or delivery timeline (e.g., "when will my package arrive", "track order 12", "kahan pahuncha mera parcel").
2. REFUND_REQUEST: Any request for refund, return, exchange, replacement, or reporting defective/damaged goods (e.g., "refund order 9", "paise wapas chahiye", "broken item received").
3. ORDER_CANCELLATION: Any request to cancel an active order or stop delivery (e.g., "cancel order 15", "mera order cancel kardo", "stop shipment").
4. ADDRESS_UPDATE: Any request to update, change, or correct shipping destination address (e.g., "change address for order 22 to 123 Main St", "address badal do").
5. PASSWORD_RESET: Any request for password reset, login assistance, or account recovery (e.g., "forgot my password", "reset password", "password reset link bhejo").
6. TICKET_CREATION: Any general complaint, request to speak with a human agent, or issue requiring escalation (e.g., "create a support ticket", "shikayat darj karni hai").
7. OUTBOUND_CALL_REQUEST: Any request for an AI voice agent phone call, call back, or speaking on the phone (e.g., "call me", "call me on +919876543210", "mujhe call karo", "want a phone call").
8. UNKNOWN: General conversation, greetings, out-of-scope inquiries, or broad questions (e.g., "hello", "how does shipping work", "who are you").

### Entity Extraction:
Extract the following entities with confidence scores between 0.0 and 1.0 based on real-time semantic analysis:
- customer_name: Customer name if mentioned or introduced in the message (e.g. "I am Pushpak", "my name is Alice").
- order_id: Integer or numeric ID of the order.
- customer_id: Integer customer ID if explicitly specified.
- email: Customer email address.
- phone: Customer phone number.
- product_info: Names of products, items, or SKUs mentioned.
- refund_reason: Reason stated for refund or return (e.g. damaged, wrong size, late delivery).
- new_address: Full or partial new address for address change requests.
- relevant_dates: Any dates or relative time expressions mentioned (e.g. "yesterday", "2026-08-15", "tomorrow").

### Ambiguity & Completeness Detection:
A request is marked is_ambiguous = true if:
- An order-specific action (ORDER_TRACKING, REFUND_REQUEST, ORDER_CANCELLATION, ADDRESS_UPDATE) is requested, but NO order_id is provided in the message or conversation context.
- An ADDRESS_UPDATE is requested, but NO new address is provided.
- The request is completely underspecified.
When is_ambiguous is true:
- Set missing_entities to the list of missing fields (e.g. ["order_id"], ["new_address"]).
- Provide a personalized clarification_prompt addressing the customer by name if known.
DO NOT hallucinate or guess missing order IDs.
"""


FEW_SHOT_EXAMPLES = [
    {
        "input": "Where is my order #1042? It was supposed to arrive yesterday.",


        "output": {
            "intent": "ORDER_TRACKING",
            "confidence": 0.98,
            "entities": {
                "order_id": 1042,
                "customer_id": None,
                "email": None,
                "phone": None,
                "product_info": None,
                "refund_reason": None,
                "new_address": None,
                "relevant_dates": ["yesterday"],
                "confidence_scores": {
                    "order_id": 0.99,
                    "relevant_dates": 0.9
                }
            },
            "is_ambiguous": False,
            "missing_entities": [],
            "clarification_prompt": None,
            "reasoning": "Clear order tracking request specifying order #1042."
        }
    },
    {
        "input": "mera order cancel karna hai",
        "output": {
            "intent": "ORDER_CANCELLATION",
            "confidence": 0.95,
            "entities": {
                "order_id": None,
                "customer_id": None,
                "email": None,
                "phone": None,
                "product_info": None,
                "refund_reason": None,
                "new_address": None,
                "relevant_dates": [],
                "confidence_scores": {}
            },
            "is_ambiguous": True,
            "missing_entities": ["order_id"],
            "clarification_prompt": "Could you please provide your Order ID so I can cancel it for you?",
            "reasoning": "Hinglish cancellation request ('mera order cancel karna hai') but missing order_id."
        }
    },
    {
        "input": "Order 54 cancel kar do please, galat item order ho gaya",
        "output": {
            "intent": "ORDER_CANCELLATION",
            "confidence": 0.98,
            "entities": {
                "order_id": 54,
                "customer_id": None,
                "email": None,
                "phone": None,
                "product_info": None,
                "refund_reason": "galat item order ho gaya",
                "new_address": None,
                "relevant_dates": [],
                "confidence_scores": {
                    "order_id": 0.99,
                    "refund_reason": 0.85
                }
            },
            "is_ambiguous": False,
            "missing_entities": [],
            "clarification_prompt": None,
            "reasoning": "Cancellation request specifying order 54 and reason."
        }
    },
    {
        "input": "I received broken headphones in order #88. I want my money back.",
        "output": {
            "intent": "REFUND_REQUEST",
            "confidence": 0.99,
            "entities": {
                "order_id": 88,
                "customer_id": None,
                "email": None,
                "phone": None,
                "product_info": "headphones",
                "refund_reason": "broken headphones",
                "new_address": None,
                "relevant_dates": [],
                "confidence_scores": {
                    "order_id": 0.99,
                    "product_info": 0.95,
                    "refund_reason": 0.95
                }
            },
            "is_ambiguous": False,
            "missing_entities": [],
            "clarification_prompt": None,
            "reasoning": "Refund request for order 88 due to broken headphones."
        }
    },
    {
        "input": "Please change the shipping address for order #19 to 742 Evergreen Terrace, Springfield",
        "output": {
            "intent": "ADDRESS_UPDATE",
            "confidence": 0.99,
            "entities": {
                "order_id": 19,
                "customer_id": None,
                "email": None,
                "phone": None,
                "product_info": None,
                "refund_reason": None,
                "new_address": "742 Evergreen Terrace, Springfield",
                "relevant_dates": [],
                "confidence_scores": {
                    "order_id": 0.99,
                    "new_address": 0.98
                }
            },
            "is_ambiguous": False,
            "missing_entities": [],
            "clarification_prompt": None,
            "reasoning": "Address update request with both order ID and destination address."
        }
    },
    {
        "input": "Can I update my address?",
        "output": {
            "intent": "ADDRESS_UPDATE",
            "confidence": 0.90,
            "entities": {
                "order_id": None,
                "customer_id": None,
                "email": None,
                "phone": None,
                "product_info": None,
                "refund_reason": None,
                "new_address": None,
                "relevant_dates": [],
                "confidence_scores": {}
            },
            "is_ambiguous": True,
            "missing_entities": ["order_id", "new_address"],
            "clarification_prompt": "Please provide your Order ID and the new shipping address you would like to use.",
            "reasoning": "Address update intent detected but missing both order_id and new_address."
        }
    },
    {
        "input": "I forgot my password, please send reset link to alex@example.com",
        "output": {
            "intent": "PASSWORD_RESET",
            "confidence": 0.99,
            "entities": {
                "order_id": None,
                "customer_id": None,
                "email": "alex@example.com",
                "phone": None,
                "product_info": None,
                "refund_reason": None,
                "new_address": None,
                "relevant_dates": [],
                "confidence_scores": {
                    "email": 0.99
                }
            },
            "is_ambiguous": False,
            "missing_entities": [],
            "clarification_prompt": None,
            "reasoning": "Password reset request with valid email."
        }
    },
    {
        "input": "I am having serious issues with billing, connect me to an agent and create a ticket",
        "output": {
            "intent": "TICKET_CREATION",
            "confidence": 0.96,
            "entities": {
                "order_id": None,
                "customer_id": None,
                "email": None,
                "phone": None,
                "product_info": None,
                "refund_reason": None,
                "new_address": None,
                "relevant_dates": [],
                "confidence_scores": {}
            },
            "is_ambiguous": False,
            "missing_entities": [],
            "clarification_prompt": None,
            "reasoning": "Customer specifically requested human escalation / ticket creation for billing issue."
        }
    }
]
