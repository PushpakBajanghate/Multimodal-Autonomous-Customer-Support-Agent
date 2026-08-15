from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import Customer, Ticket

def create_escalation_ticket(
    db: Session,
    customer_id: int,
    channel: str,
    intent: str,
    actions_attempted: Dict[str, Any],
    tool_results: Dict[str, Any],
    escalation_reason: str
) -> Tuple[bool, Optional[str], Optional[Ticket]]:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return False, f"Customer with ID {customer_id} not found", None

    ticket = Ticket(
        customer_id=customer_id,
        channel=channel,
        intent=intent,
        actions_attempted=actions_attempted,
        tool_results=tool_results,
        escalation_reason=escalation_reason,
        status="open"
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return True, None, ticket
