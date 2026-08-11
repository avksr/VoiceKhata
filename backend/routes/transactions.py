from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from backend.database import get_db
from backend.models import Customer, Transaction
from backend.schemas import TransactionCreate, TransactionOut

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def output(tx: Transaction) -> TransactionOut:
    customer_name = tx.customer.name if tx.customer else None
    return TransactionOut.model_validate({**tx.__dict__, "customer_name": customer_name})


@router.get("", response_model=list[TransactionOut])
def list_transactions(db: Session = Depends(get_db)):
    rows = (
        db.query(Transaction)
        .options(joinedload(Transaction.customer))
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return [output(tx) for tx in rows]


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found.")

    tx = Transaction(**payload.model_dump())
    balance_change = payload.amount if payload.transaction_type == "credit" else -payload.amount
    customer.outstanding_balance += balance_change

    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(customer)
    tx.customer = customer
    return output(tx)
