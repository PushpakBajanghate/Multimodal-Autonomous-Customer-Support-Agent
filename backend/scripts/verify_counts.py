import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models import (
    Customer, Order, OrderItem, Refund, Cancellation,
    AddressChangeRequest, PasswordResetRequest, Ticket,
    Conversation, ConversationMessage, ToolExecutionLog
)

def print_row_counts():
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    models = [
        Customer, Order, OrderItem, Refund, Cancellation,
        AddressChangeRequest, PasswordResetRequest, Ticket,
        Conversation, ConversationMessage, ToolExecutionLog
    ]

    print("=========================================")
    print("      POSTGRESQL TABLE ROW COUNTS        ")
    print("=========================================")
    for model in models:
        count = session.query(model).count()
        print(f"| {model.__tablename__:<25} | {count:>3} rows |")
    print("=========================================")

if __name__ == "__main__":
    print_row_counts()
