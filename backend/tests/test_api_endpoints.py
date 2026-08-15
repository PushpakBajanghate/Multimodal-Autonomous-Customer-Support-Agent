import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models import Customer, Order, OrderItem

client = TestClient(app, raise_server_exceptions=False)

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
    
    response = client.get(f"/api/v1/customers/{customer.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "success"
    assert data["data"]["id"] == customer.id
    assert data["data"]["email"] == customer.email

def test_get_customer_not_found():
    response = client.get("/api/v1/customers/999999")
    assert response.status_code == 404
    data = response.json()["detail"]
    assert data["success"] is False
    assert data["status"] == "failure"
    assert "not found" in data["reason"].lower()


# 2. GET /customers/{id}/orders
def test_get_customer_orders_happy_path(db: Session):
    customer = db.query(Customer).first()
    assert customer is not None
    
    response = client.get(f"/api/v1/customers/{customer.id}/orders")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_get_customer_orders_not_found():
    response = client.get("/api/v1/customers/999999/orders")
    assert response.status_code == 404


# 3. GET /orders/{id}
def test_get_order_happy_path(db: Session):
    order = db.query(Order).first()
    assert order is not None
    
    response = client.get(f"/api/v1/orders/{order.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == order.id

def test_get_order_not_found():
    response = client.get("/api/v1/orders/999999")
    assert response.status_code == 404


# 4. GET /orders/{id}/tracking
def test_get_order_tracking_happy_path(db: Session):
    order = db.query(Order).first()
    assert order is not None

    response = client.get(f"/api/v1/orders/{order.id}/tracking")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["order_id"] == order.id
    assert "carrier" in data["data"]

def test_get_order_tracking_not_found():
    response = client.get("/api/v1/orders/999999/tracking")
    assert response.status_code == 404


# 5. POST /orders/{id}/refund (Happy & Rejection)
def test_refund_happy_path(db: Session):
    # Create an eligible order (delivered, 5 days ago)
    customer = db.query(Customer).first()
    order = Order(
        customer_id=customer.id,
        status="delivered",
        order_date=datetime.utcnow() - timedelta(days=5),
        expected_delivery=datetime.utcnow() - timedelta(days=2),
        total_amount=100.00,
        is_editable=False
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    response = client.post(
        f"/api/v1/orders/{order.id}/refund",
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
        order_date=datetime.utcnow() - timedelta(days=2),
        expected_delivery=datetime.utcnow() + timedelta(days=2),
        total_amount=50.00,
        is_editable=False
    )
    db.add(order)
    db.commit()

    response = client.post(
        f"/api/v1/orders/{order.id}/refund",
        json={"reason": "Decided I don't want it"}
    )
    assert response.status_code == 409
    data = response.json()["detail"]
    assert data["success"] is False
    assert data["status"] == "failure"
    assert "ineligible" in data["reason"].lower()


# 6. POST /orders/{id}/cancel (Happy & Rejection)
def test_cancel_order_happy_path(db: Session):
    customer = db.query(Customer).first()
    order = Order(
        customer_id=customer.id,
        status="placed",
        order_date=datetime.utcnow(),
        expected_delivery=datetime.utcnow() + timedelta(days=4),
        total_amount=75.00,
        is_editable=True
    )
    db.add(order)
    db.commit()

    response = client.post(
        f"/api/v1/orders/{order.id}/cancel",
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
        order_date=datetime.utcnow() - timedelta(days=2),
        expected_delivery=datetime.utcnow() + timedelta(days=1),
        total_amount=120.00,
        is_editable=False
    )
    db.add(order)
    db.commit()

    response = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        json={"reason": "Too late cancellation attempt"}
    )
    assert response.status_code == 409
    data = response.json()["detail"]
    assert data["success"] is False
    assert "cannot be cancelled" in data["reason"].lower()


# 7. POST /customers/{id}/address (Happy & Rejection)
def test_address_change_happy_path(db: Session):
    customer = db.query(Customer).first()
    response = client.post(
        f"/api/v1/customers/{customer.id}/address",
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
        order_date=datetime.utcnow() - timedelta(days=3),
        expected_delivery=datetime.utcnow() + timedelta(days=1),
        total_amount=200.00,
        is_editable=False
    )
    db.add(order)
    db.commit()

    response = client.post(
        f"/api/v1/customers/{customer.id}/address",
        json={"new_address": "200 Late Change Rd", "order_id": order.id}
    )
    assert response.status_code == 409
    data = response.json()["detail"]
    assert data["success"] is False
    assert "not editable" in data["reason"].lower()


# 8. POST /customers/{id}/password-reset (Happy & Rejection)
def test_password_reset_happy_path(db: Session):
    customer = db.query(Customer).first()
    response = client.post(f"/api/v1/customers/{customer.id}/password-reset", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "reset_token_" in data["data"]["token"]

def test_password_reset_not_found():
    response = client.post("/api/v1/customers/999999/password-reset", json={})
    assert response.status_code == 404


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
    response = client.post("/api/v1/tickets", json=payload)
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
    response = client.post("/api/v1/tickets", json=payload)
    assert response.status_code == 400
    data = response.json()["detail"]
    assert data["success"] is False
    assert "not found" in data["reason"].lower()
