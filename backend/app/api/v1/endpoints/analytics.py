from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models import Ticket, Order, Refund, Customer
from app.api.deps import get_current_staff
from app.schemas.auth import StaffPrincipal
from app.schemas.common import ApiResponse

router = APIRouter()

@router.get("/dashboard", response_model=ApiResponse[Dict[str, Any]])
def get_escalation_analytics(
    db: Session = Depends(get_db),
    staff: StaffPrincipal = Depends(get_current_staff)
):
    """
    Returns analytics metrics and escalation summaries for the staff dashboard.
    Requires staff role (support_agent or admin).
    """
    total_tickets = db.query(Ticket).count()
    open_tickets = db.query(Ticket).filter(Ticket.status == "open").count()
    resolved_tickets = db.query(Ticket).filter(Ticket.status == "resolved").count()
    total_orders = db.query(Order).count()
    total_refunds = db.query(Refund).count()
    total_customers = db.query(Customer).count()

    # Intent breakdown
    intent_counts = (
        db.query(Ticket.intent, func.count(Ticket.id))
        .group_by(Ticket.intent)
        .all()
    )
    intent_breakdown = {intent: count for intent, count in intent_counts}

    metrics = {
        "staff_viewer": staff.username,
        "role": staff.staff_role,
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "resolved_tickets": resolved_tickets,
        "total_orders": total_orders,
        "total_refunds": total_refunds,
        "total_customers": total_customers,
        "intent_breakdown": intent_breakdown,
        "escalation_rate_pct": round((open_tickets / max(1, total_orders)) * 100, 2)
    }

    return ApiResponse[Dict[str, Any]](
        success=True,
        status="success",
        reason=None,
        data=metrics
    )
