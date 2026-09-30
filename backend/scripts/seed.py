import sys
import os
from datetime import datetime, timedelta, timezone
import random
import hashlib

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models import (
    Customer, Order, OrderItem, Refund, Cancellation,
    AddressChangeRequest, PasswordResetRequest, Ticket,
    Conversation, ConversationMessage, ToolExecutionLog
)

# ──────────────────────────────────────────────────────────────
# REALISTIC INDIAN NAMES (First + Last)
# ──────────────────────────────────────────────────────────────
INDIAN_FIRST_NAMES_MALE = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh",
    "Ayaan", "Krishna", "Ishaan", "Shaurya", "Atharv", "Advik", "Dhruv",
    "Kabir", "Ritvik", "Aarush", "Kian", "Darsh", "Veer",
    "Rohan", "Rahul", "Amit", "Vikram", "Suresh", "Rajesh", "Manish",
    "Nikhil", "Ankit", "Deepak", "Harsh", "Gaurav", "Siddharth", "Kunal",
    "Akash", "Sahil", "Varun", "Tushar", "Yash", "Omkar",
    "Tanmay", "Shubham", "Swapnil", "Hemant", "Vishal", "Mayur",
    "Rohit", "Sachin", "Karan", "Neeraj",
]

INDIAN_FIRST_NAMES_FEMALE = [
    "Ananya", "Diya", "Myra", "Sara", "Aanya", "Aadhya", "Aarohi",
    "Saanvi", "Anika", "Prisha", "Kavya", "Tara", "Ira", "Navya",
    "Riya", "Meera", "Nisha", "Pooja", "Sneha", "Priya",
    "Neha", "Shruti", "Tanvi", "Swati", "Ankita", "Divya", "Pallavi",
    "Komal", "Shweta", "Sakshi", "Bhavana", "Rutuja", "Vaishnavi",
    "Gauri", "Madhuri", "Sonal", "Manasi", "Renuka", "Jyoti", "Kirti",
    "Aparna", "Deepali", "Smita", "Rashmi", "Revati", "Amruta",
    "Tejal", "Prajakta", "Megha", "Vrushali",
]

INDIAN_LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Joshi",
    "Reddy", "Nair", "Iyer", "Rao", "Das", "Chatterjee", "Banerjee",
    "Mehta", "Shah", "Deshmukh", "Patil", "Kulkarni", "Jain",
    "Pandey", "Mishra", "Tiwari", "Yadav", "Chauhan", "Thakur",
    "Agarwal", "Kapoor", "Malhotra", "Bhatia", "Saxena", "Srivastava",
    "Chopra", "Khanna", "Deshpande", "Gokhale", "Bhosale", "Jadhav",
    "Pawar", "Shinde", "Wagh", "More", "Chavan", "Gaikwad",
    "Pillai", "Menon", "Mukherjee", "Bose", "Sen", "Ghosh",
]

