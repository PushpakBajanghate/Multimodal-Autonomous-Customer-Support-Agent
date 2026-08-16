import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db
import app.db.session as session_module
from app.models import (
    Customer, Order, OrderItem, Refund, Cancellation,
    AddressChangeRequest, PasswordResetRequest, Ticket,
    Conversation, ConversationMessage, ToolExecutionLog
)

# In-memory SQLite engine shared across connections in test process
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Patch module level immediately upon import
session_module.SessionLocal = TestingSessionLocal
session_module.engine = test_engine


def seed_test_data(db):
    now = datetime.now(timezone.utc)

    # 1. Seed Customers (15 customers)
    customers = []
    customer_data = [
        ("Alice Smith", "alice.smith@example.com"),
        ("Bob Jones", "bob.jones@example.com"),
        ("Charlie Brown", "charlie.brown@example.com"),
        ("Diana Prince", "diana.prince@example.com"),
        ("Evan Wright", "evan.wright@example.com"),
        ("Fiona Gallagher", "fiona.g@example.com"),
        ("George Clark", "george.clark@example.com"),
        ("Hannah Abbott", "hannah.a@example.com"),
        ("Ian Malcolm", "ian.malcolm@example.com"),
        ("Julia Roberts", "julia.r@example.com"),
        ("Kevin Bacon", "kevin.bacon@example.com"),
        ("Laura Croft", "laura.croft@example.com"),
        ("Michael Scott", "michael.scott@example.com"),
        ("Nancy Drew", "nancy.drew@example.com"),
        ("Oscar Martinez", "oscar.m@example.com"),
    ]
    for name, email in customer_data:
        c = Customer(name=name, email=email)
        db.add(c)
        customers.append(c)
    db.commit()
    for c in customers:
        db.refresh(c)

    c1 = customers[0]
    c2 = customers[1]

    # 2. Seed deterministic orders for Customer 1
    orders = [
        # Order 1: Placed, recent, editable
        Order(customer_id=c1.id, status="placed", order_date=now - timedelta(days=2), expected_delivery=now + timedelta(days=3), total_amount=129.99, is_editable=True),
        # Order 2: Delivered, recent (<= 30 days), refundable
        Order(customer_id=c1.id, status="delivered", order_date=now - timedelta(days=5), expected_delivery=now - timedelta(days=2), total_amount=89.99, is_editable=False),
        # Order 3: Shipped, not cancellable
        Order(customer_id=c1.id, status="shipped", order_date=now - timedelta(days=3), expected_delivery=now + timedelta(days=2), total_amount=249.99, is_editable=False),
        # Order 4: Cancelled
        Order(customer_id=c1.id, status="cancelled", order_date=now - timedelta(days=10), expected_delivery=now - timedelta(days=7), total_amount=45.00, is_editable=False),
        # Order 5: Old delivered (> 30 days, not refundable)
        Order(customer_id=c1.id, status="delivered", order_date=now - timedelta(days=45), expected_delivery=now - timedelta(days=40), total_amount=199.99, is_editable=False),
        # Order 6: Placed, Customer 2
        Order(customer_id=c2.id, status="placed", order_date=now - timedelta(days=1), expected_delivery=now + timedelta(days=4), total_amount=59.99, is_editable=True),
        # Order 7: Shipped, Customer 2
        Order(customer_id=c2.id, status="shipped", order_date=now - timedelta(days=4), expected_delivery=now + timedelta(days=1), total_amount=79.99, is_editable=False),
        # Order 8: Delivered, Customer 2
        Order(customer_id=c2.id, status="delivered", order_date=now - timedelta(days=7), expected_delivery=now - timedelta(days=3), total_amount=99.99, is_editable=False),
        # Order 9: Placed for Customer 1 (required by test_chat_endpoints)
        Order(customer_id=c1.id, status="placed", order_date=now - timedelta(days=1), expected_delivery=now + timedelta(days=2), total_amount=149.99, is_editable=True),
        # Order 10: Delivered for Customer 1
        Order(customer_id=c1.id, status="delivered", order_date=now - timedelta(days=8), expected_delivery=now - timedelta(days=4), total_amount=69.99, is_editable=False),
    ]
    db.add_all(orders)
    db.commit()

    # Add Order Items
    for o in orders:
        item = OrderItem(order_id=o.id, product_name="Test Product Item", quantity=1, price=o.total_amount)
        db.add(item)
    db.commit()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    session_module.SessionLocal = TestingSessionLocal
    session_module.engine = test_engine

    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    try:
        seed_test_data(db)
    finally:
        db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
