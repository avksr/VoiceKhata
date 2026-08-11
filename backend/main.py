
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.database import Base, SessionLocal, engine
from backend.models import Customer, Transaction
from backend.routes.routes import customers, reports, transactions, voice


load_dotenv()


app = FastAPI(
    title="VoiceKhata API",
    version="0.1.0"
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local frontend
        "http://127.0.0.1:5500",
        "http://localhost:5500",

        # Local backend
        "http://127.0.0.1:8000",
        "http://localhost:8000",

        # Deployed frontend
        "https://voicekhata-frontend-jjtk.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Routes
# --------------------------------------------------

app.include_router(customers.router)
app.include_router(transactions.router)
app.include_router(reports.router)
app.include_router(voice.router)


# --------------------------------------------------
# Seed sample data
# --------------------------------------------------

def seed() -> None:
    """Add sample ledger data only when the database is empty."""

    db = SessionLocal()

    try:
        # Don't add sample data if customers already exist
        if db.query(Customer).count():
            return

        ramesh = Customer(
            name="Ramesh Kumar",
            phone="9876543210",
            outstanding_balance=1200
        )

        sunita = Customer(
            name="Sunita Devi",
            phone="9876543211",
            outstanding_balance=650
        )

        imran = Customer(
            name="Imran Khan",
            phone="9876543212",
            outstanding_balance=-900
        )

        db.add_all([
            ramesh,
            sunita,
            imran
        ])

        db.flush()

        db.add_all([
            Transaction(
                customer_id=ramesh.id,
                amount=1200,
                item="Groceries",
                transaction_type="credit",
                description="Seed example",
                created_at=datetime.utcnow()
            ),

            Transaction(
                customer_id=sunita.id,
                amount=1500,
                item="Household supplies",
                transaction_type="credit",
                description="Seed example",
                created_at=datetime.utcnow() - timedelta(days=2)
            ),

            Transaction(
                customer_id=sunita.id,
                amount=850,
                item="Payment",
                transaction_type="payment",
                description="Seed example",
                created_at=datetime.utcnow() - timedelta(days=1)
            ),

            Transaction(
                customer_id=imran.id,
                amount=900,
                item="Payment",
                transaction_type="payment",
                description="Seed example",
                created_at=datetime.utcnow()
            ),
        ])

        db.commit()

    finally:
        db.close()


# --------------------------------------------------
# Startup
# --------------------------------------------------

@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed()


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok"
    }
