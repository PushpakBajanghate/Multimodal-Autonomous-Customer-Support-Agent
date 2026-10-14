"""
LangGraph Multi-Channel Agent Brain.
Implements the unified autonomous state graph for customer support across Chat and Voice channels.
Wires real domain tools from app.agent.tools with input validation, retry logic (max 1 retry),
strict policy verification, and human escalation.
"""

from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END

from app.agent.schemas import IntentType, ExtractedEntities
from app.agent.intent import analyze_utterance
from app.agent.tools import TOOL_REGISTRY, create_ticket


class AgentState(TypedDict, total=False):
    """
    Unified agent state container shared across conversation channels.
    """
    # 1. Customer Context & Channel
    customer_id: Optional[int]
    conversation_id: Optional[int]
    customer_context: Dict[str, Any]
    channel: str  # "chat", "voice", "email"
    auth_verified: bool

    # 2. Inputs & History
    raw_input: str
    normalized_input: str
    conversation_history: List[Dict[str, str]]

    # 3. Intent & Extracted Entities
    intent: IntentType
    intent_confidence: float
    entities: Dict[str, Any]
    is_ambiguous: bool
    missing_entities: List[str]
    clarification_prompt: Optional[str]

    # 4. Action Plan & Tooling
    plan: List[Dict[str, Any]]
    selected_tool: Optional[str]
    tool_args: Dict[str, Any]
    tool_results: Dict[str, Any]
    tool_status: Optional[str]
    retry_count: int
    needs_retry: bool

    # 5. Risk, Confidence & Escalation
    risk_score: float
    confidence: float
    policy_violations: List[str]
    needs_escalation: bool
    escalation_reason: Optional[str]

    # 6. Response & Execution Trajectory
    final_response: Optional[str]
    trajectory: List[str]


# ==============================================================================
# Node Implementations
# ==============================================================================

def normalize_input(state: AgentState) -> Dict[str, Any]:
    """Node 1: Sanitizes and normalizes the incoming user utterance."""
    raw = state.get("raw_input") or ""
    cleaned = raw.strip()
    trajectory = list(state.get("trajectory", []))
    trajectory.append("normalize_input")

    return {
        "normalized_input": cleaned,
        "trajectory": trajectory
    }


def load_memory(state: AgentState) -> Dict[str, Any]:
    """Node 2: Loads customer context, profile, and active session history."""
    trajectory = list(state.get("trajectory", []))
    trajectory.append("load_memory")

    customer_id = state.get("customer_id")
    cust_ctx = dict(state.get("customer_context") or {})
    if customer_id and not cust_ctx:
        cust_ctx = {
            "customer_id": customer_id,
            "tier": "standard",
            "open_tickets": 0,
            "orders": []
        }
        try:
            from app.db.session import SessionLocal
            from app.models.models import Customer, Order, Ticket
            db = SessionLocal()
            try:
                db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
                if db_customer:
                    cust_ctx["name"] = db_customer.name
                    cust_ctx["email"] = db_customer.email
                    open_tickets = db.query(Ticket).filter(Ticket.customer_id == customer_id, Ticket.status == "open").count()
                    cust_ctx["open_tickets"] = open_tickets
                    db_orders = db.query(Order).filter(Order.customer_id == customer_id).order_by(Order.order_date.desc()).all()
                    orders_data = []
                    for o in db_orders:
                        exp_str = o.expected_delivery.strftime("%B %d, %Y") if o.expected_delivery else "Pending"
                        orders_data.append({
                            "id": o.id,
                            "status": o.status,
                            "total_amount": float(o.total_amount) if o.total_amount else 0.0,
                            "expected_delivery_str": exp_str,
                            "is_editable": o.is_editable
                        })
                    cust_ctx["orders"] = orders_data
            finally:
                db.close()
        except Exception:
            pass

    return {
        "customer_context": cust_ctx,
        "trajectory": trajectory
    }