# ──────────────────────────────────────────────────────────────
# REALISTIC INDIAN E-COMMERCE PRODUCTS (Flipkart / Amazon India style)
# ──────────────────────────────────────────────────────────────
PRODUCTS = [
    # Electronics
    ("boAt Rockerz 450 Bluetooth Headphones", 1499.00),
    ("Noise ColorFit Pro 4 Smartwatch", 2999.00),
    ("Fire-Boltt Phoenix Smart Watch", 1899.00),
    ("Samsung Galaxy Buds FE", 4999.00),
    ("Redmi 12 5G (128GB, Moonstone Silver)", 10999.00),
    ("OnePlus Nord Buds 2r", 2299.00),
    ("Realme Narzo 60x 5G (6GB RAM)", 9999.00),
    ("JBL Flip 6 Portable Speaker", 9999.00),
    ("Sony WH-1000XM5 Headphones", 26990.00),
    ("Apple AirPods (3rd Gen)", 14900.00),
    ("Mi Power Bank 3i 20000mAh", 1499.00),
    ("Ambrane 10000mAh Wireless Powerbank", 1299.00),
    ("HP 15s Ryzen 5 Laptop", 38990.00),
    ("Lenovo IdeaPad Slim 3 (i5 12th Gen)", 42990.00),
    ("Logitech MK270r Wireless Keyboard Mouse Combo", 1595.00),

    # Home & Kitchen
    ("Prestige Iris 750W Mixer Grinder", 2849.00),
    ("Pigeon by Stovekraft Favourite IC 1800W Induction", 1399.00),
    ("Milton Thermosteel Flask 1L", 699.00),
    ("Havells Instanio Prime 3L Instant Water Heater", 3590.00),
    ("Bajaj Majesty New SWX 4 Sandwich Toaster", 1499.00),
    ("Borosil 500ml Stainless Steel Water Bottle", 449.00),
    ("Prestige Popular Svachh 5L Pressure Cooker", 1849.00),
    ("Cello Opalware Dazzle Series Dinner Set 35pcs", 1799.00),
    ("Solimo 100% Cotton Bath Towel Set (2 Pack)", 599.00),
    ("Amazon Basics Room Darkening Curtains (2 Pack)", 899.00),

    # Fashion & Accessories
    ("Levi's Men's 511 Slim Fit Jeans", 1799.00),
    ("Allen Solly Men's Polo T-Shirt", 899.00),
    ("Wildcraft 44L Laptop Backpack", 1299.00),
    ("Fastrack Analog Watch for Men", 1495.00),
    ("Puma Men's Running Shoes", 2499.00),
    ("Nike Women's Air Max Shoes", 5495.00),
    ("Titan Raga Women's Watch", 3995.00),
    ("Lavie Women's Handbag", 1299.00),
    ("Woodland Men's Leather Wallet", 895.00),
    ("Ray-Ban Aviator Sunglasses", 5490.00),

    # Books & Stationery
    ("Atomic Habits by James Clear", 399.00),
    ("Ikigai: The Japanese Secret", 299.00),
    ("Rich Dad Poor Dad", 349.00),
    ("The Psychology of Money", 299.00),
    ("Classmate Notebook 6-Subject (Pack of 3)", 249.00),

    # Grocery & Personal Care
    ("Tata Sampann Unpolished Toor Dal 1kg", 159.00),
    ("Fortune Sunlite Refined Sunflower Oil 5L", 649.00),
    ("Surf Excel Matic Front Load Detergent 4kg", 799.00),
    ("Himalaya Neem Face Wash 200ml", 199.00),
    ("Nivea Men's Grooming Kit", 599.00),
    ("Colgate MaxFresh Toothpaste (Pack of 3)", 249.00),
    ("Dettol Liquid Handwash 750ml (Pack of 3)", 299.00),
    ("Dove Shampoo 650ml + Conditioner 180ml Combo", 499.00),
    ("Cadbury Dairy Milk Silk Gift Pack", 599.00),
    ("Paper Boat Aam Panna Juice 1L (Pack of 2)", 199.00),
]

