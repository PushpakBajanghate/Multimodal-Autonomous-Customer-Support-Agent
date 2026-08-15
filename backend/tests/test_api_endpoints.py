import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models import Customer, Order, OrderItem
from app.core.security import create_customer_session_token

client = TestClient(app, raise_server_exceptions=False)

def get_error_payload(response):
    body = response.json()
    if "detail" in body and isinstance(body["detail"], dict):
        return body["detail"]
    return body

def auth_header(customer_id: int, is_verified: bool = True):
    token = create_customer_session_token(customer_id=customer_id, is_verified=is_verified)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# 1. GET /customers/{id}
def test_get_customer_happy_path(db: Session):
    customer = db.query(Customer).first()
    assert customer is not None, "Seed data must exist"
    
    response = client.get(
        f"/api/v1/customers/{customer.id}",
        headers=auth_header(customer.id)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "success"
    assert data["data"]["id"] == customer.id
    assert data["data"]["email"] == customer.email

def test_get_customer_not_found(db: Session):
    # Customer requesting non-existent ID with staff or self ID
    response = client.get("/api/v1/customers/999999", headers=auth_header(999999))
    assert response.status_code == 404
    data = get_error_payload(response)
    assert data["success"] is False
    assert data["status"] == "failure"
    assert "not found" in data["reason"].lower()


# 2. GET /customers/{id}/orders
def test_get_customer_orders_happy_path(db: Session):
    customer = db.query(Customer).first()
    assert customer is not None
    
    response = client.get(
        f"/api/v1/customers/{customer.id}/orders",
        headers=auth_header(customer.id)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_get_customer_orders_not_found():
    response = client.get("/api/v1/customers/999999/orders", headers=auth_header(999999))
    assert response.status_code == 404
    data = get_error_payload(response)
    assert data["success"] is False
    assert "not found" in data["reason"].lower()


# 3. GET /orders/{id}
def test_get_order_happy_path(db: Session):
    order = db.query(Order).first()
    assert order is not None
    
    response = client.get(
        f"/api/v1/orders/{order.id}",
        headers=auth_header(order.customer_id)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == order.id

def test_get_order_not_found(db: Session):
    customer = db.query(Customer).first()
    response = client.get("/api/v1/orders/999999", headers=auth_header(customer.id))
    assert response.status_code == 404
    data = get_error_payload(response)
    assert data["success"] is False
    assert "not found" in data["reason"].lower()


# 4. GET /orders/{id}/tracking
def test_get_order_tracking_happy_path(db: Session):
    order = db.query(Order).first()
    assert order is not None

    response = client.get(
        f"/api/v1/orders/{order.id}/tracking",
        headers=auth_header(order.customer_id)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["order_id"] == order.id
    assert "carrier" in data["data"]

def test_get_order_tracking_not_found(db: Session):
    customer = db.query(Customer).first()
    response = client.get("/api/v1/orders/999999/tracking", headers=auth_header(customer.id))
    assert response.status_code == 404
    data = get_error_payload(response)
    assert data["success"] is False
    assert "not found" in data["reason"].lower()


# 5. POST /orders/{id}/refund (Happy & Rejection)
def test_refund_happy_path(db: Session):
    # Create an eligible order (delivered, 5 days ago)
    customer = db.query(Customer).first()
    order = Order(
        customer_id=customer.id,
        status="delivered",
        order_date=datetime.now(timezone.utc) - timedelta(days=5),
        expected_delivery=datetime.now(timezone.utc) - timedelta(days=2),
        total_amount=100.00,
        is_editable=False
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    response = client.post(
        f"/api/v1/orders/{order.id}/refund",
        headers=auth_header(customer.id, is_verified=True),
        json={"reason": "Defective item received"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["order_id"] == order.id
    assert data["data"]["status"] == "approved"

def test_refund_rejection_path_ineligible_status(db: Session):
    # Order in 'shipped' status cannot be refunded
    customer = db.query(Customer).first()
    order = Order(
        customer_id=customer.id,
        status="shipped",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
        expected_delivery=datetime.now(timezone.utc) + timedelta(days=2),
        total_amount=50.00,
        is_editable=False
    )
    db.add(order)
    db.commit()

    response = client.post(
        f"/api/v1/orders/{order.id}/refund",
        headers=auth_header(customer.id, is_verified=True),
        json={"reason": "Decided I don't want it"}
    )
    assert response.status_code == 409
    data = get_error_payload(response)
    assert data["success"] is False
    assert data["status"] == "failure"
    assert "cannot process refund" in data["reason"].lower()


# 6. POST /orders/{id}/cancel (Happy & Rejection)
def test_cancel_order_happy_path(db: Session):
    customer = db.query(Customer).first()
    order = Order(
        customer_id=customer.id,
        status="placed",
        order_date=datetime.now(timezone.utc),
        expected_delivery=datetime.now(timezone.utc) + timedelta(days=4),
        total_amount=75.00,
        is_editable=True
    )
    db.add(order)
    db.commit()

    response = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers=auth_header(customer.id, is_verified=True),
        json={"reason": "Changed my mind"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "approved"

def test_cancel_order_rejection_already_shipped(db: Session):
    customer = db.query(Customer).first()
    order = Order(
        customer_id=customer.id,
        status="shipped",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
        expected_delivery=datetime.now(timezone.utc) + timedelta(days=1),
        total_amount=120.00,
        is_editable=False
    )
    db.add(order)
    db.commit()

    response = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers=auth_header(customer.id, is_verified=True),
        json={"reason": "Too late cancellation attempt"}
    )
    assert response.status_code == 409
    data = get_error_payload(response)
    assert data["success"] is False
    assert "already shipped" in data["reason"].lower()


# 7. POST /customers/{id}/address (Happy & Rejection)
def test_address_change_happy_path(db: Session):
    customer = db.query(Customer).first()
    response = client.post(
        f"/api/v1/customers/{customer.id}/address",
        headers=auth_header(customer.id, is_verified=True),
        json={"new_address": "100 New Street, NYC, NY"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["new_address"] == "100 New Street, NYC, NY"

def test_address_change_rejection_non_editable_order(db: Session):
    customer = db.query(Customer).first()
    order = Order(
        customer_id=customer.id,
        status="shipped",
        order_date=datetime.now(timezone.utc) - timedelta(days=3),
        expected_delivery=datetime.now(timezone.utc) + timedelta(days=1),
        total_amount=200.00,
        is_editable=False
    )
    db.add(order)
    db.commit()

    response = client.post(
        f"/api/v1/customers/{customer.id}/address",
        headers=auth_header(customer.id, is_verified=True),
        json={"new_address": "200 Late Change Rd", "order_id": order.id}
    )
    assert response.status_code == 409
    data = get_error_payload(response)
    assert data["success"] is False
    assert "cannot update address" in data["reason"].lower()


# 8. POST /customers/{id}/password-reset (Happy & Rejection)
def test_password_reset_happy_path(db: Session):
    customer = db.query(Customer).first()
    response = client.post(
        f"/api/v1/customers/{customer.id}/password-reset",
        headers=auth_header(customer.id, is_verified=True),
        json={}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "reset_token_" in data["data"]["token"]

def test_password_reset_not_found():
    response = client.post(
        "/api/v1/customers/999999/password-reset",
        headers=auth_header(999999, is_verified=True),
        json={}
    )
    assert response.status_code == 404
    data = get_error_payload(response)
    assert data["success"] is False
    assert "not found" in data["reason"].lower()


# 9. POST /tickets (Happy & Rejection)
def test_create_ticket_happy_path(db: Session):
    customer = db.query(Customer).first()
    payload = {
        "customer_id": customer.id,
        "channel": "chat",
        "intent": "dispute_charge",
        "actions_attempted": {"checked_receipt": True},
        "tool_results": {"charge_id": "ch_123"},
        "escalation_reason": "Customer requests human intervention for charge review."
    }
    response = client.post(
        "/api/v1/tickets",
        headers=auth_header(customer.id),
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "open"

def test_create_ticket_rejection_invalid_customer():
    payload = {
        "customer_id": 999999,
        "channel": "voice",
        "intent": "unknown",
        "escalation_reason": "Unknown customer ID."
    }
    response = client.post(
        "/api/v1/tickets",
        headers=auth_header(999999),
        json=payload
    )
    assert response.status_code == 400
    data = get_error_payload(response)
    assert data["success"] is False
    assert "not found" in data["reason"].lower()
