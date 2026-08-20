import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.base_class import Base

logger = logging.getLogger("aura.db")


def create_resilient_engine():
    db_uri = settings.SQLALCHEMY_DATABASE_URI
    connect_args = {}

    if db_uri.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        return create_engine(db_uri, connect_args=connect_args)

    try:
        test_engine = create_engine(db_uri, pool_pre_ping=True)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Connected successfully to PostgreSQL database ({settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}).")
        return test_engine
    except Exception as exc:
        logger.warning(
            f"PostgreSQL connection to {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} failed ({exc}). "
            "Falling back to local SQLite database (sqlite:///./macs.db)."
        )
        sqlite_uri = "sqlite:///./macs.db"
        fallback_engine = create_engine(sqlite_uri, connect_args={"check_same_thread": False})
        return fallback_engine


engine = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Ensures database tables are created and essential seed records exist."""
    import app.models  # Register all models with Base metadata
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        from app.models.models import Customer, Order, OrderItem
        if db.query(Customer).count() == 0:
            logger.info("Database is unseeded. Automatically seeding base customers and orders...")
            now = datetime.now(timezone.utc)

            c1 = Customer(name="Alice Smith", email="alice.smith@example.com")
            c2 = Customer(name="Bob Jones", email="bob.jones@example.com")
            c3 = Customer(name="Charlie Brown", email="charlie.brown@example.com")
            db.add_all([c1, c2, c3])
            db.commit()
            db.refresh(c1)
            db.refresh(c2)

            orders = [
                Order(customer_id=c1.id, status="placed", order_date=now - timedelta(days=2), expected_delivery=now + timedelta(days=3), total_amount=129.99, is_editable=True),
                Order(customer_id=c1.id, status="delivered", order_date=now - timedelta(days=5), expected_delivery=now - timedelta(days=2), total_amount=89.99, is_editable=False),
                Order(customer_id=c1.id, status="shipped", order_date=now - timedelta(days=3), expected_delivery=now + timedelta(days=2), total_amount=249.99, is_editable=False),
                Order(customer_id=c2.id, status="placed", order_date=now - timedelta(days=1), expected_delivery=now + timedelta(days=4), total_amount=59.99, is_editable=True),
                Order(customer_id=c2.id, status="delivered", order_date=now - timedelta(days=8), expected_delivery=now - timedelta(days=4), total_amount=99.99, is_editable=False),
            ]
            db.add_all(orders)
            db.commit()
            for o in orders:
                db.add(OrderItem(order_id=o.id, product_name="Premium Product Item", quantity=1, price=o.total_amount))
            db.commit()
            logger.info("Database base records seeded successfully.")
    except Exception as e:
        logger.warning(f"Notice during auto-seeding of database: {e}")
        db.rollback()
    finally:
        db.close()
