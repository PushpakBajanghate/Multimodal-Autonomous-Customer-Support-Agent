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
    assert "Where is my package" in data["data"]["reply"]

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
    assert "Thank you for contacting Aura Support" in messages[1].message_text

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
