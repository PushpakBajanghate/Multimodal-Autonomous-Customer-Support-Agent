import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models import Customer, Order
from app.core.security import (
    create_customer_session_token, create_staff_token
)
from app.core.config import settings

client = TestClient(app, raise_server_exceptions=False)

def get_error_payload(response):
    body = response.json()
    if "detail" in body and isinstance(body["detail"], dict):
        return body["detail"]
    return body

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# -------------------------------------------------------------
# 1. Customer Session & Lightweight Auth Tests
# -------------------------------------------------------------
def test_create_unverified_customer_session(db: Session):
    customer = db.query(Customer).first()
    assert customer is not None

    response = client.post(
        "/api/v1/auth/customer-session",
        json={"email": customer.email}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["customer_id"] == customer.id
    assert data["data"]["is_verified"] is False
    assert "access_token" in data["data"]

def test_create_verified_customer_session_with_order(db: Session):
    customer = db.query(Customer).first()
    order = db.query(Order).filter(Order.customer_id == customer.id).first()
    assert order is not None

    response = client.post(
        "/api/v1/auth/customer-session",
        json={"email": customer.email, "order_id": order.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["customer_id"] == customer.id
    assert data["data"]["is_verified"] is True

def test_verify_existing_customer_session(db: Session):
    customer = db.query(Customer).first()
    order = db.query(Order).filter(Order.customer_id == customer.id).first()

    # Get unverified token
    unverified_token = create_customer_session_token(customer.id, is_verified=False, email=customer.email)
    headers = {"Authorization": f"Bearer {unverified_token}"}

    # Verify session using order_id
    response = client.post(
        "/api/v1/auth/customer-session/verify",
        headers=headers,
        json={"order_id": order.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["is_verified"] is True

def test_verify_customer_session_invalid_order(db: Session):
    customer = db.query(Customer).first()
    unverified_token = create_customer_session_token(customer.id, is_verified=False, email=customer.email)
    headers = {"Authorization": f"Bearer {unverified_token}"}

    # Verify with non-matching order
    response = client.post(
        "/api/v1/auth/customer-session/verify",
        headers=headers,
        json={"order_id": 999999}
    )
    assert response.status_code == 400
    data = get_error_payload(response)
    assert data["success"] is False
    assert "verification failed" in data["reason"].lower()

# -------------------------------------------------------------
# 2. Staff Authentication & RBAC Tests
# -------------------------------------------------------------
def test_staff_login_support_agent():
    response = client.post(
        "/api/v1/auth/staff-login",
        json={"username": "agent_sarah", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["staff_role"] == "support_agent"
    assert "access_token" in data["data"]

def test_staff_login_admin():
    response = client.post(
        "/api/v1/auth/staff-login",
        json={"username": "admin_alex", "password": "adminpassword123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["staff_role"] == "admin"

def test_staff_login_invalid_credentials():
    response = client.post(
        "/api/v1/auth/staff-login",
        json={"username": "agent_sarah", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    data = get_error_payload(response)
    assert data["success"] is False

# -------------------------------------------------------------
# 3. Unauthorized & Unauthenticated Rejection Tests
# -------------------------------------------------------------
def test_unauthenticated_request_rejected(db: Session):
    customer = db.query(Customer).first()
    response = client.get(f"/api/v1/customers/{customer.id}")
    assert response.status_code == 401
    data = get_error_payload(response)
    assert data["success"] is False
    assert "authentication required" in data["reason"].lower() or "missing" in data["reason"].lower()

def test_invalid_token_rejected():
    headers = {"Authorization": "Bearer invalid_gibberish_token_value"}
    response = client.get("/api/v1/customers/1", headers=headers)
    assert response.status_code == 401
    data = get_error_payload(response)
    assert data["success"] is False
    assert "invalid or expired" in data["reason"].lower()

# -------------------------------------------------------------
# 4. Sensitive Actions: Unverified vs Verified Customer Sessions
# -------------------------------------------------------------
def test_unverified_customer_cannot_perform_sensitive_refund(db: Session):
    customer = db.query(Customer).first()
    order = db.query(Order).filter(Order.customer_id == customer.id).first()
    unverified_token = create_customer_session_token(customer.id, is_verified=False)
    headers = {"Authorization": f"Bearer {unverified_token}"}

    response = client.post(
        f"/api/v1/orders/{order.id}/refund",
        headers=headers,
        json={"reason": "Damaged goods"}
    )
    assert response.status_code == 403
    data = get_error_payload(response)
    assert data["success"] is False
    assert "verified in the current session" in data["reason"].lower()

def test_unverified_customer_cannot_perform_sensitive_address_change(db: Session):
    customer = db.query(Customer).first()
    unverified_token = create_customer_session_token(customer.id, is_verified=False)
    headers = {"Authorization": f"Bearer {unverified_token}"}

    response = client.post(
        f"/api/v1/customers/{customer.id}/address",
        headers=headers,
        json={"new_address": "456 Unverified Way"}
    )
    assert response.status_code == 403
    data = get_error_payload(response)
    assert data["success"] is False
    assert "verified" in data["reason"].lower()

def test_unverified_customer_cannot_perform_sensitive_password_reset(db: Session):
    customer = db.query(Customer).first()
    unverified_token = create_customer_session_token(customer.id, is_verified=False)
    headers = {"Authorization": f"Bearer {unverified_token}"}

    response = client.post(
        f"/api/v1/customers/{customer.id}/password-reset",
        headers=headers,
        json={}
    )
    assert response.status_code == 403
    data = get_error_payload(response)
    assert data["success"] is False
    assert "verified" in data["reason"].lower()

def test_unverified_customer_CAN_perform_order_tracking_lookup(db: Session):
    customer = db.query(Customer).first()
    order = db.query(Order).filter(Order.customer_id == customer.id).first()
    unverified_token = create_customer_session_token(customer.id, is_verified=False)
    headers = {"Authorization": f"Bearer {unverified_token}"}

    response = client.get(f"/api/v1/orders/{order.id}/tracking", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["order_id"] == order.id

# -------------------------------------------------------------
# 5. Customer Tenant Isolation Tests (Cross-Customer Access)
# -------------------------------------------------------------
def test_customer_cannot_access_other_customer_profile(db: Session):
    customers = db.query(Customer).limit(2).all()
    if len(customers) >= 2:
        c1, c2 = customers[0], customers[1]
        c1_token = create_customer_session_token(c1.id, is_verified=True)
        headers = {"Authorization": f"Bearer {c1_token}"}

        # Customer 1 attempts to access Customer 2 profile
        response = client.get(f"/api/v1/customers/{c2.id}", headers=headers)
        assert response.status_code == 403
        data = get_error_payload(response)
        assert data["success"] is False
        assert "belonging to another customer" in data["reason"].lower()

# -------------------------------------------------------------
# 6. Staff & Analytics Authorization Tests
# -------------------------------------------------------------
def test_customer_cannot_access_staff_tickets_list(db: Session):
    customer = db.query(Customer).first()
    token = create_customer_session_token(customer.id, is_verified=True)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/tickets", headers=headers)
    assert response.status_code == 403
    data = get_error_payload(response)
    assert data["success"] is False
    assert "staff authorization" in data["reason"].lower()

def test_customer_cannot_access_analytics_dashboard(db: Session):
    customer = db.query(Customer).first()
    token = create_customer_session_token(customer.id, is_verified=True)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/analytics/dashboard", headers=headers)
    assert response.status_code == 403

def test_staff_agent_can_access_tickets_and_analytics():
    staff_token = create_staff_token(staff_id="staff_001", role="support_agent", username="agent_sarah")
    headers = {"Authorization": f"Bearer {staff_token}"}

    # List tickets
    response = client.get("/api/v1/tickets", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

    # Analytics dashboard
    response = client.get("/api/v1/analytics/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "total_tickets" in data["data"]
    assert data["data"]["staff_viewer"] == "agent_sarah"

# -------------------------------------------------------------
# 7. Agent Scoped Service Credentials Tests
# -------------------------------------------------------------
def test_agent_service_key_access(db: Session):
    customer = db.query(Customer).first()
    headers = {
        "X-Agent-Service-Key": settings.AGENT_SERVICE_SECRET,
        "X-Customer-ID": str(customer.id)
    }

    # Agent executing read tool for customer
    response = client.get(f"/api/v1/customers/{customer.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == customer.id

def test_agent_invalid_service_key_rejected():
    headers = {"X-Agent-Service-Key": "wrong_invalid_service_secret"}
    response = client.get("/api/v1/customers/1", headers=headers)
    assert response.status_code == 401
    data = get_error_payload(response)
    assert data["success"] is False
    assert "invalid agent service credentials" in data["reason"].lower()
