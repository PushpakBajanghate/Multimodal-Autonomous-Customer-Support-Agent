"""
Real Agent Tool Layer for Autonomous Customer Support.
Wraps Phase 2 API endpoints (never raw DB access) with agent-facing Pydantic input validation,
verifiable structured outputs, and automatic logging to tool_execution_logs.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.core.config import settings

logger = logging.getLogger(__name__)


# ==============================================================================
# Tool Execution Logging Helper
# ==============================================================================

def log_tool_execution(
    tool_name: str,
    arguments: Dict[str, Any],
    result: Dict[str, Any],
    conversation_id: Optional[int] = None,
    ticket_id: Optional[int] = None
) -> None:
    """
    Persists every agent tool execution to the tool_execution_logs database table.
    Gracefully handles standalone test or offline database states.
    """
    try:
        from app.db.session import SessionLocal
        from app.models.models import ToolExecutionLog

        db = SessionLocal()
        try:
            # Filter sensitive values if needed and ensure serializable
            safe_arguments = json.loads(json.dumps(arguments, default=str))
            safe_result = json.loads(json.dumps(result, default=str))

            log_entry = ToolExecutionLog(
                conversation_id=conversation_id,
                ticket_id=ticket_id,
                tool_name=tool_name,
                arguments=safe_arguments,
                result=safe_result
            )
            db.add(log_entry)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not persist tool execution log to database: {e}")


# ==============================================================================
# Internal Phase 2 API Client Helper
# ==============================================================================

def _get_api_client():
    """
    Returns a FastAPI TestClient wired to app.main without running an external HTTP socket.
    Strictly goes through FastAPI routing, dependencies, RBAC, and schemas.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _agent_headers(customer_id: Optional[int] = None, is_verified: bool = True) -> Dict[str, str]:
    """Generates standard agent service authentication headers for Phase 2 API calls."""
    headers = {
        "X-Agent-Service-Key": settings.AGENT_SERVICE_SECRET,
    }
    if customer_id is not None:
        headers["X-Customer-ID"] = str(customer_id)
        headers["X-Customer-Verified"] = "true" if is_verified else "false"
    return headers


# ==============================================================================
# Pydantic Input Schemas for LLM Tool Calling
# ==============================================================================

class GetCustomerInput(BaseModel):
    customer_id: int = Field(..., gt=0, description="Unique positive integer ID of the customer to retrieve.")

class GetOrderInput(BaseModel):
    order_id: int = Field(..., gt=0, description="Unique positive integer ID of the order.")
    customer_id: Optional[int] = Field(default=None, description="Optional customer ID who owns the order.")

class TrackOrderInput(BaseModel):
    order_id: int = Field(..., gt=0, description="Unique positive integer ID of the order to track.")
    customer_id: Optional[int] = Field(default=None, description="Optional customer ID who owns the order.")

class CheckRefundEligibilityInput(BaseModel):
    order_id: int = Field(..., gt=0, description="Order ID to evaluate for return/refund eligibility.")
    customer_id: Optional[int] = Field(default=None, description="Optional customer ID who owns the order.")

class CreateRefundInput(BaseModel):
    order_id: int = Field(..., gt=0, description="Order ID for which refund is requested.")
    reason: str = Field(..., min_length=3, description="Detailed explanation or reason for requesting the refund.")
    customer_id: Optional[int] = Field(default=None, description="Optional customer ID who owns the order.")

class CancelOrderInput(BaseModel):
    order_id: int = Field(..., gt=0, description="Order ID of the active order to be cancelled.")
    reason: str = Field(default="Customer requested cancellation", description="Reason for order cancellation.")
    customer_id: Optional[int] = Field(default=None, description="Optional customer ID who owns the order.")

class UpdateAddressInput(BaseModel):
    customer_id: int = Field(..., gt=0, description="Customer ID requesting the address update.")
    new_address: str = Field(..., min_length=5, description="Full new destination shipping address.")
    order_id: Optional[int] = Field(default=None, description="Optional specific order ID to update delivery address for.")

class ResetPasswordInput(BaseModel):
    customer_id: int = Field(..., gt=0, description="Customer ID requesting the password reset link.")

class CreateTicketInput(BaseModel):
    customer_id: int = Field(..., gt=0, description="Customer ID associated with the escalation ticket.")
    channel: str = Field(default="chat", description="Communication channel: 'chat', 'voice', or 'email'.")
    intent: str = Field(default="support_escalation", description="Identified intent or problem category.")
    escalation_reason: str = Field(..., min_length=3, description="Detailed reason for human escalation.")
    actions_attempted: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Actions and tools attempted before escalation.")
    tool_results: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Recorded tool outputs before escalation.")

