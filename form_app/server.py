"""
A tiny real 'internal expense portal'. This stands in for whatever internal
tool (SAP Concur, an internal CRED tool, etc.) the agent would need to
operate via the browser in production. It's a real running web server with
a real HTML <form>, so Playwright is doing genuine browser automation
against it -- not a simulation.
"""
import json
import os
import shutil
from datetime import datetime
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse

APP_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")
DB_PATH = os.path.join(APP_DIR, "submitted_expenses.json")
os.makedirs(UPLOAD_DIR, exist_ok=True)
if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f:
        json.dump([], f)

app = FastAPI(title="Internal Expense Portal (demo)")

FORM_HTML = """
<!DOCTYPE html>
<html>
<head><title>Expense Submission</title></head>
<body>
<h2>New Expense Report</h2>
<form action="/submit" method="post" enctype="multipart/form-data" id="expense-form">
  <label>Vendor</label><br>
  <input type="text" name="vendor" id="vendor"><br><br>
  <label>Date</label><br>
  <input type="text" name="date" id="date"><br><br>
  <label>Amount (INR)</label><br>
  <input type="text" name="amount" id="amount"><br><br>
  <label>Category</label><br>
  <input type="text" name="category" id="category"><br><br>
  <label>Receipt file</label><br>
  <input type="file" name="receipt" id="receipt"><br><br>
  <button type="submit" id="submit-btn">Submit Expense</button>
</form>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return FORM_HTML


@app.post("/submit")
async def submit(
    vendor: str = Form(...),
    date: str = Form(...),
    amount: str = Form(...),
    category: str = Form(...),
    receipt: UploadFile = File(...),
):
    saved_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{receipt.filename}"
    dest = os.path.join(UPLOAD_DIR, saved_name)
    with open(dest, "wb") as out:
        shutil.copyfileobj(receipt.file, out)

    with open(DB_PATH, "r") as f:
        records = json.load(f)
    record = {
        "vendor": vendor,
        "date": date,
        "amount": amount,
        "category": category,
        "receipt_file": saved_name,
        "submitted_at": datetime.now().isoformat(),
    }
    records.append(record)
    with open(DB_PATH, "w") as f:
        json.dump(records, f, indent=2)

    return JSONResponse({"status": "ok", "record": record})


@app.get("/expenses")
def list_expenses():
    with open(DB_PATH, "r") as f:
        return json.load(f)
