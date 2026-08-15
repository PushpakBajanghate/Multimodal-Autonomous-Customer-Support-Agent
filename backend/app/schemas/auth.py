from typing import Optional, List
from pydantic import BaseModel, EmailStr

class CustomerSessionCreate(BaseModel):
    customer_id: Optional[int] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    order_id: Optional[int] = None
    verification_code: Optional[str] = None

class CustomerVerifySessionRequest(BaseModel):
    customer_id: Optional[int] = None
    order_id: Optional[int] = None
    verification_code: Optional[str] = None

class CustomerSessionRead(BaseModel):
    customer_id: int
    email: Optional[str] = None
    is_verified: bool
    access_token: str
    token_type: str = "bearer"

class StaffLoginRequest(BaseModel):
    username: str
    password: str

class StaffTokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "staff"
    staff_role: str  # "support_agent" or "admin"
    username: str
    name: Optional[str] = None

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    customer_id: Optional[int] = None
    is_verified: Optional[bool] = False
    staff_role: Optional[str] = None
    username: Optional[str] = None

class CustomerPrincipal(BaseModel):
    customer_id: int
    email: Optional[str] = None
    is_verified: bool = False
    auth_type: str = "customer_jwt"  # "customer_jwt" or "agent_service"

class StaffPrincipal(BaseModel):
    staff_id: str
    username: str
    staff_role: str  # "support_agent" or "admin"
    auth_type: str = "staff_jwt"

class AgentPrincipal(BaseModel):
    service_name: str = "agent_service"
    scopes: List[str] = ["tool_execution"]
    is_service: bool = True
