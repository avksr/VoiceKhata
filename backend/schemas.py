from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=6, max_length=20)

class CustomerOut(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    outstanding_balance: float
    created_at: datetime

class TransactionCreate(BaseModel):
    customer_id: int
    amount: float = Field(gt=0, le=10_000_000)
    item: str = Field(min_length=1, max_length=160)
    transaction_type: Literal["credit", "payment"]
    description: Optional[str] = Field(default=None, max_length=1000)

class TransactionOut(TransactionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    customer_name: Optional[str] = None

class VoiceTextRequest(BaseModel):
    transcription: str = Field(min_length=3, max_length=1000)

class ExtractedTransaction(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    amount: float = Field(gt=0)
    item: str = Field(min_length=1, max_length=160)
    transaction_type: Literal["credit", "payment"]
    date: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    explanation: Optional[str] = None

class VoiceAnswerRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)

class ReportSummary(BaseModel):
    today_sales: float
    weekly_sales: float
    outstanding_credit: float
    total_payments: float
    total_customers: int
    recent_transactions: list[TransactionOut]
    daily_sales: list[float]
