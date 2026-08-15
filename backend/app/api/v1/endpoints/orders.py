from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.order import (
    OrderRead, OrderTrackingRead, RefundCreate, RefundRead,
    CancellationCreate, CancellationRead
)
from app import services

router = APIRouter()

@router.get("/{id}", response_model=ApiResponse[OrderRead])
def get_order(id: int, db: Session = Depends(get_db)):
    success, error, order = services.get_order_by_id(db, order_id=id)
    if not success or not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiResponse[OrderRead](
                success=False,
                status="failure",
                reason=error,
                data=None
            ).model_dump()
        )

    return ApiResponse[OrderRead](
        success=True,
        status="success",
        reason=None,
        data=OrderRead.model_validate(order)
    )

@router.get("/{id}/tracking", response_model=ApiResponse[OrderTrackingRead])
def get_order_tracking(id: int, db: Session = Depends(get_db)):
    success, error, tracking_data = services.get_order_tracking(db, order_id=id)
    if not success or not tracking_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiResponse[OrderTrackingRead](
                success=False,
                status="failure",
                reason=error,
                data=None
            ).model_dump()
        )

    return ApiResponse[OrderTrackingRead](
        success=True,
        status="success",
        reason=None,
        data=OrderTrackingRead(**tracking_data)
    )

@router.post("/{id}/refund", response_model=ApiResponse[RefundRead])
def request_order_refund(
    id: int,
    payload: RefundCreate,
    db: Session = Depends(get_db)
):
    success, error, refund = services.process_refund(db, order_id=id, reason=payload.reason)
    if not success or not refund:
        # Check if error is due to not found vs ineligible business rule
        is_not_found = "not found" in (error or "").lower()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if is_not_found else status.HTTP_409_CONFLICT,
            detail=ApiResponse[RefundRead](
                success=False,
                status="failure",
                reason=error,
                data=None
            ).model_dump()
        )

    return ApiResponse[RefundRead](
        success=True,
        status="success",
        reason=None,
        data=RefundRead.model_validate(refund)
    )

@router.post("/{id}/cancel", response_model=ApiResponse[CancellationRead])
def cancel_order(
    id: int,
    payload: CancellationCreate,
    db: Session = Depends(get_db)
):
    success, error, cancellation = services.process_cancellation(db, order_id=id, reason=payload.reason)
    if not success or not cancellation:
        is_not_found = "not found" in (error or "").lower()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if is_not_found else status.HTTP_409_CONFLICT,
            detail=ApiResponse[CancellationRead](
                success=False,
                status="failure",
                reason=error,
                data=None
            ).model_dump()
        )

    return ApiResponse[CancellationRead](
        success=True,
        status="success",
        reason=None,
        data=CancellationRead.model_validate(cancellation)
    )
