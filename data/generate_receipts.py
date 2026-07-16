"""
Generates a small set of synthetic receipt PDFs so the agent has real
files to open, parse, and act on. Includes one deliberately messy receipt
to exercise the agent's error-recovery path.
"""
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5

OUT_DIR = os.path.join(os.path.dirname(__file__), "receipts")
os.makedirs(OUT_DIR, exist_ok=True)

RECEIPTS = [
    {
        "file": "receipt_cafe.pdf",
        "vendor": "Third Wave Coffee",
        "date": "2026-07-02",
        "amount": "487.00",
        "category": "Food & Beverage",
        "gst": "18%",
    },
    {
        "file": "receipt_travel.pdf",
        "vendor": "Ola Cabs",
        "date": "2026-07-05",
        "amount": "612.50",
        "category": "Travel",
        "gst": "5%",
    },
    {
        "file": "receipt_saas.pdf",
        "vendor": "Notion Labs Inc.",
        "date": "2026-07-08",
        "amount": "1499.00",
        "category": "Software",
        "gst": "18%",
    },
    {
        # deliberately malformed: no clear "Total" label, smudged formatting
        "file": "receipt_ambiguous.pdf",
        "vendor": "Unknown Stationery Shop",
        "date": "??/07/2026",
        "amount": "",       # missing amount -> forces agent to flag for confirmation
        "category": "",
        "gst": "",
    },
]


def make_receipt(info):
    path = os.path.join(OUT_DIR, info["file"])
    c = canvas.Canvas(path, pagesize=A5)
    w, h = A5
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, h - 40, info["vendor"] if info["vendor"] else "RECEIPT")
    c.setFont("Helvetica", 10)
    y = h - 70
    if info["date"]:
        c.drawString(30, y, f"Date: {info['date']}")
        y -= 18
    if info["amount"]:
        c.drawString(30, y, f"Total Amount: Rs. {info['amount']}")
        y -= 18
    else:
        # simulate a badly printed receipt with no clear total
        c.drawString(30, y, "misc items ......... qty 3")
        y -= 18
        c.drawString(30, y, "(thermal print faded)")
        y -= 18
    if info["gst"]:
        c.drawString(30, y, f"GST: {info['gst']}")
        y -= 18
    c.drawString(30, y - 10, "Thank you for your purchase.")
    c.save()
    return path


if __name__ == "__main__":
    for r in RECEIPTS:
        p = make_receipt(r)
        print("created", p)