# ──────────────────────────────────────────────────────────────
# REALISTIC INDIAN ADDRESSES
# ──────────────────────────────────────────────────────────────
INDIAN_ADDRESSES = [
    "Flat 302, Shree Residency, Baner Road, Pune, Maharashtra 411045",
    "H. No. 14, Sector 22, Dwarka, New Delhi 110077",
    "302/A, Sagar Apartments, Andheri West, Mumbai, Maharashtra 400058",
    "Plot 45, Jubilee Hills, Road No 10, Hyderabad, Telangana 500033",
    "2nd Floor, 15th Cross, JP Nagar 6th Phase, Bengaluru, Karnataka 560078",
    "B-204, Swagat Rainforest, SG Highway, Ahmedabad, Gujarat 380054",
    "Flat 501, Ganga Tower, Aundh, Pune, Maharashtra 411007",
    "House 88, Gomti Nagar Extension, Lucknow, UP 226010",
    "403, Harmony Heights, Salt Lake Sector V, Kolkata, WB 700091",
    "Flat 12A, Palm Meadows, Whitefield, Bengaluru, Karnataka 560066",
    "G-7, Royal Orchid, Pratap Nagar, Jaipur, Rajasthan 302033",
    "B-302, Lodha Palava, Dombivli East, Thane, Maharashtra 421204",
    "House 5, Shivaji Nagar, Nagpur, Maharashtra 440010",
    "Flat 601, Oberoi Splendor, Jogeshwari East, Mumbai, Maharashtra 400060",
    "27/3, Vasant Kunj Enclave, South Delhi, New Delhi 110070",
    "A-11, Laxmi Nagar, Near Metro Station, East Delhi 110092",
    "Plot 78, IT Park Road, Hinjewadi Phase 2, Pune, Maharashtra 411057",
    "3rd Floor, Sai Complex, Kothrud, Pune, Maharashtra 411038",
    "102, Sapphire Residency, Manikonda, Hyderabad, Telangana 500089",
    "Flat 204, Vrindavan Society, Thane West, Maharashtra 400601",
    "House 33, Civil Lines, Nagpur, Maharashtra 440001",
    "Flat 12, Empress City, Empress Mill Compound, Nagpur, Maharashtra 440018",
    "B-301, Skyline Towers, Wardha Road, Nagpur, Maharashtra 440015",
    "Plot 22, Friends Colony, Manewada Road, Nagpur, Maharashtra 440024",
    "A-5, Laxmi Apartments, Dharampeth, Nagpur, Maharashtra 440010",
    "202, Sai Residency, Ramdaspeth, Nagpur, Maharashtra 440012",
    "House 17, Seminary Hills, Near Law College, Nagpur, Maharashtra 440006",
    "Flat 403, Trimurti Nagar, Near Poonam Chambers, Nagpur, Maharashtra 440022",
    "45/B, Model Town, Jalandhar, Punjab 144003",
    "Flat 9, Green Valley Apartments, Noida Sector 62, UP 201301",
    "D-401, Marathon Nexzone, Panvel, Navi Mumbai, Maharashtra 410206",
    "55, Teachers Colony, Saharanpur Road, Dehradun, Uttarakhand 248001",
]

# ──────────────────────────────────────────────────────────────
# EMAIL DOMAINS COMMON IN INDIA
# ──────────────────────────────────────────────────────────────
EMAIL_DOMAINS = [
    "gmail.com", "gmail.com", "gmail.com", "gmail.com",  # heavily weighted
    "yahoo.co.in", "outlook.com", "hotmail.com", "rediffmail.com",
]

# ──────────────────────────────────────────────────────────────
# REFUND / CANCELLATION / TICKET REASONS (Indian context)
# ──────────────────────────────────────────────────────────────
REFUND_REASONS = [
    "Product received was damaged during shipping.",
    "Wrong item delivered, ordered blue colour but received black.",
    "Item is defective, not working out of the box.",
    "Quality not as shown on website, looks different from images.",
    "Duplicate order placed by mistake, need refund for one.",
    "Size does not fit, product description was misleading.",
    "Received expired grocery product.",
    "Product stopped working within 2 days of delivery.",
    "Missing accessories in the box (charger/cable missing).",
    "Ordered for gifting but delivered late, no longer needed.",
]

CANCEL_REASONS = [
    "Found same product at cheaper price on another site.",
    "Delivery date too far, need it urgently.",
    "Ordered by mistake, wrong product selected.",
    "Changed mind, no longer need this product.",
    "Better variant available, want to reorder.",
    "Duplicate order placed accidentally.",
    "Seller reviews are bad, not trusting the product anymore.",
    "Shipping charges too high for this product.",
    "Payment issue, want to reorder with different method.",
    "Moving to a new city, address will change before delivery.",
]

