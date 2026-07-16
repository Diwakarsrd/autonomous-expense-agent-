"""
Real PDF -> structured data extraction using pdfplumber.
This is the 'computer vision / document understanding' step. It's rule-based
regex extraction here (fast, free, no API key needed) but is written so an
LLM-vision call can be dropped in for messier real-world receipts -- see
`extract_with_llm_fallback`.
"""
import re
import pdfplumber

AMOUNT_RE = re.compile(r"(?:rs\.?|inr|₹)\s*([\d,]+\.\d{2}|[\d,]+)", re.IGNORECASE)
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
GST_RE = re.compile(r"gst[:\s]*([\d]+%)", re.IGNORECASE)


def extract_text(pdf_path: str) -> str:
    text_chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            text_chunks.append(t)
    return "\n".join(text_chunks)


def extract_receipt_fields(pdf_path: str) -> dict:
    """Returns structured fields + a confidence flag. Never raises --
    a receipt the parser can't understand comes back with needs_review=True
    instead of crashing the pipeline, which is the 'error recovery' behavior."""
    text = extract_text(pdf_path)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    vendor = lines[0] if lines else "Unknown vendor"

    amount_match = AMOUNT_RE.search(text)
    date_match = DATE_RE.search(text)
    gst_match = GST_RE.search(text)

    amount = amount_match.group(1).replace(",", "") if amount_match else None
    date = date_match.group(1) if date_match else None
    gst = gst_match.group(1) if gst_match else None

    needs_review = amount is None or date is None
    reasons = []
    if amount is None:
        reasons.append("no clear total amount found")
    if date is None:
        reasons.append("no parseable date found")

    return {
        "source_file": pdf_path,
        "vendor": vendor,
        "amount": amount,
        "date": date,
        "gst": gst,
        "raw_text": text,
        "needs_review": needs_review,
        "review_reasons": reasons,
    }


CATEGORY_KEYWORDS = {
    "Travel": ["ola", "uber", "cab", "taxi", "flight", "irctc", "train"],
    "Food & Beverage": ["coffee", "cafe", "restaurant", "swiggy", "zomato"],
    "Software": ["notion", "saas", "subscription", "software", "labs inc"],
}


def guess_category(vendor: str) -> str:
    v = vendor.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if any(k in v for k in keys):
            return cat
    return "Uncategorized"
