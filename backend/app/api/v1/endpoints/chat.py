from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Conversation, ConversationMessage
from app.api.deps import get_current_actor
from app.schemas.auth import CustomerPrincipal, StaffPrincipal, AgentPrincipal
from app.schemas.common import ApiResponse
from app.schemas.chat import (
    ChatRequest, ChatResponse, ConversationMessageRead, ConversationRead
)

router = APIRouter()

@router.post("", response_model=ApiResponse[ChatResponse])
def send_chat_message(
    payload: ChatRequest,
    actor = Depends(get_current_actor),
    db: Session = Depends(get_db)
):
    """
    Customer-facing chat endpoint.
    Maintains conversation session state and persists all messages to the PostgreSQL database.
    (Stubbed response for Phase 2; autonomous agent LLM reasoning pipeline connects in Phase 3/4).
    """
    customer_id = None
    if isinstance(actor, CustomerPrincipal):
        customer_id = actor.customer_id if actor.customer_id > 0 else None

    # 1. Retrieve or Create Conversation Session
    conversation = None
    if payload.conversation_id is not None:
        conversation = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()

    if not conversation:
        conversation = Conversation(
            customer_id=customer_id,
            channel=payload.channel or "chat",
            status="active"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 2. Persist User Message
    user_msg = ConversationMessage(
        conversation_id=conversation.id,
        sender="user",
        message_text=payload.message
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 3. Generate Agent Reply (Stubbed for Phase 2)
    clean_text = payload.message.strip()
    agent_reply_text = (
        f"Thank you for contacting Aura Support! I received your inquiry: \"{clean_text}\". "
        f"Our support system is active (Session #{conversation.id}). How else can I assist you today?"
    )

    # 4. Persist Agent Message
    agent_msg = ConversationMessage(
        conversation_id=conversation.id,
        sender="agent",
        message_text=agent_reply_text
    )
    db.add(agent_msg)
    db.commit()
    db.refresh(agent_msg)

    return ApiResponse[ChatResponse](
        success=True,
        status="success",
        reason=None,
        data=ChatResponse(
            conversation_id=conversation.id,
            user_message_id=user_msg.id,
            agent_message_id=agent_msg.id,
            reply=agent_reply_text,
            created_at=agent_msg.created_at or datetime.now(timezone.utc)
        )
    )

@router.get("/conversations/{id}/messages", response_model=ApiResponse[List[ConversationMessageRead]])
def get_conversation_messages(
    id: int,
    actor = Depends(get_current_actor),
    db: Session = Depends(get_db)
):
    """
    Retrieves stored message history for a specific conversation session from the database.
    """
    conversation = db.query(Conversation).filter(Conversation.id == id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiResponse[List[ConversationMessageRead]](
                success=False,
                status="failure",
                reason=f"Conversation #{id} not found.",
                data=[]
            ).model_dump()
        )

    # If caller is customer, verify ownership
    if isinstance(actor, CustomerPrincipal) and actor.auth_type == "customer_jwt" and conversation.customer_id:
        if conversation.customer_id != actor.customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ApiResponse[List[ConversationMessageRead]](
                    success=False,
                    status="failure",
                    reason="Access forbidden: cannot view another customer's conversation.",
                    data=[]
                ).model_dump()
            )

    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )

    return ApiResponse[List[ConversationMessageRead]](
        success=True,
        status="success",
        reason=None,
        data=[ConversationMessageRead.model_validate(m) for m in messages]
    )

@router.post("/conversations/new", response_model=ApiResponse[ConversationRead])
def create_new_conversation(
    channel: str = "chat",
    actor = Depends(get_current_actor),
    db: Session = Depends(get_db)
):
    """
    Explicitly starts a new conversation session.
    """
    customer_id = None
    if isinstance(actor, CustomerPrincipal):
        customer_id = actor.customer_id if actor.customer_id > 0 else None

    conversation = Conversation(
        customer_id=customer_id,
        channel=channel,
        status="active"
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return ApiResponse[ConversationRead](
        success=True,
        status="success",
        reason=None,
        data=ConversationRead.model_validate(conversation)
    )
