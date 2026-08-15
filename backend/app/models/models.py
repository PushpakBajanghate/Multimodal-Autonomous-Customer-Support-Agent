from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String, ForeignKey, Numeric, Boolean, DateTime, JSON, Text, Integer, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, TimestampMixin

class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Relationships
    orders: Mapped[List["Order"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    tickets: Mapped[List["Ticket"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="customer")
    address_change_requests: Mapped[List["AddressChangeRequest"]] = relationship(back_populates="customer")
    password_reset_requests: Mapped[List["PasswordResetRequest"]] = relationship(back_populates="customer")


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # placed, shipped, delivered, cancelled
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_delivery: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_editable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    refunds: Mapped[List["Refund"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    cancellations: Mapped[List["Cancellation"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    address_change_requests: Mapped[List["AddressChangeRequest"]] = relationship(back_populates="order")


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="items")


class Refund(Base, TimestampMixin):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # requested, approved, rejected, processed

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="refunds")


class Cancellation(Base, TimestampMixin):
    __tablename__ = "cancellations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # requested, approved, rejected

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="cancellations")


class AddressChangeRequest(Base, TimestampMixin):
    __tablename__ = "address_change_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    new_address: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # pending, completed, rejected

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="address_change_requests")
    order: Mapped[Optional["Order"]] = relationship(back_populates="address_change_requests")


class PasswordResetRequest(Base, TimestampMixin):
    __tablename__ = "password_reset_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # pending, used, expired

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="password_reset_requests")


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)  # chat, voice
    intent: Mapped[str] = mapped_column(String(100), nullable=False)
    actions_attempted: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    tool_results: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    escalation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # open, in_progress, resolved, closed

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    tool_execution_logs: Mapped[List["ToolExecutionLog"]] = relationship(back_populates="ticket")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)  # chat, voice
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # active, completed

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="conversations")
    messages: Mapped[List["ConversationMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    tool_execution_logs: Mapped[List["ToolExecutionLog"]] = relationship(back_populates="conversation")


class ConversationMessage(Base, TimestampMixin):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(50), nullable=False)  # user, agent
    message_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class ToolExecutionLog(Base, TimestampMixin):
    __tablename__ = "tool_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    ticket_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    conversation: Mapped[Optional["Conversation"]] = relationship(back_populates="tool_execution_logs")
    ticket: Mapped[Optional["Ticket"]] = relationship(back_populates="tool_execution_logs")
