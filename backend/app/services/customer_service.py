import uuid
from typing import Tuple, Optional, List
from sqlalchemy.orm import Session
from app.models import Customer, Order, AddressChangeRequest, PasswordResetRequest

def get_customer_by_id(db: Session, customer_id: int) -> Tuple[bool, Optional[str], Optional[Customer]]:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return False, f"Customer #{customer_id} not found in database.", None
    return True, None, customer

def get_customer_orders(db: Session, customer_id: int) -> Tuple[bool, Optional[str], List[Order]]:
    success, error, customer = get_customer_by_id(db, customer_id)
    if not success or not customer:
        return False, error, []
    return True, None, customer.orders

def request_address_change(
    db: Session, customer_id: int, new_address: str, order_id: Optional[int] = None
) -> Tuple[bool, Optional[str], Optional[AddressChangeRequest]]:
    success, error, customer = get_customer_by_id(db, customer_id)
    if not success or not customer:
        return False, error, None

    order = None
    if order_id is not None:
        order = db.query(Order).filter(Order.id == order_id, Order.customer_id == customer_id).first()
        if not order:
            return False, f"Order #{order_id} does not belong to Customer #{customer_id} or does not exist.", None
        
        # Check order editability business rules
        if not order.is_editable or order.status != "placed":
            return (
                False,
                f"Cannot update address for Order #{order_id}: order is in '{order.status}' status (is_editable={order.is_editable}). Address updates are only permitted while order is in 'placed' status.",
                None
            )

    addr_req = AddressChangeRequest(
        customer_id=customer_id,
        order_id=order_id,
        new_address=new_address,
        status="completed" if order else "pending"
    )
    db.add(addr_req)
    db.commit()
    db.refresh(addr_req)
    return True, None, addr_req

def request_password_reset(
    db: Session, customer_id: int
) -> Tuple[bool, Optional[str], Optional[PasswordResetRequest]]:
    success, error, customer = get_customer_by_id(db, customer_id)
    if not success or not customer:
        return False, error, None

    token = f"reset_token_{uuid.uuid4().hex[:16]}"
    reset_req = PasswordResetRequest(
        customer_id=customer_id,
        token=token,
        status="pending"
    )
    db.add(reset_req)
    db.commit()
    db.refresh(reset_req)
    return True, None, reset_req
