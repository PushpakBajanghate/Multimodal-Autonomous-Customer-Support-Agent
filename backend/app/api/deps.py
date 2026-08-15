from typing import Optional, Union
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.schemas.auth import (
    CustomerPrincipal, StaffPrincipal, AgentPrincipal
)
from app.schemas.common import ApiResponse

bearer_scheme = HTTPBearer(auto_error=False)
agent_key_header = APIKeyHeader(name="X-Agent-Service-Key", auto_error=False)

def _raise_auth_error(status_code: int, message: str):
    raise HTTPException(
        status_code=status_code,
        detail=ApiResponse(
            success=False,
            status="failure",
            reason=message,
            data=None
        ).model_dump()
    )

def get_current_actor(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    agent_key: Optional[str] = Depends(agent_key_header),
) -> Union[CustomerPrincipal, StaffPrincipal, AgentPrincipal]:
    """
    Extracts the authenticated actor from either:
    1. A scoped Agent Service key header (X-Agent-Service-Key)
    2. A Customer JWT (role='customer')
    3. A Staff JWT (role='staff')
    """
    # 1. Check Agent Service Credential
    if agent_key:
        if agent_key == settings.AGENT_SERVICE_SECRET:
            return AgentPrincipal(
                service_name="agent_service",
                scopes=["tool_execution", "customer_support"],
                is_service=True
            )
        else:
            _raise_auth_error(status.HTTP_401_UNAUTHORIZED, "Invalid agent service credentials.")

    # 2. Check Bearer Token
    if not auth or not auth.credentials:
        _raise_auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "Authentication required. Missing Bearer token or Service credentials."
        )

    payload = decode_access_token(auth.credentials)
    if not payload:
        _raise_auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired authentication token."
        )

    role = payload.get("role")
    if role == "customer":
        customer_id = payload.get("customer_id") or payload.get("sub")
        if not customer_id:
            _raise_auth_error(status.HTTP_401_UNAUTHORIZED, "Invalid customer token payload.")
        return CustomerPrincipal(
            customer_id=int(customer_id),
            email=payload.get("email"),
            is_verified=bool(payload.get("is_verified", False)),
            auth_type="customer_jwt"
        )
    elif role == "staff":
        staff_role = payload.get("staff_role", "support_agent")
        return StaffPrincipal(
            staff_id=payload.get("sub", ""),
            username=payload.get("username", ""),
            staff_role=staff_role,
            auth_type="staff_jwt"
        )
    elif role == "agent_service":
        return AgentPrincipal(
            service_name="agent_service",
            scopes=payload.get("scopes", ["tool_execution"]),
            is_service=True
        )

    _raise_auth_error(status.HTTP_401_UNAUTHORIZED, "Unrecognized token role.")

def get_current_customer(
    actor: Union[CustomerPrincipal, StaffPrincipal, AgentPrincipal] = Depends(get_current_actor),
    x_customer_id: Optional[int] = Header(default=None, alias="X-Customer-ID"),
    x_customer_verified: Optional[bool] = Header(default=None, alias="X-Customer-Verified"),
) -> CustomerPrincipal:
    """
    Ensures caller is a customer or a service acting on behalf of a customer.
    """
    if isinstance(actor, CustomerPrincipal):
        return actor

    if isinstance(actor, AgentPrincipal):
        # Scoped agent tool execution for a customer
        if x_customer_id is not None:
            return CustomerPrincipal(
                customer_id=x_customer_id,
                is_verified=x_customer_verified if x_customer_verified is not None else True,
                auth_type="agent_service"
            )
        # Agent acting in generic customer context
        return CustomerPrincipal(
            customer_id=0,
            is_verified=True,
            auth_type="agent_service"
        )

    if isinstance(actor, StaffPrincipal):
        # Staff acting on behalf of customer support
        target_id = x_customer_id if x_customer_id is not None else 0
        return CustomerPrincipal(
            customer_id=target_id,
            is_verified=True,
            auth_type="staff_proxy"
        )

    _raise_auth_error(status.HTTP_403_FORBIDDEN, "Customer access required.")

def require_verified_customer(
    customer: CustomerPrincipal = Depends(get_current_customer),
) -> CustomerPrincipal:
    """
    Enforces that customer identity is verified in the current session.
    Required for sensitive actions (refund, cancellation, address change, password reset).
    """
    if not customer.is_verified:
        _raise_auth_error(
            status.HTTP_403_FORBIDDEN,
            "Customer identity must be verified in the current session before performing this sensitive action."
        )
    return customer

def get_current_staff(
    actor: Union[CustomerPrincipal, StaffPrincipal, AgentPrincipal] = Depends(get_current_actor),
) -> StaffPrincipal:
    """
    Enforces that caller is internal staff with support_agent or admin role.
    """
    if isinstance(actor, StaffPrincipal):
        if actor.staff_role in ["support_agent", "admin"]:
            return actor
        _raise_auth_error(
            status.HTTP_403_FORBIDDEN,
            f"Insufficient permissions: staff role '{actor.staff_role}' not authorized."
        )
    _raise_auth_error(
        status.HTTP_403_FORBIDDEN,
        "Staff authorization with 'support_agent' or 'admin' role is required."
    )

def require_admin_staff(
    staff: StaffPrincipal = Depends(get_current_staff),
) -> StaffPrincipal:
    """
    Enforces that caller is internal staff with admin role.
    """
    if staff.staff_role != "admin":
        _raise_auth_error(
            status.HTTP_403_FORBIDDEN,
            "Admin role required to perform this action."
        )
    return staff

def get_agent_service(
    actor: Union[CustomerPrincipal, StaffPrincipal, AgentPrincipal] = Depends(get_current_actor),
) -> AgentPrincipal:
    """
    Enforces that caller is the autonomous agent service or authorized staff.
    """
    if isinstance(actor, AgentPrincipal):
        return actor
    if isinstance(actor, StaffPrincipal) and actor.staff_role == "admin":
        return AgentPrincipal(service_name="admin_proxy", scopes=["all"], is_service=True)
    _raise_auth_error(
        status.HTTP_403_FORBIDDEN,
        "Scoped agent service credentials required."
    )
