"""
Unit & Integration Tests for Agent Domain Tools (Phase 7 Real Tool Layer).
Verifies input validation, Phase 2 API wrapping, LangChain tool schemas,
execution logging in tool_execution_logs, and structured outputs.
"""

import pytest
from sqlalchemy.orm import Session
from app.models.models import Customer, Order, ToolExecutionLog, Ticket
from app.agent.tools import (
    get_customer,
    get_order,
    track_order,
    check_refund_eligibility,
    create_refund,
    cancel_order,
    update_address,
    reset_password,
    create_ticket,
    send_confirmation,
    TOOL_REGISTRY,
    ALL_AGENT_TOOLS
)


def test_tool_registry_contains_all_tools():
    """Verifies all required 10 domain tools are registered and LangChain compatible."""
    expected_tools = [
        "get_customer", "get_order", "track_order", "check_refund_eligibility",
        "create_refund", "cancel_order", "update_address", "reset_password",
        "create_ticket", "send_confirmation"
    ]
    for tool_name in expected_tools:
        assert tool_name in TOOL_REGISTRY, f"Missing tool {tool_name} in TOOL_REGISTRY"
        tool_obj = TOOL_REGISTRY[tool_name]
        assert hasattr(tool_obj, "args_schema") or hasattr(tool_obj, "invoke"), (
            f"Tool {tool_name} is not LangChain tool compliant"
        )


def test_get_customer_tool_success_and_not_found(db: Session):
    customer = db.query(Customer).first()
    assert customer is not None

    # Happy path
    res = get_customer.invoke({"customer_id": customer.id})
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["customer"]["id"] == customer.id
    assert res["customer"]["email"] == customer.email

    # Not found
    res_err = get_customer.invoke({"customer_id": 99999})
    assert res_err["success"] is False
    assert res_err["status"] == "error"
    assert "not found" in res_err["error"].lower()


def test_get_order_tool(db: Session):
    order = db.query(Order).first()
    assert order is not None

    # Happy path
    res = get_order.invoke({"order_id": order.id, "customer_id": order.customer_id})
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["order"]["id"] == order.id

    # Not found
    res_err = get_order.invoke({"order_id": 99999, "customer_id": 1})
    assert res_err["success"] is False
    assert res_err["status"] == "error"


def test_track_order_tool(db: Session):
    order = db.query(Order).first()
    assert order is not None

    res = track_order.invoke({"order_id": order.id, "customer_id": order.customer_id})
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["order_id"] == order.id
    assert "carrier" in res
    assert "tracking_number" in res
    assert res["tracking_number"].startswith("TRK-")


def test_check_refund_eligibility_tool(db: Session):
    # Order 2 is delivered and recent -> eligible
    order_delivered = db.query(Order).filter(Order.status == "delivered").first()
    assert order_delivered is not None

    res = check_refund_eligibility.invoke({"order_id": order_delivered.id})
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["eligible"] is True
    assert res["order_id"] == order_delivered.id

    # Order 1 is placed -> ineligible for refund
    order_placed = db.query(Order).filter(Order.status == "placed").first()
    assert order_placed is not None

    res_ineligible = check_refund_eligibility.invoke({"order_id": order_placed.id})
    assert res_ineligible["success"] is True
    assert res_ineligible["eligible"] is False
    assert "status" in res_ineligible["reason"].lower()


def test_create_refund_tool(db: Session):
    order_delivered = db.query(Order).filter(Order.status == "delivered").first()
    assert order_delivered is not None

    res = create_refund.invoke({
        "order_id": order_delivered.id,
        "reason": "Item defective upon unboxing",
        "customer_id": order_delivered.customer_id
    })
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["refund_amount"] > 0
    assert "approved" in res["message"].lower()

    # Second refund on same order should be rejected by business rules
    res_dup = create_refund.invoke({
        "order_id": order_delivered.id,
        "reason": "Duplicate refund attempt",
        "customer_id": order_delivered.customer_id
    })
    assert res_dup["success"] is False
    assert res_dup["status"] == "error"


def test_cancel_order_tool(db: Session):
    order_placed = db.query(Order).filter(Order.status == "placed").first()
    assert order_placed is not None

    res = cancel_order.invoke({
        "order_id": order_placed.id,
        "reason": "Ordered by mistake",
        "customer_id": order_placed.customer_id
    })
    assert res["success"] is True
    assert res["status"] == "success"
    assert "cancelled successfully" in res["message"].lower()

    # Cancel shipped order should fail
    order_shipped = db.query(Order).filter(Order.status == "shipped").first()
    assert order_shipped is not None

    res_shipped = cancel_order.invoke({
        "order_id": order_shipped.id,
        "reason": "Want to cancel shipped item",
        "customer_id": order_shipped.customer_id
    })
    assert res_shipped["success"] is False
    assert res_shipped["status"] == "error"
    assert "shipped" in res_shipped["error"].lower()


def test_update_address_tool(db: Session):
    customer = db.query(Customer).first()
    assert customer is not None

    res = update_address.invoke({
        "customer_id": customer.id,
        "new_address": "742 Evergreen Terrace, Springfield, OR 97477"
    })
    assert res["success"] is True
    assert res["status"] == "success"
    assert "742 Evergreen" in res["new_address"]


def test_reset_password_tool(db: Session):
    customer = db.query(Customer).first()
    assert customer is not None

    res = reset_password.invoke({"customer_id": customer.id})
    assert res["success"] is True
    assert res["status"] == "success"
    assert "password_reset" in res


def test_create_ticket_tool(db: Session):
    customer = db.query(Customer).first()
    assert customer is not None

    res = create_ticket.invoke({
        "customer_id": customer.id,
        "channel": "chat",
        "intent": "damaged_goods",
        "escalation_reason": "Customer reported shattered package",
        "actions_attempted": {"step": "track_order"},
        "tool_results": {"carrier": "FedEx"}
    })
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["ticket_id"] is not None
    assert res["ticket"]["status"] == "open"


def test_send_confirmation_tool():
    res = send_confirmation.invoke({
        "customer_id": 1,
        "confirmation_type": "refund",
        "details": {"amount": 89.99, "order_id": 2},
        "recipient": "alice.smith@example.com"
    })
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["delivered"] is True
    assert res["confirmation_id"].startswith("CNF-")


def test_tool_executions_logged_to_database(db: Session):
    """Verifies that every tool call logs a record to tool_execution_logs table."""
    customer = db.query(Customer).first()
    initial_count = db.query(ToolExecutionLog).count()

    get_customer.invoke({"customer_id": customer.id})
    track_order.invoke({"order_id": 1, "customer_id": customer.id})

    final_count = db.query(ToolExecutionLog).count()
    assert final_count >= initial_count + 2

    last_log = db.query(ToolExecutionLog).order_by(ToolExecutionLog.id.desc()).first()
    assert last_log is not None
    assert last_log.tool_name in ["track_order", "get_customer"]
    assert "arguments" in last_log.__dict__ or hasattr(last_log, "arguments")