TICKET_ESCALATION_DATA = [
    {
        "intent": "refund_dispute",
        "escalation_reason": "Customer claims product was damaged on delivery. Delivery partner marked it as successfully delivered. Photos shared as proof.",
        "actions_attempted": {"checked_delivery_status": True, "verified_photos": True, "contacted_seller": True},
        "tool_results": {"delivery_status": "delivered", "damage_claim": True, "seller_response": "pending"}
    },
    {
        "intent": "cancellation_failure",
        "escalation_reason": "Customer requested cancellation but order already dispatched from warehouse. Shipment in transit with Delhivery courier.",
        "actions_attempted": {"fetch_order": True, "attempt_cancel": False, "contacted_courier": True},
        "tool_results": {"order_status": "shipped", "carrier": "Delhivery", "awb": "DL2024789456"}
    },
    {
        "intent": "shipping_delay",
        "escalation_reason": "Package stuck at sorting hub for 5 days. Expected delivery was 3 days ago. Customer threatening to file consumer complaint.",
        "actions_attempted": {"checked_tracking": True, "escalated_to_courier": True},
        "tool_results": {"last_location": "Bhiwandi Sorting Hub, Maharashtra", "days_stuck": 5}
    },
    {
        "intent": "wrong_item_delivered",
        "escalation_reason": "Customer ordered Redmi 12 5G but received a phone cover instead. Requesting immediate replacement or full refund.",
        "actions_attempted": {"verified_order_details": True, "checked_warehouse_logs": True},
        "tool_results": {"ordered_product": "Redmi 12 5G", "delivered_product": "Phone Cover", "warehouse": "Pune Hub"}
    },
    {
        "intent": "payment_issue",
        "escalation_reason": "Customer's UPI payment of ₹10,999 was debited but order shows as payment failed. Bank confirms amount deducted.",
        "actions_attempted": {"checked_payment_gateway": True, "verified_bank_statement": True},
        "tool_results": {"payment_method": "UPI - Google Pay", "txn_id": "GPY240930789012", "status": "amount_debited_order_failed"}
    },
    {
        "intent": "account_security",
        "escalation_reason": "Customer reports unauthorized order placed from their account. Suspects account was compromised. Requesting order cancellation and account lock.",
        "actions_attempted": {"checked_login_history": True, "flagged_account": True},
        "tool_results": {"suspicious_login_ip": "103.45.67.89", "location": "Unknown - VPN detected", "orders_placed": 2}
    },
]

CONVERSATION_TEMPLATES = [
    [
        ("user", "Hi, I placed an order 3 days ago but haven't received any shipping update yet. Can you check?"),
        ("agent", "Sure! Could you please share your Order ID so I can look into this for you?"),
        ("user", "It's Order #{order_id}"),
        ("agent", "Thank you! I can see Order #{order_id} is currently {status}. {detail}"),
    ],
    [
        ("user", "I want to return a product. The quality is not good at all."),
        ("agent", "I'm sorry to hear that! Could you please provide your Order ID and the specific item you'd like to return?"),
        ("user", "Order #{order_id}, the {product} I received looks completely different from the pictures."),
        ("agent", "I understand your frustration. I've initiated a return request for your {product}. Our pickup partner will contact you within 24 hours."),
    ],
    [
        ("user", "Mera order kab aayega? Bahut din ho gaye."),
        ("agent", "Namaste! Aapka Order ID share karein, main abhi check karta/karti hoon."),
        ("user", "Order #{order_id} hai mera"),
        ("agent", "Aapka Order #{order_id} abhi {status} hai. Expected delivery {delivery} tak hai. Koi aur help chahiye?"),
    ],
    [
        ("user", "I need to change the delivery address for my recent order. Is that possible?"),
        ("agent", "Yes, address changes are possible if the order hasn't been shipped yet. Let me check your order status."),
        ("user", "It's Order #{order_id}. I need it delivered to a different flat number."),
        ("agent", "I see that your order is still in '{status}' status. I've updated the delivery address as requested!"),
    ],
    [
        ("user", "Can you cancel my order? I found the same thing cheaper on Flipkart."),
        ("agent", "I understand! Please share your Order ID and I'll process the cancellation right away."),
        ("user", "#{order_id}"),
        ("agent", "Order #{order_id} has been cancelled successfully. Your refund of ₹{amount} will be credited within 5-7 business days."),
    ],
]


def generate_email(first_name, last_name):
    """Generate a realistic Indian-style email address."""
    patterns = [
        f"{first_name.lower()}.{last_name.lower()}",
        f"{first_name.lower()}{last_name.lower()[:3]}",
        f"{first_name.lower()}_{last_name.lower()}",
        f"{first_name.lower()}{random.randint(10, 99)}",
        f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 9)}",
        f"{first_name.lower()}{random.choice(['_', '.'])}{last_name.lower()}{random.randint(1, 99)}",
    ]
    email_local = random.choice(patterns)
    domain = random.choice(EMAIL_DOMAINS)
    return f"{email_local}@{domain}"


