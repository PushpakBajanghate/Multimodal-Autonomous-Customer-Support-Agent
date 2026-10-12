from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import Order, OrderItem, Refund, Cancellation

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

    if order.status == "cancelled":
        cancellation = (
            db.query(Cancellation)
            .filter(Cancellation.order_id == order_id)
            .order_by(Cancellation.created_at.desc())
            .first()
        )
        if cancellation:
            tracking_data["cancellation_reason"] = cancellation.reason
            tracking_data["cancellation_status"] = cancellation.status
        else:
            tracking_data["cancellation_reason"] = "Customer cancellation request."
            tracking_data["cancellation_status"] = "approved"

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


def get_order_cancellation(db: Session, order_id: int) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Retrieves cancellation details for a cancelled order."""
    success, error, order = get_order_by_id(db, order_id)
    if not success or not order:
        return False, error or f"Order #{order_id} not found.", None

    cancellation = (
        db.query(Cancellation)
        .filter(Cancellation.order_id == order_id)
        .order_by(Cancellation.created_at.desc())
        .first()
    )

    if cancellation:
        return True, None, {
            "order_id": order.id,
            "order_status": order.status,
            "cancellation_id": cancellation.id,
            "reason": cancellation.reason,
            "status": cancellation.status,
            "cancelled_at": cancellation.created_at.strftime("%B %d, %Y") if cancellation.created_at else None
        }

    if order.status == "cancelled":
        return True, None, {
            "order_id": order.id,
            "order_status": order.status,
            "cancellation_id": None,
            "reason": "Cancelled per customer request / automated order cancellation policy.",
            "status": "approved",
            "cancelled_at": None
        }

    return False, f"Order #{order_id} is not cancelled (current status: {order.status}).", None


def reorder_cancelled_order(db: Session, order_id: int) -> Tuple[bool, Optional[str], Optional[Order]]:
    """
    Reorders an order (typically after cancellation) by creating a new active order 
    with the same customer and items in 'placed' status.
    """
    success, error, original_order = get_order_by_id(db, order_id)
    if not success or not original_order:
        return False, error or f"Order #{order_id} not found.", None

    now = datetime.now(timezone.utc)
    expected_delivery = now + timedelta(days=4)

    new_order = Order(
        customer_id=original_order.customer_id,
        status="placed",
        order_date=now,
        expected_delivery=expected_delivery,
        total_amount=original_order.total_amount,
        is_editable=True
    )
    db.add(new_order)
    db.flush()

    # Clone all items from the original order
    for item in original_order.items:
        new_item = OrderItem(
            order_id=new_order.id,
            product_name=item.product_name,
            quantity=item.quantity,
            price=item.price
        )
        db.add(new_item)

    db.commit()
    db.refresh(new_order)
    return True, None, new_order