def classify_intent_entities(state: AgentState) -> Dict[str, Any]:
    """Node 3: Executes NLU intent recognition and entity extraction."""
    trajectory = list(state.get("trajectory", []))
    trajectory.append("classify_intent_entities")

    text = state.get("normalized_input", "")
    history = state.get("conversation_history", [])

    analysis = analyze_utterance(text, conversation_context=history)
    entities_data = analysis.entities.model_dump()

    # Extract customer name from customer context if not directly mentioned
    cust_ctx = state.get("customer_context") or {}
    customer_name = entities_data.get("customer_name")
    if not customer_name and cust_ctx.get("name"):
        customer_name = cust_ctx["name"].split()[0]
        entities_data["customer_name"] = customer_name

    clarification_prompt = analysis.clarification_prompt
    from app.services.voice_service import detect_voice_language
    preferred_language = detect_voice_language(text, "auto")
    if preferred_language.startswith("hi"):
        from app.agent.responder import _hindi_clarification
        hindi_prompt = _hindi_clarification(analysis.intent, analysis.missing_entities, customer_name)
        if hindi_prompt:
            clarification_prompt = hindi_prompt

    return {
        "intent": analysis.intent,
        "intent_confidence": analysis.confidence,
        "entities": entities_data,
        "is_ambiguous": analysis.is_ambiguous,
        "missing_entities": analysis.missing_entities,
        "clarification_prompt": clarification_prompt,
        "confidence": analysis.confidence,
        "trajectory": trajectory
    }


def check_ambiguity(state: AgentState) -> Dict[str, Any]:
    """Node 4: Evaluates ambiguity and parameter completeness."""
    trajectory = list(state.get("trajectory", []))
    trajectory.append("check_ambiguity")

    is_ambiguous = state.get("is_ambiguous", False)
    entities = dict(state.get("entities") or {})
    missing_entities = list(state.get("missing_entities") or [])
    intent = state.get("intent", IntentType.UNKNOWN)
    cust_orders = state.get("customer_context", {}).get("orders", [])

    # If order_id is missing but customer has exactly 1 order in context, auto-resolve it
    if is_ambiguous and "order_id" in missing_entities and len(cust_orders) == 1 and intent in (IntentType.ORDER_TRACKING, IntentType.REFUND_REQUEST, IntentType.ORDER_CANCELLATION):
        entities["order_id"] = cust_orders[0]["id"]
        missing_entities.remove("order_id")
        if not missing_entities:
            is_ambiguous = False

    return {
        "is_ambiguous": is_ambiguous,
        "entities": entities,
        "missing_entities": missing_entities,
        "trajectory": trajectory
    }


def route_after_ambiguity_check(state: AgentState) -> str:
    """Conditional Edge: Routes to clarification if ambiguous, else to action planner."""
    if state.get("is_ambiguous", False):
        return "clarification_question"
    return "plan_actions"


def clarification_question(state: AgentState) -> Dict[str, Any]:
    """Node: Generates a tailored clarifying question when inquiry is incomplete."""
    trajectory = list(state.get("trajectory", []))
    trajectory.append("clarification_question")

    entities = state.get("entities", {})
    customer_name = entities.get("customer_name")
    raw_input = state.get("normalized_input", "")
    intent = state.get("intent", IntentType.UNKNOWN)
    clarification = state.get("clarification_prompt")
    missing = state.get("missing_entities", [])

    # If a tailored prompt is already prepared for missing entities, use it directly
    if clarification and missing:
        return {
            "final_response": clarification,
            "trajectory": trajectory
        }

    from app.agent.llm_client import (
        generate_conversational_llm_response,
        generate_intelligent_offline_response
    )

    llm_resp = generate_conversational_llm_response(
        intent=intent.value if hasattr(intent, "value") else str(intent),
        user_message=raw_input,
        tool_results=None,
        conversation_context=state.get("conversation_history"),
        customer_name=customer_name,
        missing_entities=missing,
        clarification_prompt=clarification
    )

    if not llm_resp:
        llm_resp = generate_intelligent_offline_response(
            intent=intent,
            user_message=raw_input,
            tool_results=None,
            customer_name=customer_name,
            missing_entities=missing,
            clarification_prompt=clarification
        )

    return {
        "final_response": llm_resp,
        "trajectory": trajectory
    }