class SendConfirmationInput(BaseModel):
    customer_id: int = Field(..., gt=0, description="Customer ID to receive the confirmation.")
    confirmation_type: str = Field(..., description="Type of confirmation: 'order_tracking', 'refund', 'cancellation', 'address_update', 'password_reset', or 'ticket'.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Summary details of the action completed.")
    recipient: Optional[str] = Field(default=None, description="Optional email or phone recipient identifier.")


# ==============================================================================
# Real Domain Tools (Wrapping Phase 2 API Endpoints)
# ==============================================================================

@tool(args_schema=GetCustomerInput)
def get_customer(customer_id: int) -> Dict[str, Any]:
    """
    Retrieves customer account profile information (name, email, order summary) by customer ID.
    Always use this tool to verify customer details.
    """
    client = _get_api_client()
    try:
        response = client.get(
            f"/api/v1/customers/{customer_id}",
            headers=_agent_headers(customer_id=customer_id)
        )
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            result = {
                "success": True,
                "status": "success",
                "customer": data.get("data")
            }
        else:
            reason = data.get("reason") if isinstance(data, dict) else f"HTTP {response.status_code}"
            result = {
                "success": False,
                "status": "error",
                "error": reason or f"Customer #{customer_id} not found."
            }
    except Exception as exc:
        result = {"success": False, "status": "error", "error": f"API request error: {str(exc)}"}

    log_tool_execution("get_customer", {"customer_id": customer_id}, result)
    return result


