import re
import unicodedata
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Customer
from backend.schemas import ExtractedTransaction, VoiceAnswerRequest, VoiceTextRequest

router = APIRouter(prefix="/api/voice", tags=["voice"])

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
DEVANAGARI_MAP = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "ा": "a", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ं": "n", "ँ": "n", "ः": "h", "्": "", "़": "",
}
CONSONANTS = set("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह")


def _repair_mojibake(text: str) -> str:
    """Accept UTF-8 Hindi that a browser/client has accidentally decoded as Latin-1."""
    text = text or ""
    if any(marker in text for marker in ("à", "â", "ð")):
        try:
            repaired = text.encode("latin-1").decode("utf-8")
            if repaired:
                return repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return text


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", _repair_mojibake(text)).translate(DEVANAGARI_DIGITS)
    text = text.replace("₹", " rupees ").replace("₨", " rupees ")
    text = re.sub(r"[\"'“”]", "", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _transliterate(text: str) -> str:
    text = _normalise(text).replace("क्ष", "ksh").replace("त्र", "tr").replace("ज्ञ", "gy")
    result = []
    for char in text:
        result.append(DEVANAGARI_MAP.get(char, char))
    return re.sub(r"\s+", " ", "".join(result)).strip()


def _forms(text: str) -> set[str]:
    original, latin = _normalise(text), _transliterate(text)
    values = {value for value in (original, latin) if value}
    return values | {value.replace(" ", "") for value in values}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z\u0900-\u097F]+", text)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def _spoken_name(text: str) -> str | None:
    # Names are deliberately only taken from the beginning, before the action/amount.
    match = re.match(
        r"^\s*([A-Za-z\u0900-\u097F][A-Za-z\u0900-\u097F .'-]{0,58}?)\s+"
        r"(?:ne|ने|ko|को|borrowed|borrow|paid|pay|gave|took|bought|liya|liye|li|लिया|लिए|ली|rupees?|rupaye|rs\.?|\d)",
        _normalise(text), re.IGNORECASE,
    )
    if not match:
        return None
    name = match.group(1).strip(" .-'")
    return name.title() if re.fullmatch(r"[A-Za-z .'-]+", name) else name


def _match_customer(spoken: str | None, customers: list[Customer]) -> Customer | None:
    if not spoken:
        return None
    spoken_forms = _forms(spoken)
    # Exact full-name or first-name matching is safe and handles Ramesh -> Ramesh Kumar.
    exact = []
    for customer in customers:
        customer_forms = _forms(customer.name)
        first_forms = _forms(customer.name.split()[0])
        if spoken_forms & customer_forms or spoken_forms & first_forms:
            exact.append(customer)
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None

    spoken_tokens = _words(_normalise(spoken)) + _words(_transliterate(spoken))
    scores = []
    for customer in customers:
        parts = customer.name.split()
        score = max((_similarity(form, word) for part in parts for form in _forms(part) for word in spoken_tokens if len(form) >= 3 and len(word) >= 3), default=0)
        scores.append((score, customer))
    scores.sort(key=lambda row: row[0], reverse=True)
    if scores and scores[0][0] >= 0.88 and (len(scores) == 1 or scores[0][0] - scores[1][0] >= 0.12):
        return scores[0][1]
    return None


def _extract_amount(text: str) -> float | None:
    value = _normalise(text)
    patterns = [
        r"(?:rupees?|rs\.?|inr)\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
        r"\b([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:rupees?|rupaye|rupay)\b",
        r"\b([0-9]+(?:\.[0-9]+)?)\s*(k|thousand)\b",
        r"\b([0-9][0-9,]*(?:\.[0-9]+)?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(",", ""))
            if len(match.groups()) > 1 and match.group(2) in {"k", "thousand"}:
                amount *= 1000
            return amount if amount > 0 else None
    return None


def _extract_type(text: str) -> str:
    value = _normalise(text)
    payment = ("paid", "payment", "pay ", "gave", "received", "jama", "chuka", "चुक", "भुगतान", "दिए", "दिया", "दे दिया")
    credit = ("borrow", "udhaar", "udhar", "credit", "owes", "due", "on credit", "उधार", "कर्ज", "लिया", "लिए")
    if any(word in value for word in payment):
        return "payment"
    return "credit" if any(word in value for word in credit) else "credit"


def _extract_item(text: str, transaction_type: str) -> str:
    value = _normalise(text)
    if transaction_type == "payment":
        return "Payment"
    # "5000 rupaye ka samaan udhaar" / "goods worth 5000".
    match = re.search(r"(?:rupees?|rupaye)\s+(?:ka|ki|ke)\s+(.+?)\s+(?:udhaar|udhar|credit|लिया|लिए)", value)
    if match:
        item = match.group(1).strip(" .")
        if item:
            return item.title()
    if re.search(r"\b(goods?|samaan|saman|सामान)\b", value):
        return "Goods"
    return "Goods"


@router.post("/extract", response_model=ExtractedTransaction)
def extract_transaction(payload: VoiceTextRequest, db: Session = Depends(get_db)):
    text = payload.transcription.strip()
    amount = _extract_amount(text)
    spoken_name = _spoken_name(text)
    if amount is None:
        raise HTTPException(422, "I could not identify the amount. Try saying 'Ramesh borrowed 5000 rupees'.")
    if not spoken_name:
        raise HTTPException(422, "I could not identify the customer name. Please say the customer's name clearly.")
    matched = _match_customer(spoken_name, db.query(Customer).all())
    customer_name = matched.name if matched else spoken_name
    transaction_type = _extract_type(text)
    explanation = f'Heard: "{_repair_mojibake(text)}". Detected {customer_name}, ₹{amount:,.0f}, {"credit / udhaar" if transaction_type == "credit" else "payment received"}.'
    if not matched:
        explanation += " No existing customer was confidently matched; add or select the customer before saving."
    return ExtractedTransaction(customer_name=customer_name, amount=amount, item=_extract_item(text, transaction_type), transaction_type=transaction_type, confidence=0.9 if matched else 0.7, explanation=explanation)


@router.post("/query")
def voice_query(payload: VoiceAnswerRequest, db: Session = Depends(get_db)):
    question = payload.question.strip()
    if not question:
        raise HTTPException(422, "Please ask a question.")
    spoken = _spoken_name(question)
    # Question wording rarely uses 'ne'; find a customer from safe exact/fuzzy token matching instead.
    customers = db.query(Customer).all()
    matched = _match_customer(spoken, customers) if spoken else None
    if not matched:
        words = _words(_normalise(question)) + _words(_transliterate(question))
        candidates = []
        for customer in customers:
            best = max((_similarity(form, word) for part in customer.name.split() for form in _forms(part) for word in words if len(form) >= 3 and len(word) >= 3), default=0)
            if best >= 0.88:
                candidates.append((best, customer))
        candidates.sort(key=lambda item: item[0], reverse=True)
        if candidates and (len(candidates) == 1 or candidates[0][0] - candidates[1][0] >= 0.12):
            matched = candidates[0][1]
    if not matched:
        return {"answer": "I could not find that customer in your khata."}
    return {"answer": f"{matched.name} ka outstanding balance ₹{matched.outstanding_balance:,.0f} hai."}
