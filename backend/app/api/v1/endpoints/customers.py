from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.customer import (
    CustomerRead, AddressChangeCreate, AddressChangeRead,
    PasswordResetCreate, PasswordResetRead
)
from app.schemas.order import OrderRead
from app.schemas.auth import CustomerPrincipal
from app.api.deps import get_current_customer, require_verified_customer
from app import services

router = APIRouter()

def _check_customer_authorization(current_customer: CustomerPrincipal, target_customer_id: int):
    if current_customer.auth_type == "customer_jwt" and current_customer.customer_id != target_customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ApiResponse(
                success=False,
                status="failure",
                reason="Access forbidden: cannot access or modify resources belonging to another customer.",
                data=None
            ).model_dump()
        )

@router.get("/{id}", response_model=ApiResponse[CustomerRead])
def get_customer(
    id: int,
    db: Session = Depends(get_db),
    current_customer: CustomerPrincipal = Depends(get_current_customer)
):
    _check_customer_authorization(current_customer, id)
    success, error, customer = services.get_customer_by_id(db, customer_id=id)
    if not success or not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiResponse[CustomerRead](
                success=False,
                status="failure",
                reason=error,
                data=None
            ).model_dump()
        )
    
    return ApiResponse[CustomerRead](
        success=True,
        status="success",
        reason=None,
        data=CustomerRead.model_validate(customer)
    )

@router.get("/{id}/orders", response_model=ApiResponse[List[OrderRead]])
def get_customer_orders(
    id: int,
    db: Session = Depends(get_db),
    current_customer: CustomerPrincipal = Depends(get_current_customer)
):
    _check_customer_authorization(current_customer, id)
    success, error, orders = services.get_customer_orders(db, customer_id=id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiResponse[List[OrderRead]](
                success=False,
                status="failure",
                reason=error,
                data=[]
            ).model_dump()
        )
    
    order_reads = [OrderRead.model_validate(o) for o in orders]
    return ApiResponse[List[OrderRead]](
        success=True,
        status="success",
        reason=None,
        data=order_reads
    )

@router.post("/{id}/address", response_model=ApiResponse[AddressChangeRead])
def update_customer_address(
    id: int,
    payload: AddressChangeCreate,
    db: Session = Depends(get_db),
    current_customer: CustomerPrincipal = Depends(require_verified_customer)
):
    """
    Sensitive Action: Requires customer identity to be verified in the current session.
    """
    _check_customer_authorization(current_customer, id)
    success, error, addr_req = services.request_address_change(
        db, customer_id=id, new_address=payload.new_address, order_id=payload.order_id
    )
    if not success or not addr_req:
        is_not_found = "not found" in (error or "").lower()
        is_conflict = "cannot update address" in (error or "").lower() or "not editable" in (error or "").lower()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if is_not_found else (
                status.HTTP_409_CONFLICT if is_conflict else status.HTTP_400_BAD_REQUEST
            ),
            detail=ApiResponse[AddressChangeRead](
                success=False,
                status="failure",
                reason=error,
                data=None
            ).model_dump()
        )

    return ApiResponse[AddressChangeRead](
        success=True,
        status="success",
        reason=None,
        data=AddressChangeRead.model_validate(addr_req)
    )

@router.post("/{id}/password-reset", response_model=ApiResponse[PasswordResetRead])
def request_password_reset(
    id: int,
    payload: PasswordResetCreate = PasswordResetCreate(),
    db: Session = Depends(get_db),
    current_customer: CustomerPrincipal = Depends(require_verified_customer)
):
    """
    Sensitive Action: Requires customer identity to be verified in the current session.
    """
    _check_customer_authorization(current_customer, id)
    success, error, reset_req = services.request_password_reset(db, customer_id=id)
    if not success or not reset_req:
        is_not_found = "not found" in (error or "").lower()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if is_not_found else status.HTTP_400_BAD_REQUEST,
            detail=ApiResponse[PasswordResetRead](
                success=False,
                status="failure",
                reason=error,
                data=None
            ).model_dump()
        )

    return ApiResponse[PasswordResetRead](
        success=True,
        status="success",
        reason=None,
        data=PasswordResetRead.model_validate(reset_req)
    )