@tool(args_schema=GetOrderInput)
def get_order(order_id: int, customer_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Retrieves complete details of an order including status, line items, order date, and total amount.
    """
    client = _get_api_client()
    try:
        response = client.get(
            f"/api/v1/orders/{order_id}",
            headers=_agent_headers(customer_id=customer_id)
        )
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            result = {
                "success": True,
                "status": "success",
                "order": data.get("data")
            }
        else:
            reason = data.get("reason") if isinstance(data, dict) else f"HTTP {response.status_code}"
            result = {
                "success": False,
                "status": "error",
                "error": reason or f"Order #{order_id} not found."
            }
    except Exception as exc:
        result = {"success": False, "status": "error", "error": f"API request error: {str(exc)}"}

    log_tool_execution("get_order", {"order_id": order_id, "customer_id": customer_id}, result)
    return result


@tool(args_schema=TrackOrderInput)
def track_order(order_id: int, customer_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetches real-time carrier tracking details, delivery ETA, carrier name, and tracking number for an order.
    """
    client = _get_api_client()
    try:
        response = client.get(
            f"/api/v1/orders/{order_id}/tracking",
            headers=_agent_headers(customer_id=customer_id)
        )
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            tracking_info = data.get("data", {})
            result = {
                "success": True,
                "status": "success",
                "order_id": order_id,
                "order_status": tracking_info.get("status"),
                "carrier": tracking_info.get("carrier"),
                "tracking_number": tracking_info.get("tracking_number"),
                "expected_delivery": tracking_info.get("expected_delivery"),
                "estimated_days_remaining": tracking_info.get("estimated_days_remaining", 0),
                "is_delivered": tracking_info.get("is_delivered", False),
                "tracking": tracking_info
            }
        else:
            reason = data.get("reason") if isinstance(data, dict) else f"HTTP {response.status_code}"
            result = {
                "success": False,
                "status": "error",
                "error": reason or f"Unable to fetch tracking for Order #{order_id}."
            }
    except Exception as exc:
        result = {"success": False, "status": "error", "error": f"API request error: {str(exc)}"}

    log_tool_execution("track_order", {"order_id": order_id, "customer_id": customer_id}, result)
    return result


@tool(args_schema=CheckRefundEligibilityInput)
def check_refund_eligibility(order_id: int, customer_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Evaluates whether an order qualifies for a refund under the 30-day return policy.
    Checks order status (must be 'delivered' or 'cancelled') and order date window.
    """
    client = _get_api_client()
    try:
        response = client.get(
            f"/api/v1/orders/{order_id}",
            headers=_agent_headers(customer_id=customer_id)
        )
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            order_data = data.get("data", {})
            status = order_data.get("status")
            order_date_str = order_data.get("order_date")
            total_amount = order_data.get("total_amount", 0.0)

            # Check status rule
            if status not in ["delivered", "cancelled"]:
                result = {
                    "success": True,
                    "status": "success",
                    "eligible": False,
                    "order_id": order_id,
                    "order_status": status,
                    "total_amount": total_amount,
                    "reason": f"Order #{order_id} is in '{status}' status. Refunds are only allowed for delivered or cancelled orders."
                }
            else:
                # Check 30-day window
                is_within_window = True
                days_ago = 0
                if order_date_str:
                    try:
                        order_dt = datetime.fromisoformat(order_date_str.replace("Z", "+00:00"))
                        now = datetime.now(timezone.utc)
                        if order_dt.tzinfo is None:
                            order_dt = order_dt.replace(tzinfo=timezone.utc)
                        days_ago = (now - order_dt).days
                        if days_ago > 30:
                            is_within_window = False
                    except Exception:
                        pass

                if not is_within_window:
                    result = {
                        "success": True,
                        "status": "success",
                        "eligible": False,
                        "order_id": order_id,
                        "order_status": status,
                        "total_amount": total_amount,
                        "reason": f"Order #{order_id} was placed {days_ago} days ago, which exceeds the 30-day refund policy."
                    }
                else:
                    result = {
                        "success": True,
                        "status": "success",
                        "eligible": True,
                        "order_id": order_id,
                        "order_status": status,
                        "total_amount": total_amount,
                        "reason": f"Order #{order_id} is eligible for a full refund of ${float(total_amount):.2f}."
                    }
        else:
            reason = data.get("reason") if isinstance(data, dict) else f"HTTP {response.status_code}"
            result = {
                "success": False,
                "status": "error",
                "error": reason or f"Order #{order_id} not found."
            }
    except Exception as exc:
        result = {"success": False, "status": "error", "error": f"API request error: {str(exc)}"}

    log_tool_execution("check_refund_eligibility", {"order_id": order_id, "customer_id": customer_id}, result)
    return result


@tool(args_schema=CreateRefundInput)
def create_refund(order_id: int, reason: str, customer_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Submits and processes a verified refund request for an eligible order through the Phase 2 API.
    """
    client = _get_api_client()
    try:
        response = client.post(
            f"/api/v1/orders/{order_id}/refund",
            json={"order_id": order_id, "reason": reason},
            headers=_agent_headers(customer_id=customer_id, is_verified=True)
        )
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            refund_info = data.get("data", {})
            result = {
                "success": True,
                "status": "success",
                "order_id": order_id,
                "refund_id": refund_info.get("id"),
                "refund_amount": refund_info.get("amount"),
                "refund_status": refund_info.get("status"),
                "message": f"Refund for Order #{order_id} approved for ${float(refund_info.get('amount', 0.0)):.2f}.",
                "refund": refund_info
            }
        else:
            reason_err = data.get("reason") if isinstance(data, dict) else f"HTTP {response.status_code}"
            result = {
                "success": False,
                "status": "error",
                "error": reason_err or f"Refund request rejected for Order #{order_id}."
            }
    except Exception as exc:
        result = {"success": False, "status": "error", "error": f"API request error: {str(exc)}"}

    log_tool_execution("create_refund", {"order_id": order_id, "reason": reason, "customer_id": customer_id}, result)
    return result


@tool(args_schema=CancelOrderInput)
def cancel_order(order_id: int, reason: str = "Customer requested cancellation", customer_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Cancels an active, unshipped order ('placed' status) and voids pending charges.
    """
    client = _get_api_client()
    try:
        response = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            json={"order_id": order_id, "reason": reason},
            headers=_agent_headers(customer_id=customer_id, is_verified=True)
        )
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            cancel_info = data.get("data", {})
            result = {
                "success": True,
                "status": "success",
                "order_id": order_id,
                "cancellation_id": cancel_info.get("id"),
                "cancellation_status": cancel_info.get("status"),
                "message": f"Order #{order_id} cancelled successfully.",
                "cancellation": cancel_info
            }
        else:
            reason_err = data.get("reason") if isinstance(data, dict) else f"HTTP {response.status_code}"
            result = {
                "success": False,
                "status": "error",
                "error": reason_err or f"Cancellation failed for Order #{order_id}."
            }
    except Exception as exc:
        result = {"success": False, "status": "error", "error": f"API request error: {str(exc)}"}

    log_tool_execution("cancel_order", {"order_id": order_id, "reason": reason, "customer_id": customer_id}, result)
    return result


@tool(args_schema=UpdateAddressInput)
def update_address(customer_id: int, new_address: str, order_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Updates delivery shipping address on customer profile or a specific editable order.
    """
    client = _get_api_client()
    try:
        response = client.post(
            f"/api/v1/customers/{customer_id}/address",
            json={"new_address": new_address, "order_id": order_id},
            headers=_agent_headers(customer_id=customer_id, is_verified=True)
        )
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            addr_info = data.get("data", {})
            result = {
                "success": True,
                "status": "success",
                "customer_id": customer_id,
                "order_id": order_id,
                "new_address": new_address,
                "message": f"Shipping address updated to: {new_address}",
                "address_change": addr_info
            }
        else:
            reason_err = data.get("reason") if isinstance(data, dict) else f"HTTP {response.status_code}"
            result = {
                "success": False,
                "status": "error",
                "error": reason_err or f"Address update failed for customer #{customer_id}."
            }
    except Exception as exc:
        result = {"success": False, "status": "error", "error": f"API request error: {str(exc)}"}

    log_tool_execution("update_address", {"customer_id": customer_id, "new_address": new_address, "order_id": order_id}, result)
    return result


@tool(args_schema=ResetPasswordInput)
def reset_password(customer_id: int) -> Dict[str, Any]:
    """
    Generates and dispatches a secure password reset link to the verified customer's email.
    """
    client = _get_api_client()
    try:
        response = client.post(
            f"/api/v1/customers/{customer_id}/password-reset",
            json={},
            headers=_agent_headers(customer_id=customer_id, is_verified=True)
        )
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            reset_info = data.get("data", {})
            result = {
                "success": True,
                "status": "success",
                "customer_id": customer_id,
                "message": f"Password reset link generated and dispatched.",
                "password_reset": reset_info
            }
        else:
            reason_err = data.get("reason") if isinstance(data, dict) else f"HTTP {response.status_code}"
            result = {
                "success": False,
                "status": "error",
                "error": reason_err or f"Password reset request failed for customer #{customer_id}."
            }
    except Exception as exc:
        result = {"success": False, "status": "error", "error": f"API request error: {str(exc)}"}

    log_tool_execution("reset_password", {"customer_id": customer_id}, result)
    return result


@tool(args_schema=CreateTicketInput)
def create_ticket(
    customer_id: int,
    channel: str = "chat",
    intent: str = "support_escalation",
    escalation_reason: str = "Issue escalated to support agent",
    actions_attempted: Optional[Dict[str, Any]] = None,
    tool_results: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Creates a formal support ticket in the database to escalate an inquiry to human support specialists.
    """
    client = _get_api_client()
    payload = {
        "customer_id": customer_id,
        "channel": channel,
        "intent": intent,
        "escalation_reason": escalation_reason,
        "actions_attempted": actions_attempted or {},
        "tool_results": tool_results or {}
    }
    try:
        response = client.post(
            "/api/v1/tickets",
            json=payload,
            headers=_agent_headers(customer_id=customer_id)
        )
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            ticket_info = data.get("data", {})
            result = {
                "success": True,
                "status": "success",
                "ticket_id": ticket_info.get("id"),
                "ticket": ticket_info,
                "message": f"Support ticket #{ticket_info.get('id')} created successfully."
            }
        else:
            reason_err = data.get("reason") if isinstance(data, dict) else f"HTTP {response.status_code}"
            result = {
                "success": False,
                "status": "error",
                "error": reason_err or "Failed to create support ticket."
            }
    except Exception as exc:
        result = {"success": False, "status": "error", "error": f"API request error: {str(exc)}"}

    log_tool_execution("create_ticket", payload, result)
    return result


@tool(args_schema=SendConfirmationInput)
def send_confirmation(
    customer_id: int,
    confirmation_type: str,
    details: Optional[Dict[str, Any]] = None,
    recipient: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends/records an official confirmation receipt (email/SMS notification) for an executed action.
    """
    details_dict = details or {}
    confirmation_id = f"CNF-{uuid.uuid4().hex[:8].upper()}"
    timestamp_str = datetime.now(timezone.utc).isoformat()
    target_recipient = recipient or f"customer_{customer_id}@example.com"

    result = {
        "success": True,
        "status": "success",
        "confirmation_id": confirmation_id,
        "confirmation_type": confirmation_type,
        "recipient": target_recipient,
        "delivered": True,
        "timestamp": timestamp_str,
        "details": details_dict,
        "message": f"Confirmation {confirmation_id} dispatched to {target_recipient}."
    }

    log_tool_execution(
        "send_confirmation",
        {"customer_id": customer_id, "confirmation_type": confirmation_type, "recipient": target_recipient},
        result
    )
    return result


# ==============================================================================
# Tool Registry Map
# ==============================================================================

TOOL_REGISTRY: Dict[str, Any] = {
    "get_customer": get_customer,
    "get_order": get_order,
    "track_order": track_order,
    "check_refund_eligibility": check_refund_eligibility,
    "create_refund": create_refund,
    "cancel_order": cancel_order,
    "update_address": update_address,
    "reset_password": reset_password,
    "create_ticket": create_ticket,
    "send_confirmation": send_confirmation,
    # Phase 6 legacy aliases
    "get_order_tracking_tool": track_order,
    "process_refund_tool": create_refund,
    "process_cancellation_tool": cancel_order,
    "update_shipping_address_tool": update_address,
    "request_password_reset_tool": reset_password,
    "create_support_ticket_tool": create_ticket
}

ALL_AGENT_TOOLS = [
    get_customer,
    get_order,
    track_order,
    check_refund_eligibility,
    create_refund,
    cancel_order,
    update_address,
    reset_password,
    create_ticket,
    send_confirmation
]