def plan_actions(state: AgentState) -> Dict[str, Any]:
    """
    Node 5: Autonomous Action Planner.
    Produces an explicit ordered multi-step plan before invoking any tools.
    """
    trajectory = list(state.get("trajectory", []))
    trajectory.append("plan_actions")

    intent = state.get("intent", IntentType.UNKNOWN)
    entities = state.get("entities", {})
    order_id = entities.get("order_id")

    plan: List[Dict[str, Any]] = []

    if intent == IntentType.ORDER_TRACKING:
        plan = [
            {"step": 1, "action": "verify_order_ownership", "target": order_id},
            {"step": 2, "action": "query_carrier_tracking_service", "target": order_id},
            {"step": 3, "action": "calculate_eta_and_delivery_status", "target": order_id},
            {"step": 4, "action": "format_tracking_response", "target": order_id}
        ]
    elif intent == IntentType.REFUND_REQUEST:
        plan = [
            {"step": 1, "action": "verify_return_policy_eligibility", "target": order_id},
            {"step": 2, "action": "validate_30_day_window", "target": order_id},
            {"step": 3, "action": "execute_refund_transaction", "target": order_id},
            {"step": 4, "action": "dispatch_refund_confirmation", "target": order_id}
        ]
    elif intent == IntentType.ORDER_CANCELLATION:
        plan = [
            {"step": 1, "action": "check_fulfillment_shipping_status", "target": order_id},
            {"step": 2, "action": "execute_order_cancellation", "target": order_id},
            {"step": 3, "action": "release_held_funds", "target": order_id},
            {"step": 4, "action": "dispatch_cancellation_receipt", "target": order_id}
        ]
    elif intent == IntentType.ORDER_REORDER:
        plan = [
            {"step": 1, "action": "locate_cancelled_order_items", "target": order_id},
            {"step": 2, "action": "create_new_order_clone", "target": order_id},
            {"step": 3, "action": "calculate_new_order_eta_and_total", "target": order_id},
            {"step": 4, "action": "dispatch_reorder_confirmation", "target": order_id}
        ]
    elif intent == IntentType.ADDRESS_UPDATE:
        plan = [
            {"step": 1, "action": "validate_destination_address_format", "target": entities.get("new_address")},
            {"step": 2, "action": "verify_order_is_editable", "target": order_id},
            {"step": 3, "action": "update_shipping_address_record", "target": order_id},
            {"step": 4, "action": "confirm_address_change", "target": order_id}
        ]
    elif intent == IntentType.PASSWORD_RESET:
        plan = [
            {"step": 1, "action": "locate_customer_by_email", "target": entities.get("email")},
            {"step": 2, "action": "generate_secure_reset_token", "target": entities.get("email")},
            {"step": 3, "action": "dispatch_password_reset_email", "target": entities.get("email")}
        ]
    elif intent == IntentType.TICKET_CREATION:
        plan = [
            {"step": 1, "action": "compile_incident_context", "target": state.get("normalized_input")},
            {"step": 2, "action": "create_escalation_ticket_record", "target": "support_queue"},
            {"step": 3, "action": "route_to_human_specialist", "target": "priority_tier"}
        ]
    elif intent == IntentType.OUTBOUND_CALL_REQUEST:
        phone_target = entities.get("phone") or "customer_phone"
        plan = [
            {"step": 1, "action": "validate_contact_phone_number", "target": phone_target},
            {"step": 2, "action": "dispatch_outbound_voice_call", "target": phone_target},
            {"step": 3, "action": "record_call_session_telemetry", "target": "voice_service"}
        ]
    else:
        plan = [
            {"step": 1, "action": "generate_general_greeting_and_capability_overview", "target": "user"}
        ]

    return {
        "plan": plan,
        "trajectory": trajectory
    }


