from fastapi import APIRouter
from app.api.v1.endpoints import auth, customers, orders, tickets, analytics, chat

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

