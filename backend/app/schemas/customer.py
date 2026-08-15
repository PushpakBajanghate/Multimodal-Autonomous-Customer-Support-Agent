from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime

class AddressChangeCreate(BaseModel):
    new_address: str
    order_id: Optional[int] = None

class AddressChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    order_id: Optional[int] = None
    new_address: str
    status: str
    created_at: datetime

class PasswordResetCreate(BaseModel):
    note: Optional[str] = None

class PasswordResetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    token: str
    status: str
    created_at: datetime