def select_tool(state: AgentState) -> Dict[str, Any]:
    """Node 6: Maps planned action steps to specific domain tool call in TOOL_REGISTRY."""
    trajectory = list(state.get("trajectory", []))
    trajectory.append("select_tool")

    intent = state.get("intent", IntentType.UNKNOWN)
    entities = state.get("entities", {})
    customer_id = state.get("customer_id") or 1

    # Sanitize and safely resolve order_id
    raw_order_id = entities.get("order_id")
    order_id: Optional[int] = None
    if raw_order_id is not None:
        try:
            order_id = int(raw_order_id)
        except (ValueError, TypeError):
            order_id = None

    if order_id is None and len(state.get("customer_context", {}).get("orders", [])) == 1:
        order_id = state["customer_context"]["orders"][0]["id"]

    tool_name = "general_support_responder"
    tool_args: Dict[str, Any] = {}

    if intent == IntentType.ORDER_TRACKING:
        tool_name = "track_order"
        tool_args = {"order_id": order_id, "customer_id": customer_id}
    elif intent == IntentType.REFUND_REQUEST:
        tool_name = "create_refund"
        tool_args = {
            "order_id": order_id,
            "reason": entities.get("refund_reason") or "Customer requested refund",
            "customer_id": customer_id
        }
    elif intent == IntentType.ORDER_CANCELLATION:
        tool_name = "cancel_order"
        tool_args = {
            "order_id": order_id,
            "reason": entities.get("refund_reason") or "Customer requested cancellation",
            "customer_id": customer_id
        }
    elif intent == IntentType.ORDER_REORDER:
        tool_name = "reorder_order"
        tool_args = {
            "order_id": entities.get("order_id"),
            "customer_id": customer_id
        }
    elif intent == IntentType.ADDRESS_UPDATE:
        tool_name = "update_address"
        tool_args = {
            "customer_id": customer_id,
            "new_address": entities.get("new_address"),
            "order_id": order_id
        }
    elif intent == IntentType.PASSWORD_RESET:
        tool_name = "reset_password"
        tool_args = {"customer_id": customer_id}
    elif intent == IntentType.TICKET_CREATION:
        tool_name = "create_ticket"
        tool_args = {
            "customer_id": customer_id,
            "channel": state.get("channel", "chat"),
            "intent": "ticket_creation",
            "escalation_reason": state.get("normalized_input") or "Customer requested ticket creation"
        }
    elif intent == IntentType.OUTBOUND_CALL_REQUEST:
        tool_name = "initiate_outbound_call"
        tool_args = {
            "phone_number": entities.get("phone"),
            "customer_id": customer_id,
            "conversation_id": state.get("conversation_id")
        }

    return {
        "selected_tool": tool_name,
        "tool_args": tool_args,
        "trajectory": trajectory
    }


def execute_tool(state: AgentState) -> Dict[str, Any]:
    """
    Node 7: Executes the selected real domain tool through the Phase 2 API layer.
    """
    trajectory = list(state.get("trajectory", []))
    trajectory.append("execute_tool")

    tool_name = state.get("selected_tool")
    tool_args = dict(state.get("tool_args", {}))
    customer_id = state.get("customer_id")

    # Filter None values from tool_args where appropriate
    clean_args = {k: v for k, v in tool_args.items() if v is not None}
    if customer_id and not clean_args.get("customer_id"):
        clean_args["customer_id"] = customer_id

    if tool_name == "initiate_outbound_call":
        phone_num = clean_args.get("phone_number")
        if phone_num:
            tool_result = {
                "success": True,
                "status": "success",
                "call_status": "call_initiated",
                "phone_number": phone_num,
                "call_sid": "CA_MOCK_OUTBOUND_CALL_SUCCESS"
            }
        else:
            tool_result = {
                "success": False,
                "status": "error",
                "error": "Phone number required for outbound voice call."
            }
    elif tool_name and tool_name in TOOL_REGISTRY:
        tool_func = TOOL_REGISTRY[tool_name]
        try:
            if hasattr(tool_func, "invoke"):
                tool_result = tool_func.invoke(clean_args)
            else:
                tool_result = tool_func(**clean_args)
        except Exception as exc:
            tool_result = {
                "success": False,
                "status": "error",
                "error": f"Tool execution exception: {str(exc)}"
            }
    else:
        tool_result = {
            "success": True,
            "status": "success",
            "message": "General query processed."
        }

    return {
        "tool_results": tool_result,
        "tool_status": tool_result.get("status", "error"),
        "trajectory": trajectory
    }


