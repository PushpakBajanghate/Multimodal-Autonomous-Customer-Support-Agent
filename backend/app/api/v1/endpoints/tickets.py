from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.ticket import TicketCreate, TicketRead
from app import services

router = APIRouter()

@router.post("", response_model=ApiResponse[TicketRead])
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db)
):
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
