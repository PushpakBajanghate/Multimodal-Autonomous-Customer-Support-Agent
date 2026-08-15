import sys
import os
from datetime import datetime, timedelta
import random
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

def seed_database():
    print(f"Connecting to database: {settings.SQLALCHEMY_DATABASE_URI}")
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Seed Customers (15 customers)
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

        customers = []
        for name, email in customer_data:
            cust = Customer(name=name, email=email)
            session.add(cust)
            customers.append(cust)

        session.commit()
        print(f"Seeded {len(customers)} customers.")

        # 2. Setup Products for Orders
        products = [
            ("Wireless Headphones", 89.99),
            ("Mechanical Keyboard", 129.99),
            ("Ergonomic Office Chair", 249.99),
            ("USB-C Hub Multiport Adapter", 34.50),
            ("Smart Watch v4", 199.99),
            ("Leather Wallet", 45.00),
            ("Portable Bluetooth Speaker", 59.99),
            ("Stainless Steel Water Bottle", 25.00),
            ("Yoga Mat Premium", 39.99),
            ("Laptop Stand Adjustable", 29.99)
        ]

        # 3. Seed Orders & Order Items (at least 40 orders)
        statuses = ["placed", "shipped", "delivered", "cancelled"]
        orders = []

        base_date = datetime.utcnow()

        for i in range(45):
            customer = random.choice(customers)
            status = random.choice(statuses)
            
            # Days calculation for realistic history
            days_ago = random.randint(1, 60)
            order_date = base_date - timedelta(days=days_ago)
            expected_delivery = order_date + timedelta(days=random.randint(2, 5))
            
            is_editable = True
            if status in ["shipped", "delivered", "cancelled"] or days_ago > 30:
                is_editable = False

            # Add Order
            order = Order(
                customer=customer,
                status=status,
                order_date=order_date,
                expected_delivery=expected_delivery,
                total_amount=0.0,  # calculated below
                is_editable=is_editable
            )
            session.add(order)
            
            # Add OrderItems (1 to 3 items per order)
            num_items = random.randint(1, 3)
            selected_products = random.sample(products, num_items)
            
            total = 0.0
            for prod_name, price in selected_products:
                qty = random.randint(1, 2)
                item = OrderItem(
                    order=order,
                    product_name=prod_name,
                    quantity=qty,
                    price=price
                )
                session.add(item)
                total += float(price) * qty
            
            order.total_amount = total
            orders.append(order)

        session.commit()
        print(f"Seeded {len(orders)} orders and their respective order items.")

        # 4. Seed Refunds (at least 5 refunds)
        # Select some cancelled or delivered orders to refund
        eligible_for_refund = [o for o in orders if o.status in ["cancelled", "delivered"]]
        refund_reasons = [
            "Defective product out of box.",
            "Order cancelled by customer before dispatch.",
            "Incorrect item delivered.",
            "Returned within 30-day window.",
            "Accidental double order."
        ]

        refund_statuses = ["requested", "approved", "processed", "rejected"]
        refunds_count = 0

        for order in eligible_for_refund[:8]:
            refund = Refund(
                order=order,
                amount=order.total_amount,
                reason=random.choice(refund_reasons),
                status=random.choice(refund_statuses)
            )
            session.add(refund)
            refunds_count += 1

        session.commit()
        print(f"Seeded {refunds_count} refund records.")

        # 5. Seed Cancellations (at least 5 cancellations)
        cancelled_orders = [o for o in orders if o.status == "cancelled"]
        cancel_reasons = [
            "Changed mind about the color.",
            "Found a better deal elsewhere.",
            "Shipping takes too long.",
            "Ordered by mistake.",
            "Customer support request processed cancellation."
        ]

        cancellation_statuses = ["approved", "requested", "rejected"]
        cancellations_count = 0

        for order in cancelled_orders[:7]:
            cancellation = Cancellation(
                order=order,
                reason=random.choice(cancel_reasons),
                status=random.choice(cancellation_statuses)
            )
            session.add(cancellation)
            cancellations_count += 1

        session.commit()
        print(f"Seeded {cancellations_count} cancellation records.")

        # 6. Seed Address Change Requests (at least 5 requests)
        address_statuses = ["pending", "completed", "rejected"]
        new_addresses = [
            "123 Maple St, Apt 4B, Boston, MA 02111",
            "456 Oak Rd, San Francisco, CA 94102",
            "789 Pine Ave, Seattle, WA 98101",
            "101 Cedar Blvd, Austin, TX 78701",
            "202 Elm Ln, Chicago, IL 60601"
        ]

        address_requests_count = 0
        for i in range(6):
            customer = random.choice(customers)
            # Find an active order if any, otherwise set to None
            active_order = next((o for o in customer.orders if o.status == "placed"), None)
            
            addr_req = AddressChangeRequest(
                customer=customer,
                order=active_order,
                new_address=new_addresses[i % len(new_addresses)],
                status=random.choice(address_statuses)
            )
            session.add(addr_req)
            address_requests_count += 1

        session.commit()
        print(f"Seeded {address_requests_count} address change requests.")

        # 7. Seed Password Reset Requests
        pw_statuses = ["pending", "used", "expired"]
        pw_requests_count = 0
        for i in range(5):
            customer = random.choice(customers)
            pw_req = PasswordResetRequest(
                customer=customer,
                token=f"token_reset_hash_{random.randint(100000, 999999)}",
                status=random.choice(pw_statuses)
            )
            session.add(pw_req)
            pw_requests_count += 1

        session.commit()
        print(f"Seeded {pw_requests_count} password reset requests.")

        # 8. Seed Tickets (Escalations) (at least 3 tickets)
        ticket_intents = ["refund_dispute", "cancellation_failure", "shipping_delay"]
        ticket_statuses = ["open", "in_progress", "resolved", "closed"]
        
        ticket_data = [
            {
                "intent": "refund_dispute",
                "escalation_reason": "Customer demands refund for item delivered 35 days ago (outside 30-day limit). Needs manager override.",
                "actions_attempted": {"checked_order_status": True, "validated_delivery_date": True},
                "tool_results": {"delivery_days_ago": 35, "policy_refund_window": 30}
            },
            {
                "intent": "cancellation_failure",
                "escalation_reason": "Customer tried to cancel order but it already transitioned to 'shipped' status in shipping pipeline.",
                "actions_attempted": {"fetch_order": True, "attempt_cancel": False},
                "tool_results": {"order_status": "shipped", "carrier": "FedEx"}
            },
            {
                "intent": "shipping_delay",
                "escalation_reason": "Package is 3 days past delivery expected date. Tracker shows stuck in sorting facility.",
                "actions_attempted": {"checked_courier_tracker": True},
                "tool_results": {"last_update": "Stuck in Sort Facility - Dallas TX"}
            }
        ]

        tickets = []
        for td in ticket_data:
            customer = random.choice(customers)
            ticket = Ticket(
                customer=customer,
                channel=random.choice(["chat", "voice"]),
                intent=td["intent"],
                actions_attempted=td["actions_attempted"],
                tool_results=td["tool_results"],
                escalation_reason=td["escalation_reason"],
                status=random.choice(ticket_statuses)
            )
            session.add(ticket)
            tickets.append(ticket)

        session.commit()
        print(f"Seeded {len(tickets)} support tickets/escalations.")

        # 9. Seed Conversations & Messages
        convs_count = 0
        msgs_count = 0
        for i in range(10):
            customer = random.choice(customers)
            conv = Conversation(
                customer=customer,
                channel=random.choice(["chat", "voice"]),
                status=random.choice(["active", "completed"])
            )
            session.add(conv)
            convs_count += 1
            
            # Seed 2-4 messages per conversation
            for j in range(random.randint(2, 4)):
                sender = "user" if j % 2 == 0 else "agent"
                msg = ConversationMessage(
                    conversation=conv,
                    sender=sender,
                    message_text=f"Sample message {j+1} from {sender}."
                )
                session.add(msg)
                msgs_count += 1

        session.commit()
        print(f"Seeded {convs_count} conversations and {msgs_count} conversation messages.")

        # 10. Seed Tool Execution Logs
        tool_names = ["fetch_customer_by_email", "fetch_order_by_id", "initiate_refund", "cancel_order_by_id"]
        tools_count = 0
        for i in range(12):
            ticket = random.choice(tickets)
            log = ToolExecutionLog(
                conversation=None,
                ticket=ticket,
                tool_name=random.choice(tool_names),
                arguments={"query_param": "test_arg"},
                result={"status": "success", "rows_modified": 1}
            )
            session.add(log)
            tools_count += 1

        session.commit()
        print(f"Seeded {tools_count} tool execution logs.")

        print("\nAll mock data seeded successfully!")

    except Exception as e:
        session.rollback()
        print(f"An error occurred while seeding the database: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