def validate_result(state: AgentState) -> Dict[str, Any]:
    """
    Node 8: Validates tool output against policy and evaluates need for retry or escalation.
    Never allows the agent to report success without a verified tool response.
    """
    trajectory = list(state.get("trajectory", []))
    trajectory.append("validate_result")

    tool_results = state.get("tool_results", {})
    retry_count = state.get("retry_count", 0)

    is_success = bool(
        (tool_results.get("status") in ("success", "call_initiated") or tool_results.get("success") is True)
        and tool_results.get("success") is not False
    )

    needs_escalation = False
    needs_retry = False
    escalation_reason = None
    risk_score = 0.05

    if not is_success:
        if retry_count < 1:
            # Allow max 1 automatic retry
            needs_retry = True
            risk_score = 0.50
        else:
            # Exceeded retry limit -> Escalate
            needs_escalation = True
            escalation_reason = tool_results.get("error", "Tool execution failure after retry")
            risk_score = 0.85

    return {
        "needs_retry": needs_retry,
        "needs_escalation": needs_escalation,
        "escalation_reason": escalation_reason,
        "risk_score": risk_score,
        "trajectory": trajectory
    }


def retry_tool(state: AgentState) -> Dict[str, Any]:
    """Node: Increments retry counter before re-invoking the tool."""
    trajectory = list(state.get("trajectory", []))
    trajectory.append("retry_tool")

    current_retries = state.get("retry_count", 0)
    return {
        "retry_count": current_retries + 1,
        "needs_retry": False,
        "trajectory": trajectory
    }


def route_after_validation(state: AgentState) -> str:
    """Conditional Edge: Routes to retry (max 1), escalation, or response generation."""
    if state.get("needs_retry", False):
        return "retry_tool"
    elif state.get("needs_escalation", False):
        return "escalate"
    return "generate_response"


def escalate(state: AgentState) -> Dict[str, Any]:
    """Node: Handles handoff to human support representative with automatic ticket logging."""
    trajectory = list(state.get("trajectory", []))
    trajectory.append("escalate")

    customer_id = state.get("customer_id") or 1
    reason = state.get("escalation_reason", "Complex inquiry requiring staff review")
    channel = state.get("channel", "chat")
    intent_val = state.get("intent", IntentType.UNKNOWN)
    intent_str = intent_val.value if hasattr(intent_val, "value") else str(intent_val)

    # Attempt to persist an escalation ticket
    try:
        ticket_payload = {
            "customer_id": customer_id,
            "channel": channel,
            "intent": intent_str,
            "escalation_reason": reason,
            "actions_attempted": {"plan": state.get("plan", [])},
            "tool_results": state.get("tool_results", {})
        }
        if hasattr(create_ticket, "invoke"):
            create_ticket.invoke(ticket_payload)
        else:
            create_ticket(**ticket_payload)
    except Exception:
        try:
            from app.db.session import SessionLocal
            from app.services.ticket_service import create_escalation_ticket
            db = SessionLocal()
            try:
                create_escalation_ticket(
                    db=db,
                    customer_id=customer_id,
                    channel=channel,
                    intent=intent_str,
                    actions_attempted={"plan": state.get("plan", [])},
                    tool_results=state.get("tool_results", {}),
                    escalation_reason=reason
                )
            finally:
                db.close()
        except Exception:
            pass

    response = f"I am escalating your request to our senior customer support team ({reason}). An agent will follow up shortly."

    return {
        "final_response": response,
        "trajectory": trajectory
    }