def seed_database():
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.db.base_class import Base

    print(f"Connecting to database: {settings.SQLALCHEMY_DATABASE_URI}")
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)

    # Create all tables if they don't exist
    import app.models
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        now = datetime.now(timezone.utc)

        # ──────────────────────────────────────────────────────
        # 0. CLEAR ALL EXISTING DATA (fresh start)
        # ──────────────────────────────────────────────────────
        print("Clearing existing data...")
        for table_name in [
            "tool_execution_logs", "conversation_messages", "conversations",
            "tickets", "password_reset_requests", "address_change_requests",
            "cancellations", "refunds", "order_items", "orders", "customers"
        ]:
            session.execute(text(f"DELETE FROM {table_name}"))
        session.commit()
        print("[OK] All tables cleared.")

        # ──────────────────────────────────────────────────────
        # 1. SEED CUSTOMERS (5 team members + 95 generated = 100)
        # ──────────────────────────────────────────────────────
        team_members = [
            ("Pushkar Sawarkar", "pushkarsawarkar22@gmail.com"),
            ("Ashlesha Varghane", "ashleshavarghane@gmail.com"),
            ("Pranav Tapdiya", "pranavtapdiya@gmail.com"),
            ("Pushpak Bajanghate", "pushpakbajanghate09@gmail.com"),
            ("Prathmesh Rathod", "prathameshrathod@gmail.com"),
        ]

        customer_data = list(team_members)
        used_emails = {email for _, email in team_members}
        used_names = {name for name, _ in team_members}

        # Generate 95 more unique Indian customers
        while len(customer_data) < 100:
            is_female = random.random() < 0.45
            if is_female:
                first = random.choice(INDIAN_FIRST_NAMES_FEMALE)
            else:
                first = random.choice(INDIAN_FIRST_NAMES_MALE)
            last = random.choice(INDIAN_LAST_NAMES)
            full_name = f"{first} {last}"

            if full_name in used_names:
                continue

            email = generate_email(first, last)
            if email in used_emails:
                continue

            used_names.add(full_name)
            used_emails.add(email)
            customer_data.append((full_name, email))

        customers = []
        for name, email in customer_data:
            cust = Customer(name=name, email=email)
            session.add(cust)
            customers.append(cust)

        session.commit()
        print(f"✅ Seeded {len(customers)} customers (5 team + {len(customers) - 5} generated Indian names)")

        # ──────────────────────────────────────────────────────
        # 2. SEED ORDERS & ORDER ITEMS (200+ orders)
        # ──────────────────────────────────────────────────────
        statuses = ["placed", "shipped", "delivered", "cancelled"]
        status_weights = [0.25, 0.20, 0.40, 0.15]  # most orders delivered
        orders = []

        for i in range(250):
            customer = random.choice(customers)
            status = random.choices(statuses, weights=status_weights, k=1)[0]

            days_ago = random.randint(1, 90)
            order_date = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            delivery_days = random.randint(2, 7)
            expected_delivery = order_date + timedelta(days=delivery_days)

            is_editable = status == "placed" and days_ago <= 30

            order = Order(
                customer=customer,
                status=status,
                order_date=order_date,
                expected_delivery=expected_delivery,
                total_amount=0.0,
                is_editable=is_editable
            )
            session.add(order)

            # 1-4 unique items per order (no duplicate products in same order)
            num_items = random.choices([1, 2, 3, 4], weights=[0.40, 0.35, 0.18, 0.07], k=1)[0]
            selected_products = random.sample(PRODUCTS, num_items)  # sample guarantees uniqueness

            total = 0.0
            used_product_names = set()
            for prod_name, price in selected_products:
                if prod_name in used_product_names:
                    continue  # skip duplicate (safety guard)
                used_product_names.add(prod_name)
                qty = random.choices([1, 2, 3], weights=[0.70, 0.25, 0.05], k=1)[0]
                item = OrderItem(
                    order=order,
                    product_name=prod_name,
                    quantity=qty,
                    price=price
                )
                session.add(item)
                total += float(price) * qty

            order.total_amount = round(total, 2)
            orders.append(order)

        session.commit()
        print(f"✅ Seeded {len(orders)} orders with order items")

        # ──────────────────────────────────────────────────────
        # 3. SEED REFUNDS (15-20 refunds)
        # ──────────────────────────────────────────────────────
        eligible_for_refund = [o for o in orders if o.status in ["cancelled", "delivered"]]
        random.shuffle(eligible_for_refund)
        refund_statuses = ["requested", "approved", "processed", "rejected"]
        refund_status_weights = [0.20, 0.30, 0.35, 0.15]
        refunds_count = 0

        for order in eligible_for_refund[:18]:
            # Full or partial refund
            if random.random() < 0.7:
                refund_amount = float(order.total_amount)
            else:
                refund_amount = round(float(order.total_amount) * random.uniform(0.3, 0.8), 2)

            refund = Refund(
                order=order,
                amount=refund_amount,
                reason=random.choice(REFUND_REASONS),
                status=random.choices(refund_statuses, weights=refund_status_weights, k=1)[0]
            )
            session.add(refund)
            refunds_count += 1

        session.commit()
        print(f"✅ Seeded {refunds_count} refund records")

        # ──────────────────────────────────────────────────────
        # 4. SEED CANCELLATIONS (10-15 cancellations)
        # ──────────────────────────────────────────────────────
        cancelled_orders = [o for o in orders if o.status == "cancelled"]
        random.shuffle(cancelled_orders)
        cancellation_statuses = ["approved", "requested", "rejected"]
        cancellation_weights = [0.60, 0.25, 0.15]
        cancellations_count = 0

        for order in cancelled_orders[:12]:
            cancellation = Cancellation(
                order=order,
                reason=random.choice(CANCEL_REASONS),
                status=random.choices(cancellation_statuses, weights=cancellation_weights, k=1)[0]
            )
            session.add(cancellation)
            cancellations_count += 1

        session.commit()
        print(f"✅ Seeded {cancellations_count} cancellation records")

        # ──────────────────────────────────────────────────────
        # 5. SEED ADDRESS CHANGE REQUESTS (10 requests)
        # ──────────────────────────────────────────────────────
        address_statuses = ["pending", "completed", "rejected"]
        address_weights = [0.30, 0.55, 0.15]
        address_requests_count = 0

        for i in range(10):
            customer = random.choice(customers)
            active_order = next((o for o in customer.orders if o.status == "placed"), None)

            addr_req = AddressChangeRequest(
                customer=customer,
                order=active_order,
                new_address=random.choice(INDIAN_ADDRESSES),
                status=random.choices(address_statuses, weights=address_weights, k=1)[0]
            )
            session.add(addr_req)
            address_requests_count += 1

        session.commit()
        print(f"✅ Seeded {address_requests_count} address change requests")

        # ──────────────────────────────────────────────────────
        # 6. SEED PASSWORD RESET REQUESTS
        # ──────────────────────────────────────────────────────
        pw_statuses = ["pending", "used", "expired"]
        pw_weights = [0.20, 0.50, 0.30]
        pw_requests_count = 0

        for i in range(8):
            customer = random.choice(customers)
            token_hash = hashlib.sha256(f"reset_{customer.email}_{random.randint(100000, 999999)}".encode()).hexdigest()[:40]
            pw_req = PasswordResetRequest(
                customer=customer,
                token=token_hash,
                status=random.choices(pw_statuses, weights=pw_weights, k=1)[0]
            )
            session.add(pw_req)
            pw_requests_count += 1

        session.commit()
        print(f"✅ Seeded {pw_requests_count} password reset requests")

        # ──────────────────────────────────────────────────────
        # 7. SEED TICKETS / ESCALATIONS (6 tickets)
        # ──────────────────────────────────────────────────────
        ticket_statuses = ["open", "in_progress", "resolved", "closed"]
        ticket_weights = [0.25, 0.25, 0.30, 0.20]
        tickets = []

        for td in TICKET_ESCALATION_DATA:
            customer = random.choice(customers)
            ticket = Ticket(
                customer=customer,
                channel=random.choice(["chat", "voice"]),
                intent=td["intent"],
                actions_attempted=td["actions_attempted"],
                tool_results=td["tool_results"],
                escalation_reason=td["escalation_reason"],
                status=random.choices(ticket_statuses, weights=ticket_weights, k=1)[0]
            )
            session.add(ticket)
            tickets.append(ticket)

        session.commit()
        print(f"✅ Seeded {len(tickets)} support tickets/escalations")

        # ──────────────────────────────────────────────────────
        # 8. SEED CONVERSATIONS & MESSAGES (15 conversations)
        # ──────────────────────────────────────────────────────
        convs_count = 0
        msgs_count = 0

        for i in range(15):
            customer = random.choice(customers)
            conv = Conversation(
                customer=customer,
                channel=random.choice(["chat", "voice"]),
                status=random.choice(["active", "completed", "completed"])  # mostly completed
            )
            session.add(conv)
            session.commit()
            session.refresh(conv)
            convs_count += 1

            # Pick a random conversation template and fill in real data
            template = random.choice(CONVERSATION_TEMPLATES)
            cust_orders = customer.orders
            if cust_orders:
                sample_order = random.choice(cust_orders)
                order_id = sample_order.id
                status = sample_order.status
                amount = f"{sample_order.total_amount:,.2f}"
                delivery = sample_order.expected_delivery.strftime("%d %b %Y") if sample_order.expected_delivery else "soon"
                items = sample_order.items
                product = items[0].product_name if items else "your product"
                detail = {
                    "placed": "Your order is being prepared and will be shipped soon.",
                    "shipped": "It's on its way! You should receive it by the expected delivery date.",
                    "delivered": "This order has been delivered. Let me know if there's an issue.",
                    "cancelled": "This order was cancelled. Would you like to reorder?",
                }.get(status, "Let me check on this for you.")
            else:
                order_id = random.randint(1, 250)
                status = "placed"
                amount = "999.00"
                delivery = "soon"
                product = "your product"
                detail = "Let me look into this."

            for sender, text in template:
                msg_text = (text
                    .replace("{order_id}", str(order_id))
                    .replace("{status}", status)
                    .replace("{amount}", amount)
                    .replace("{delivery}", delivery)
                    .replace("{product}", product)
                    .replace("{detail}", detail)
                )
                msg = ConversationMessage(
                    conversation=conv,
                    sender=sender,
                    message_text=msg_text
                )
                session.add(msg)
                msgs_count += 1

        session.commit()
        print(f"✅ Seeded {convs_count} conversations with {msgs_count} messages")

        # ──────────────────────────────────────────────────────
        # 9. SEED TOOL EXECUTION LOGS
        # ──────────────────────────────────────────────────────
        tool_names = [
            "fetch_customer_by_email", "fetch_order_by_id",
            "initiate_refund", "cancel_order_by_id",
            "track_shipment", "update_delivery_address",
            "check_payment_status", "escalate_to_human_agent"
        ]
        tools_count = 0

        for i in range(20):
            ticket = random.choice(tickets) if tickets else None
            tool_name = random.choice(tool_names)

            log = ToolExecutionLog(
                conversation=None,
                ticket=ticket,
                tool_name=tool_name,
                arguments={"query_param": f"param_{random.randint(1000, 9999)}"},
                result={"status": random.choice(["success", "success", "error"]), "rows_modified": random.randint(0, 3)}
            )
            session.add(log)
            tools_count += 1

        session.commit()
        print(f"✅ Seeded {tools_count} tool execution logs")

        # ──────────────────────────────────────────────────────
        # SUMMARY
        # ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  🎉 ALL INDIAN E-COMMERCE DATA SEEDED SUCCESSFULLY!")
        print("=" * 60)
        print(f"  👤 Customers:              {len(customers)}")
        print(f"  📦 Orders:                 {len(orders)}")
        print(f"  💰 Refunds:                {refunds_count}")
        print(f"  ❌ Cancellations:           {cancellations_count}")
        print(f"  📍 Address Changes:        {address_requests_count}")
        print(f"  🔐 Password Resets:        {pw_requests_count}")
        print(f"  🎫 Support Tickets:        {len(tickets)}")
        print(f"  💬 Conversations:          {convs_count}")
        print(f"  📝 Messages:               {msgs_count}")
        print(f"  🔧 Tool Logs:              {tools_count}")
        print("=" * 60)

    except Exception as e:
        session.rollback()
        print(f"❌ An error occurred while seeding the database: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
