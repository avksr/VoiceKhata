from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from backend.database import get_db
from backend.models import Customer, Transaction
from backend.schemas import ReportSummary, TransactionOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


def total(db: Session, transaction_type: str, start: datetime | None = None) -> float:
    query = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.transaction_type == transaction_type
    )
    if start:
        query = query.filter(Transaction.created_at >= start)
    return float(query.scalar() or 0)


@router.get("/summary", response_model=ReportSummary)
def summary(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sales = total(db, "credit", today)
    weekly = total(db, "credit", today - timedelta(days=6))
    payments = total(db, "payment")

    outstanding = float(
        db.query(func.coalesce(func.sum(Customer.outstanding_balance), 0)).scalar() or 0
    )
    recent = (
        db.query(Transaction)
        .options(joinedload(Transaction.customer))
        .order_by(Transaction.created_at.desc())
        .limit(8)
        .all()
    )

    daily_sales = []
    for days_ago in range(6, -1, -1):
        day = today - timedelta(days=days_ago)
        next_day = day + timedelta(days=1)
        daily_sales.append(total(db, "credit", day) - total(db, "credit", next_day))

    recent_transactions = [
        TransactionOut.model_validate({**tx.__dict__, "customer_name": tx.customer.name})
        for tx in recent
    ]
    return ReportSummary(
        today_sales=sales,
        weekly_sales=weekly,
        outstanding_credit=outstanding,
        total_payments=payments,
        total_customers=db.query(Customer).count(),
        daily_sales=daily_sales,
        recent_transactions=recent_transactions,
    )
