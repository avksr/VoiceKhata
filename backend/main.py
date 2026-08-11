from datetime import datetime, timedelta
from backend.routes.routes import transactions
from backend.routes.routes import customers, reports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from backend.database import Base, SessionLocal, engine
from backend.models import Customer, Transaction
from backend.routes.routes import voice

load_dotenv()

app = FastAPI(title="VoiceKhata API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers.router)
app.include_router(transactions.router)
app.include_router(reports.router)
app.include_router(voice.router)


def seed() -> None:
    """Add a small sample ledger only when the local database is empty."""
    db = SessionLocal()
    try:
        if db.query(Customer).count():
            return

        ramesh = Customer(name="Ramesh Kumar", phone="9876543210", outstanding_balance=1200)
        sunita = Customer(name="Sunita Devi", phone="9876543211", outstanding_balance=650)
        imran = Customer(name="Imran Khan", phone="9876543212", outstanding_balance=-900)
        db.add_all([ramesh, sunita, imran])
        db.flush()

        db.add_all(
            [
                Transaction(customer_id=ramesh.id, amount=1200, item="Groceries", transaction_type="credit", description="Seed example", created_at=datetime.utcnow()),
                Transaction(customer_id=sunita.id, amount=1500, item="Household supplies", transaction_type="credit", description="Seed example", created_at=datetime.utcnow() - timedelta(days=2)),
                Transaction(customer_id=sunita.id, amount=850, item="Payment", transaction_type="payment", description="Seed example", created_at=datetime.utcnow() - timedelta(days=1)),
                Transaction(customer_id=imran.id, amount=900, item="Payment", transaction_type="payment", description="Seed example", created_at=datetime.utcnow()),
            ]
        )
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
