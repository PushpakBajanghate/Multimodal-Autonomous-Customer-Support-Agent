from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Ticket
from app.schemas.common import ApiResponse
from app.schemas.ticket import TicketCreate, TicketRead
from app.schemas.auth import StaffPrincipal
from app.api.deps import get_current_actor, get_current_staff
from app import services

router = APIRouter()

@router.post("", response_model=ApiResponse[TicketRead])
def create_ticket(
    payload: TicketCreate,
    actor = Depends(get_current_actor),
    db: Session = Depends(get_db)
):
    """
    Creates an escalation ticket.
    Can be created by customer sessions, autonomous agent tool executions, or internal staff.
    """
    success, error, ticket = services.create_escalation_ticket(
        db,
        customer_id=payload.customer_id,
        channel=payload.channel,
        intent=payload.intent,
        actions_attempted=payload.actions_attempted,
        tool_results=payload.tool_results,
        escalation_reason=payload.escalation_reason
    )

    if not success or not ticket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ApiResponse[TicketRead](
                success=False,
                status="failure",
                reason=error,
                data=None
            ).model_dump()
        )

    return ApiResponse[TicketRead](
        success=True,
        status="success",
        reason=None,
        data=TicketRead.model_validate(ticket)
    )

@router.get("", response_model=ApiResponse[List[TicketRead]])
def list_tickets(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    staff: StaffPrincipal = Depends(get_current_staff)
):
    """
    Lists support tickets for the staff escalation dashboard.
    Requires staff role (support_agent or admin).
    """
    query = db.query(Ticket)
    if status_filter:
        query = query.filter(Ticket.status == status_filter)
    tickets = query.order_by(Ticket.created_at.desc()).all()

    return ApiResponse[List[TicketRead]](
        success=True,
        status="success",
        reason=None,
        data=[TicketRead.model_validate(t) for t in tickets]
    )

@router.get("/{id}", response_model=ApiResponse[TicketRead])
def get_ticket(
    id: int,
    db: Session = Depends(get_db),
    staff: StaffPrincipal = Depends(get_current_staff)
):
    """
    Retrieves detailed escalation ticket by ID.
    Requires staff role (support_agent or admin).
    """
    ticket = db.query(Ticket).filter(Ticket.id == id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiResponse[TicketRead](
                success=False,
                status="failure",
                reason=f"Ticket #{id} not found.",
                data=None
            ).model_dump()
        )

    return ApiResponse[TicketRead](
        success=True,
        status="success",
        reason=None,
        data=TicketRead.model_validate(ticket)
    )
