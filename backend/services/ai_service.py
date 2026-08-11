import json
import os
import re
from backend.schemas import ExtractedTransaction

SYSTEM_PROMPT = "Extract one khata transaction. Return JSON only: customer_name, amount, item, transaction_type (credit or payment), date optional, confidence, explanation. Credit is udhaar given; payment is money received. Never invent financial details."

def _fallback(text: str) -> ExtractedTransaction:
    """Deliberately limited development parser; it is not an AI replacement."""
    lowered = text.lower()
    amount_match = re.search(r"(?:₹|rs\.?|rupaye?|rupees?)?\s*(\d[\d,]*(?:\.\d+)?)", lowered)
    if not amount_match:
        raise ValueError("I could not find an amount. Please edit the details before confirming.")
    amount = float(amount_match.group(1).replace(",", ""))
    payment_words = ("payment", "paid", "diya", "jama", "vasool", "received")
    kind = "payment" if any(word in lowered for word in payment_words) and "udhaar" not in lowered else "credit"
    name_match = re.search(r"^\s*([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)\s+(?:ko|ne|from|paid|gave)", text, re.I)
    name = name_match.group(1).strip().title() if name_match else "Customer to confirm"
    item_match = re.search(r"(?:ka|for|item)\s+([a-zA-Z\u0900-\u097F][\w\s-]{1,40}?)(?:\s+(?:udhaar|diya|paid|payment)|[.!]|$)", text, re.I)
    item = item_match.group(1).strip() if item_match else ("Payment" if kind == "payment" else "Goods")
    return ExtractedTransaction(customer_name=name, amount=amount, item=item, transaction_type=kind, confidence=0.55, explanation="Development fallback parser used because OPENAI_API_KEY is not configured.")

def _openai_extract(text: str) -> ExtractedTransaction:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}], response_format={"type": "json_object"}, temperature=0)
    return ExtractedTransaction.model_validate(json.loads(response.choices[0].message.content or "{}"))

def extract_transaction(text: str) -> ExtractedTransaction:
    if os.getenv("OPENAI_API_KEY"):
        try:
            return _openai_extract(text)
        except Exception as exc:
            raise ValueError(f"AI extraction is unavailable: {exc}") from exc
    return _fallback(text)
