from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    status: str  # "success" or "failure"
    reason: Optional[str] = None
    data: Optional[T] = None
