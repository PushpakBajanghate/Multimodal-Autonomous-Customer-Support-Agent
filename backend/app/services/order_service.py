from datetime import datetime, timezone
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import Order, Refund, Cancellation

def get_order_by_id(db: Session, order_id: int) -> Tuple[bool, Optional[str], Optional[Order]]:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return False, f"Order #{order_id} not found in database.", None
    return True, None, order

def get_order_tracking(db: Session, order_id: int) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    success, error, order = get_order_by_id(db, order_id)
    if not success or not order:
        return False, error, None

    now = datetime.now(timezone.utc)
    expected = order.expected_delivery
    if expected.tzinfo is None:
        expected = expected.replace(tzinfo=timezone.utc)

    diff_days = (expected - now).days
    estimated_days = max(0, diff_days)

    tracking_data = {
        "order_id": order.id,
        "status": order.status,
        "order_date": order.order_date,
        "expected_delivery": order.expected_delivery,
        "carrier": "FedEx Express" if order.id % 2 == 0 else "UPS Ground",
        "tracking_number": f"TRK-{order.id*1000 + 4921}",
        "estimated_days_remaining": estimated_days if order.status in ["placed", "shipped"] else 0,
        "is_delivered": order.status == "delivered"
    }
    return True, None, tracking_data

def process_refund(db: Session, order_id: int, reason: str) -> Tuple[bool, Optional[str], Optional[Refund]]:
    success, error, order = get_order_by_id(db, order_id)
    if not success or not order:
        return False, error, None

    # Business Rule 1: Status must be delivered or cancelled
    if order.status not in ["delivered", "cancelled"]:
        return (
            False,
            f"Cannot process refund for Order #{order_id}: current status is '{order.status}' (refunds are only permitted for delivered or cancelled orders).",
            None
        )

    # Business Rule 2: 30-day window check
    now = datetime.now(timezone.utc)
    order_dt = order.order_date
    if order_dt.tzinfo is None:
        order_dt = order_dt.replace(tzinfo=timezone.utc)

    days_since_order = (now - order_dt).days
    if days_since_order > 30:
        order_date_str = order.order_date.strftime('%Y-%m-%d')
        return (
            False,
            f"Refund ineligible for Order #{order_id}: order was placed on {order_date_str} ({days_since_order} days ago), which exceeds our 30-day return policy window.",
            None
        )

    # Business Rule 3: Existing active/approved refund check
    existing_refund = db.query(Refund).filter(
        Refund.order_id == order_id,
        Refund.status.in_(["requested", "approved", "processed"])
    ).first()

    if existing_refund:
        created_str = existing_refund.created_at.strftime('%Y-%m-%d') if existing_refund.created_at else "prior date"
        return (
            False,
            f"Cannot process refund for Order #{order_id}: a refund request was already {existing_refund.status} on {created_str} for ${existing_refund.amount:.2f}.",
            None
        )

    # Process refund
    refund = Refund(
        order_id=order.id,
        amount=order.total_amount,
        reason=reason,
        status="approved"
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return True, None, refund

def process_cancellation(db: Session, order_id: int, reason: str) -> Tuple[bool, Optional[str], Optional[Cancellation]]:
    success, error, order = get_order_by_id(db, order_id)
    if not success or not order:
        return False, error, None

    # Business Rule 1: Order must be in 'placed' status to cancel
    if order.status == "shipped":
        ship_date_str = order.order_date.strftime('%Y-%m-%d')
        return (
            False,
            f"Cannot cancel Order #{order_id}: order was already shipped on {ship_date_str} (cancellations are only allowed prior to shipping).",
            None
        )
    elif order.status == "delivered":
        deliv_date_str = order.expected_delivery.strftime('%Y-%m-%d')
        return (
            False,
            f"Cannot cancel Order #{order_id}: order was already delivered on {deliv_date_str}. Please initiate a refund request instead.",
            None
        )
    elif order.status == "cancelled":
        return (
            False,
            f"Cannot cancel Order #{order_id}: this order has already been cancelled.",
            None
        )
    elif order.status != "placed":
        return (
            False,
            f"Cannot cancel Order #{order_id}: order is in '{order.status}' status (only 'placed' orders can be cancelled).",
            None
        )

    # Update order state
    order.status = "cancelled"
    order.is_editable = False

    cancellation = Cancellation(
        order_id=order.id,
        reason=reason,
        status="approved"
    )
    db.add(cancellation)
    db.commit()
    db.refresh(cancellation)
    return True, None, cancellation
