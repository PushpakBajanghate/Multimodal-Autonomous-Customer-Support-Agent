import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models import Customer, Conversation, ConversationMessage
from app.core.security import create_customer_session_token

client = TestClient(app, raise_server_exceptions=False)

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

def test_send_chat_message_creates_conversation_and_persists_messages(db: Session):
    customer = db.query(Customer).first()
    assert customer is not None

    payload = {
        "message": "Where is my package from yesterday?",
        "channel": "chat"
    }

    response = client.post(
        "/api/v1/chat",
        headers=auth_header(customer.id),
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "conversation_id" in data["data"]
    assert "reply" in data["data"]
    assert len(data["data"]["reply"]) > 5

    conv_id = data["data"]["conversation_id"]

    # Verify database persistence
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    assert conv is not None
    assert conv.customer_id == customer.id

    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conv_id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
    assert len(messages) == 2
    assert messages[0].sender == "user"
    assert messages[0].message_text == "Where is my package from yesterday?"
    assert messages[1].sender == "agent"
    assert len(messages[1].message_text) > 5

def test_send_chat_message_existing_conversation(db: Session):
    customer = db.query(Customer).first()

    # Step 1: First message creates session
    r1 = client.post(
        "/api/v1/chat",
        headers=auth_header(customer.id),
        json={"message": "First inquiry"}
    )
    assert r1.status_code == 200
    conv_id = r1.json()["data"]["conversation_id"]

    # Step 2: Second message in same conversation
    r2 = client.post(
        "/api/v1/chat",
        headers=auth_header(customer.id),
        json={"message": "Second follow-up question", "conversation_id": conv_id}
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["conversation_id"] == conv_id

    # Verify 4 messages in DB (2 user, 2 agent)
    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conv_id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
    assert len(messages) == 4

def test_get_conversation_messages_history(db: Session):
    customer = db.query(Customer).first()

    # Send a message
    r = client.post(
        "/api/v1/chat",
        headers=auth_header(customer.id),
        json={"message": "History test message"}
    )
    conv_id = r.json()["data"]["conversation_id"]

    # Fetch history via API
    hist_res = client.get(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_header(customer.id)
    )
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["success"] is True
    assert len(hist_data["data"]) >= 2
    assert hist_data["data"][0]["sender"] == "user"
    assert hist_data["data"][1]["sender"] == "agent"

def test_chat_unauthenticated_rejected():
    response = client.post(
        "/api/v1/chat",
        json={"message": "Hello without auth"}
    )
    assert response.status_code == 401

def test_real_agent_dynamic_intent_and_clarification(db: Session):
    customer = db.query(Customer).first()

    # 1. Ambiguous cancellation request
    r1 = client.post(
        "/api/v1/chat",
        headers=auth_header(customer.id),
        json={"message": "mera order cancel karna hai"}
    )
    assert r1.status_code == 200
    reply1 = r1.json()["data"]["reply"]
    # Agent should ask for Order ID rather than guess
    assert "order id" in reply1.lower() or "which order" in reply1.lower()

    # 2. Tracking with real order
    r2 = client.post(
        "/api/v1/chat",
        headers=auth_header(customer.id),
        json={"message": "Please track my order #9"}
    )
    assert r2.status_code == 200
    reply2 = r2.json()["data"]["reply"]
    assert "9" in reply2 or "order" in reply2.lower()
    assert "status" in reply2.lower() or "found" in reply2.lower() or "order" in reply2.lower()


def test_chat_call_request_does_not_claim_success_without_twilio_config(db: Session, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.TWILIO_ACCOUNT_SID", None)
    monkeypatch.setattr("app.core.config.settings.TWILIO_AUTH_TOKEN", None)
    monkeypatch.setattr("app.core.config.settings.TWILIO_FROM_NUMBER", None)
    monkeypatch.setattr("app.core.config.settings.PUBLIC_BASE_URL", None)
    customer = db.query(Customer).first()

    response = client.post(
        "/api/v1/chat",
        headers=auth_header(customer.id),
        json={"message": "call me on +918855998802"},
    )

    assert response.status_code == 200
    reply = response.json()["data"]["reply"].lower()
    assert "could not place" in reply or "not configured" in reply or "configure twilio" in reply
    assert "answer your phone" not in reply

