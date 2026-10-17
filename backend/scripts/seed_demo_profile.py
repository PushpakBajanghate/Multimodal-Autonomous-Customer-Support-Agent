"""Idempotently seed the Pushpak Bajanghate demo profile and 10 varied orders."""

from datetime import datetime, timedelta, timezone

from app.core.security import get_password_hash
from app.db.session import SessionLocal, init_db
from app.models import Cancellation, Customer, Order, OrderItem, Ticket

EMAIL = "pushpakbajanghate09@gmail.com"
DEMO_PREFIX = "Aura Demo"

DEMO_ORDERS = [
    ("placed", 2499.00, "Aura Demo Noise Cancelling Headphones", True),
    ("placed", 5999.00, "Aura Demo Smart Watch", True),
    ("delivered", 14999.00, "Aura Demo 4K Monitor", False),
    ("delivered", 22000.00, "Aura Demo Premium Tablet", False),
    ("delivered", 32000.00, "Aura Demo Flagship Smartphone", False),
    ("shipped", 12999.00, "Aura Demo Gaming Keyboard", False),
    ("delivered", 8999.00, "Aura Demo Robot Vacuum", False),
    ("cancelled", 4999.00, "Aura Demo Air Fryer", False),
    ("placed", 18999.00, "Aura Demo Laptop Backpack Bundle", True),
    ("delivered", 28000.00, "Aura Demo Mirrorless Camera", False),
]


def seed_demo_profile() -> None:
    init_db()
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.email == EMAIL).first()
        if not customer:
            customer = Customer(
                name="Pushpak Bajanghate",
                email=EMAIL,
                password_hash=get_password_hash("password123"),
            )
            db.add(customer)
            db.flush()
        else:
            customer.name = "Pushpak Bajanghate"

        existing = (
            db.query(Order)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .filter(Order.customer_id == customer.id, OrderItem.product_name.like(f"{DEMO_PREFIX}%"))
            .all()
        )
        existing_names = {item.product_name for order in existing for item in order.items}
        now = datetime.now(timezone.utc)
        created = []

        for index, (status, amount, product, editable) in enumerate(DEMO_ORDERS, start=1):
            if product in existing_names:
                continue
            order = Order(
                customer_id=customer.id,
                status=status,
                order_date=now - timedelta(days=2 + index),
                expected_delivery=now + timedelta(days=max(1, 7 - index)),
                total_amount=amount,
                is_editable=editable,
            )
            db.add(order)
            db.flush()
            db.add(OrderItem(order_id=order.id, product_name=product, quantity=1, price=amount))
            created.append(order)

            if status == "cancelled":
                db.add(Cancellation(
                    order_id=order.id,
                    reason="Customer changed their mind before dispatch",
                    status="approved",
                ))

            if amount > 25000:
                db.add(Ticket(
                    customer_id=customer.id,
                    channel="chat",
                    intent="high_value_refund_approval",
                    actions_attempted={"order_id": order.id, "refund_amount": amount},
                    tool_results={"status": "awaiting_human_approval"},
                    escalation_reason=f"Demo approval queue: refund for Order #{order.id} is ₹{amount:,.2f}.",
                    status="open",
                ))

        db.commit()
        print(f"Demo profile ready: {customer.name} ({customer.email}); added {len(created)} orders.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_profile()
