from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str
    quantity: int
    price: float

class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    status: str
    order_date: datetime
    expected_delivery: datetime
    total_amount: float
    is_editable: bool
    items: List[OrderItemRead] = []

class OrderTrackingRead(BaseModel):
    order_id: int
    status: str
    order_date: datetime
    expected_delivery: datetime
    carrier: str
    tracking_number: str
    estimated_days_remaining: int
    is_delivered: bool

class RefundCreate(BaseModel):
    reason: str

class RefundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    amount: float
    reason: str
    status: str
    created_at: datetime

class CancellationCreate(BaseModel):
    reason: str

class CancellationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    reason: str
    status: str
    created_at: datetime
