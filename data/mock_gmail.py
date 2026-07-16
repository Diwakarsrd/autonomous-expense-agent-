"""
Mock Gmail inbox.

Real Gmail integration requires OAuth credentials (credentials.json) and the
google-api-python-client library. To let this project run immediately with
zero setup, this module exposes the SAME method signatures a real Gmail
client wrapper would (search_messages, get_attachment, send_email) but backed
by an in-memory inbox.

Swap this module for `agent/gmail_client.py` (real API) without touching the
planner or tool logic — that's the point of the adapter pattern here.
"""
import os
import glob
import time

RECEIPTS_DIR = os.path.join(os.path.dirname(__file__), "receipts")

_INBOX = [
    {
        "id": "msg_001",
        "from": "receipts@thirdwavecoffee.in",
        "subject": "Your receipt from Third Wave Coffee",
        "snippet": "Thank you for your order. Amount charged Rs 487.00",
        "attachment": "receipt_cafe.pdf",
        "date": "2026-07-02",
    },
    {
        "id": "msg_002",
        "from": "no-reply@olacabs.com",
        "subject": "Your Ola ride invoice",
        "snippet": "Your trip invoice is attached.",
        "attachment": "receipt_travel.pdf",
        "date": "2026-07-05",
    },
    {
        "id": "msg_003",
        "from": "billing@notion.so",
        "subject": "Your Notion Plus receipt",
        "snippet": "Payment received for Notion Plus subscription.",
        "attachment": "receipt_saas.pdf",
        "date": "2026-07-08",
    },
    {
        "id": "msg_004",
        "from": "noreply@stationeryshop.example",
        "subject": "Purchase confirmation",
        "snippet": "Thanks for shopping with us.",
        "attachment": "receipt_ambiguous.pdf",
        "date": "2026-07-09",
    },
    # noise the agent must correctly IGNORE
    {
        "id": "msg_005",
        "from": "newsletter@techcrunch.com",
        "subject": "Today's top stories",
        "snippet": "Here is your daily digest of tech news...",
        "attachment": None,
        "date": "2026-07-09",
    },
    {
        "id": "msg_006",
        "from": "friend@gmail.com",
        "subject": "Lunch this weekend?",
        "snippet": "Are you free on Saturday?",
        "attachment": None,
        "date": "2026-07-10",
    },
]

_SENT_LOG = []


def search_messages(query: str = "has:attachment receipt OR invoice"):
    """Simulates Gmail search. Returns messages that look like receipts."""
    time.sleep(0.2)  # simulate network latency, like a real API call
    keywords = ["receipt", "invoice", "payment", "purchase", "order", "billing"]
    results = []
    for m in _INBOX:
        text = f"{m['subject']} {m['snippet']} {m['from']}".lower()
        if any(k in text for k in keywords):
            results.append(m)
    return results


def get_attachment_path(message_id: str):
    time.sleep(0.1)
    for m in _INBOX:
        if m["id"] == message_id and m["attachment"]:
            path = os.path.join(RECEIPTS_DIR, m["attachment"])
            if os.path.exists(path):
                return path
    return None


def send_email(to: str, subject: str, body: str):
    """Simulates sending a confirmation email."""
    time.sleep(0.15)
    entry = {"to": to, "subject": subject, "body": body}
    _SENT_LOG.append(entry)
    return {"status": "sent", **entry}


def get_sent_log():
    return list(_SENT_LOG)
