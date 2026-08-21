"""
Integration tests for the LangGraph Autonomous Agent State Machine (Phase 7).
Verifies state transitions, planning, real tool invocations, automatic retry on failure,
and human escalation without fabricating success confirmations.
"""

import pytest
from sqlalchemy.orm import Session
from app.models.models import Customer, Order, Ticket
from app.agent.graph import agent_graph, build_agent_graph, AgentState
from app.agent.schemas import IntentType


def test_order_tracking_full_graph_trajectory(db: Session):
    """
    Runs a complete ORDER_TRACKING request through the LangGraph agent state machine
    using real domain tools, asserting each node transition occurs in canonical order.
    """
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    customer = db.query(Customer).first()
    assert customer is not None

    order = Order(
        customer_id=customer.id,
        status="placed",
        order_date=now,
        expected_delivery=now + timedelta(days=2),
        total_amount=99.99,
        is_editable=True
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    initial_state: AgentState = {
        "customer_id": order.customer_id,
        "channel": "chat",
        "raw_input": f"Where is my order #{order.id}? Please track it.",
        "conversation_history": [],
        "trajectory": []
    }

    final_state = agent_graph.invoke(initial_state)

    # 1. Assert state populated correctly
    assert final_state["normalized_input"] == f"Where is my order #{order.id}? Please track it."
    assert final_state["intent"] == IntentType.ORDER_TRACKING
    assert final_state["entities"]["order_id"] == order.id
    assert final_state["is_ambiguous"] is False

    # 2. Assert explicit ordered action plan was generated
    assert len(final_state["plan"]) >= 3
    assert final_state["plan"][0]["step"] == 1
    assert "tracking" in final_state["plan"][1]["action"]

    # 3. Assert tool execution and validation
    assert final_state["selected_tool"] in ["track_order", "get_order_tracking_tool"]
    assert final_state["tool_results"]["status"] == "success"
    assert final_state["needs_escalation"] is False

    # 4. Assert final synthesized response
    assert str(order.id) in final_state["final_response"]
    assert any(term in final_state["final_response"].lower() for term in ["carrier", "status", "delivery", "fedex", "ups", "tracking", "progress", "transit", "estimated", "order"])

    # 5. Assert Exact Ordered State Trajectory
    expected_trajectory = [
        "normalize_input",
        "load_memory",
        "classify_intent_entities",
        "check_ambiguity",
        "plan_actions",
        "select_tool",
        "execute_tool",
        "validate_result",
        "generate_response",
        "log_interaction"
    ]
    assert final_state["trajectory"] == expected_trajectory


def test_refund_request_full_graph_flow(db: Session):
    """
    Runs a complete REFUND_REQUEST through the full graph for a delivered order.
    """
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    customer = db.query(Customer).first()
    assert customer is not None

    delivered_order = Order(
        customer_id=customer.id,
        status="delivered",
        order_date=now - timedelta(days=4),
        expected_delivery=now - timedelta(days=1),
        total_amount=115.50,
        is_editable=False
    )
    db.add(delivered_order)
    db.commit()
    db.refresh(delivered_order)

    initial_state: AgentState = {
        "customer_id": delivered_order.customer_id,
        "channel": "chat",
        "raw_input": f"I want a refund for order #{delivered_order.id}, the item was broken.",
        "conversation_history": [],
        "trajectory": []
    }

    final_state = agent_graph.invoke(initial_state)

    assert final_state["intent"] == IntentType.REFUND_REQUEST
    assert final_state["entities"]["order_id"] == delivered_order.id
    assert final_state["selected_tool"] in ["create_refund", "process_refund_tool"]
    assert final_state["tool_results"]["status"] == "success"
    assert final_state["needs_escalation"] is False
    assert "refund" in final_state["final_response"].lower()
    assert str(delivered_order.id) in final_state["final_response"]



def test_order_cancellation_full_graph_flow(db: Session):
    """
    Runs a complete ORDER_CANCELLATION through the full graph for a placed order.
    """
    # Create a fresh placed order for test
    customer = db.query(Customer).first()
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    fresh_order = Order(
        customer_id=customer.id,
        status="placed",
        order_date=now,
        expected_delivery=now + timedelta(days=3),
        total_amount=75.00,
        is_editable=True
    )
    db.add(fresh_order)
    db.commit()
    db.refresh(fresh_order)

    initial_state: AgentState = {
        "customer_id": customer.id,
        "channel": "chat",
        "raw_input": f"Please cancel my order #{fresh_order.id}",
        "conversation_history": [],
        "trajectory": []
    }

    final_state = agent_graph.invoke(initial_state)

    assert final_state["intent"] == IntentType.ORDER_CANCELLATION
    assert final_state["entities"]["order_id"] == fresh_order.id
    assert any(word in final_state["final_response"].lower() for word in ["cancel", "cancellation", "canceled", "cancelled"])
    assert str(fresh_order.id) in final_state["final_response"]


def test_ambiguous_inquiry_branches_to_clarification():
    """
    Tests that an incomplete request (e.g. missing order_id) correctly branches
    to clarification_question instead of executing tools.
    """
    initial_state: AgentState = {
        "customer_id": 1,
        "channel": "chat",
        "raw_input": "mera order cancel karna hai",  # Ambiguous: no order_id
        "conversation_history": [],
        "trajectory": []
    }

    final_state = agent_graph.invoke(initial_state)

    assert final_state["intent"] == IntentType.ORDER_CANCELLATION
    assert final_state["is_ambiguous"] is True
    assert "order_id" in final_state["missing_entities"]
    assert "execute_tool" not in final_state["trajectory"]

    expected_trajectory = [
        "normalize_input",
        "load_memory",
        "classify_intent_entities",
        "check_ambiguity",
        "clarification_question",
        "log_interaction"
    ]
    assert final_state["trajectory"] == expected_trajectory


def test_deliberate_tool_failure_retries_and_escalates():
    """
    Deliberate tool failure test:
    Asserts that if a tool call fails, the graph executes 1 retry,
    and upon second failure routes to human escalation rather than claiming success.
    """
    # Non-existent order #999999 will fail when track_order is invoked
    initial_state: AgentState = {
        "customer_id": 1,
        "channel": "chat",
        "raw_input": "Please track order #999999 immediately",
        "conversation_history": [],
        "trajectory": []
    }

    final_state = agent_graph.invoke(initial_state)

    # 1. Assert tool failed
    assert final_state["tool_results"]["status"] == "error"

    # 2. Assert retry occurred (retry_count == 1)
    assert final_state.get("retry_count") == 1
    assert "retry_tool" in final_state["trajectory"]

    # 3. Assert graph escalated
    assert final_state["needs_escalation"] is True
    assert "escalate" in final_state["trajectory"]

    # 4. Assert agent NEVER fabricated success
    assert "delivered" not in final_state["final_response"].lower()
    assert "on schedule" not in final_state["final_response"].lower()
    assert "escalating" in final_state["final_response"].lower()

    # 5. Assert Exact Trajectory with retry loop
    expected_trajectory = [
        "normalize_input",
        "load_memory",
        "classify_intent_entities",
        "check_ambiguity",
        "plan_actions",
        "select_tool",
        "execute_tool",
        "validate_result",
        "retry_tool",
        "execute_tool",
        "validate_result",
        "escalate",
        "log_interaction"
    ]
    assert final_state["trajectory"] == expected_trajectory
