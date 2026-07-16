"""
Run the full Autonomous Expense Report Agent end to end.

    python3 main.py

What happens:
  1. Generates 4 sample receipt PDFs (3 clean, 1 deliberately ambiguous)
  2. Starts the real internal 'expense portal' web app (FastAPI + uvicorn)
  3. Runs the agent: searches the (mock) inbox, downloads attachments,
     extracts fields from real PDFs, drives a real headless Chromium
     browser to fill and submit the expense form, sends a confirmation
     email, and flags the one ambiguous receipt for human review instead
     of guessing.
  4. Prints a summary + where to find the full structured trace log.
"""
import os
import sys
import time
import threading
import uvicorn

sys.path.append(os.path.dirname(__file__))

from data.generate_receipts import RECEIPTS, make_receipt
from agent.planner import run_expense_agent
from form_app.server import app as form_app

HOST, PORT = "127.0.0.1", 8811
BASE_URL = f"http://{HOST}:{PORT}/"


def start_server():
    config = uvicorn.Config(form_app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def wait_for_server(url, timeout=10):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    print("=" * 70)
    print("STEP 0: generating sample receipts")
    print("=" * 70)
    for r in RECEIPTS:
        path = make_receipt(r)
        print("  created:", path)

    print("\n" + "=" * 70)
    print("STEP 0b: starting internal expense portal (real FastAPI server)")
    print("=" * 70)
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    if not wait_for_server(BASE_URL):
        print("ERROR: expense portal did not start in time.")
        return
    print(f"  portal live at {BASE_URL}")

    print("\n" + "=" * 70)
    print("STEP 1-6: running the agent")
    print("=" * 70)
    results = run_expense_agent(BASE_URL)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for r in results:
        print(f"  [{r['status'].upper():>12}] message {r['message_id']}")

    print("\nFull structured trace: logs/run_log.jsonl")
    print("Filed expenses (server-side record): form_app/submitted_expenses.json")
    print("Uploaded receipt copies:              form_app/uploads/")


if __name__ == "__main__":
    main()