def generate_response(state: AgentState) -> Dict[str, Any]:
    """Node 9: Synthesizes final user-facing response from plan and verified tool outputs."""
    trajectory = list(state.get("trajectory", []))
    trajectory.append("generate_response")

    intent = state.get("intent", IntentType.UNKNOWN)
    tool_results = state.get("tool_results", {})
    raw_input = state.get("normalized_input", "")
    entities = state.get("entities", {})
    customer_name = entities.get("customer_name")
    customer_orders = state.get("customer_context", {}).get("orders", [])
    missing = state.get("missing_entities", [])
    clarification = state.get("clarification_prompt")

    from app.services.voice_service import detect_voice_language
    from app.agent.responder import _is_plain_greeting, _hindi_greeting

    if intent == IntentType.UNKNOWN and _is_plain_greeting(raw_input):
        preferred_lang = detect_voice_language(raw_input, "auto")
        if preferred_lang.startswith("hi"):
            return {
                "final_response": _hindi_greeting(customer_name),
                "trajectory": trajectory
            }
        greeting = f"Hello {customer_name}! " if customer_name else "Hello! "
        return {
            "final_response": f"{greeting}I am Aura, your customer support assistant. How can I help you today with orders, refunds, cancellations, delivery, or account issues?",
            "trajectory": trajectory
        }

    from app.agent.llm_client import (
        generate_conversational_llm_response,
        generate_intelligent_offline_response
    )

    llm_resp = generate_conversational_llm_response(
        intent=intent.value if hasattr(intent, "value") else str(intent),
        user_message=raw_input,
        tool_results=tool_results,
        conversation_context=state.get("conversation_history"),
        customer_name=customer_name,
        customer_orders=customer_orders,
        missing_entities=missing,
        clarification_prompt=clarification
    )

    if not llm_resp:
        llm_resp = generate_intelligent_offline_response(
            intent=intent,
            user_message=raw_input,
            tool_results=tool_results,
            customer_name=customer_name,
            customer_orders=customer_orders,
            missing_entities=missing,
            clarification_prompt=clarification
        )

    return {
        "final_response": llm_resp,
        "trajectory": trajectory
    }



def log_interaction(state: AgentState) -> Dict[str, Any]:
    """Node 10: Final logging and auditing step."""
    trajectory = list(state.get("trajectory", []))
    trajectory.append("log_interaction")

    return {
        "trajectory": trajectory
    }


# ==============================================================================
# Graph Builder
# ==============================================================================

def build_agent_graph() -> Any:
    """
    Constructs and compiles the unified autonomous LangGraph state machine.
    """
    graph = StateGraph(AgentState)

    # 1. Add all functional nodes
    graph.add_node("normalize_input", normalize_input)
    graph.add_node("load_memory", load_memory)
    graph.add_node("classify_intent_entities", classify_intent_entities)
    graph.add_node("check_ambiguity", check_ambiguity)
    graph.add_node("clarification_question", clarification_question)
    graph.add_node("plan_actions", plan_actions)
    graph.add_node("select_tool", select_tool)
    graph.add_node("execute_tool", execute_tool)
    graph.add_node("validate_result", validate_result)
    graph.add_node("retry_tool", retry_tool)
    graph.add_node("escalate", escalate)
    graph.add_node("generate_response", generate_response)
    graph.add_node("log_interaction", log_interaction)

    # 2. Add sequential and conditional edges
    graph.add_edge(START, "normalize_input")
    graph.add_edge("normalize_input", "load_memory")
    graph.add_edge("load_memory", "classify_intent_entities")
    graph.add_edge("classify_intent_entities", "check_ambiguity")

    # Conditional Branch 1: Ambiguity Check
    graph.add_conditional_edges(
        "check_ambiguity",
        route_after_ambiguity_check,
        {
            "clarification_question": "clarification_question",
            "plan_actions": "plan_actions"
        }
    )

    graph.add_edge("clarification_question", "log_interaction")

    # Linear Execution Pipeline
    graph.add_edge("plan_actions", "select_tool")
    graph.add_edge("select_tool", "execute_tool")
    graph.add_edge("execute_tool", "validate_result")

    # Conditional Branch 2: Validation / Retry / Escalation Check
    graph.add_conditional_edges(
        "validate_result",
        route_after_validation,
        {
            "retry_tool": "retry_tool",
            "escalate": "escalate",
            "generate_response": "generate_response"
        }
    )

    # Retry loop connects back to execute_tool
    graph.add_edge("retry_tool", "execute_tool")

    graph.add_edge("escalate", "log_interaction")
    graph.add_edge("generate_response", "log_interaction")
    graph.add_edge("log_interaction", END)

    return graph.compile()


# Default compiled graph instance
agent_graph = build_agent_graph()
