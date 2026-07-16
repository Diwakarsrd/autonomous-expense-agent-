# Autonomous Expense Report Agent

![Python](https://img.shields.io/badge/python-3.12-blue)
![Playwright](https://img.shields.io/badge/browser--automation-Playwright-2EAD33)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![Status](https://img.shields.io/badge/status-working%20demo-brightgreen)

A computer-using agent that finds expense receipts in an inbox, reads them,
files them in an internal expense system through a **real browser session**,
and confirms back to the user — with explicit error recovery for receipts it
can't confidently parse.

## Why this project

It maps directly onto a fintech company's actual back office (expense
processing) and demonstrates, in one small runnable repo:

- **Browser automation / computer use** — a real headless Chromium session
  (Playwright) fills and submits a real HTML form on a real running server.
  Nothing here is mocked at the browser layer.
- **Document understanding** — real PDF parsing (`pdfplumber`) with
  regex-based field extraction, structured to be swapped for an LLM-vision
  call on messier real-world receipts.
- **Multi-step planning** — an explicit, inspectable state machine
  (`agent/planner.py`) rather than one opaque model call. Every decision is
  logged to `logs/run_log.jsonl`.
- **Error recovery** — a receipt with no parseable amount or date is
  **flagged for human review, never guessed**. Financial data doesn't get
  invented. Browser submission also retries on transient failure before
  giving up.
- **Tool calling** — Gmail search/attachment/send are exposed as a clean
  adapter interface (`data/mock_gmail.py`) so the mock inbox can be replaced
  by the real Gmail API without touching planner or browser code.

## What's real vs. mocked

| Component | Status |
|---|---|
| PDF generation of sample receipts | Real (reportlab) |
| PDF text extraction | Real (pdfplumber) |
| Field parsing + validation | Real (regex + confidence flagging) |
| Internal "expense portal" web app | Real (FastAPI + uvicorn, actually running) |
| Browser automation filling the form | Real (Playwright + headless Chromium) |
| Gmail inbox | **Mocked** — no OAuth setup needed to run this. Adapter-shaped so swapping in the real Gmail API is a drop-in replacement (see below). |
| Sending confirmation email | **Mocked** — logged to an in-memory sent list, same reason as above. |
| Planning "intelligence" | Rule-based state machine. An LLM call can replace the `decide_*` logic without touching the tool contracts — see below. |

Being upfront about this split is deliberate: an interviewer will ask what's
real, and "here's exactly what's real, here's exactly what's mocked and why,
here's the adapter boundary where I'd swap it" is a stronger answer than
pretending everything is production-grade.

## Run it

```bash
pip install -r requirements.txt
playwright install chromium
python3 main.py
```

This will:
1. Generate 4 sample receipt PDFs (3 clean, 1 deliberately ambiguous)
2. Start the real internal expense portal at `http://127.0.0.1:8811`
3. Run the agent: search inbox → download attachment → extract fields →
   validate → fill + submit via real browser automation → send confirmation
   → flag the ambiguous one instead of guessing
4. Print a summary and point you to the full trace

Check the results:
```bash
cat logs/run_log.jsonl              # full structured agent trace
cat form_app/submitted_expenses.json # what actually got filed
ls form_app/uploads/                 # receipt files the "portal" received
```

## Architecture

```
main.py
 ├─ data/generate_receipts.py   real PDF generation (sample data)
 ├─ data/mock_gmail.py          inbox adapter (swap for real Gmail API)
 ├─ form_app/server.py          real FastAPI app = the "internal system"
 └─ agent/
     ├─ planner.py              orchestration loop + structured trace log
     ├─ extract.py              real PDF parsing + validation
     └─ browser_tool.py         real Playwright automation + retry logic
```

## Swapping in the real Gmail API

Replace `data/mock_gmail.py` with a module exposing the same three
functions (`search_messages`, `get_attachment_path`, `send_email`), backed by
`google-api-python-client` and OAuth credentials. `agent/planner.py` doesn't
change at all — it only calls the adapter interface.

## Swapping in a real LLM for planning/extraction

- **Extraction**: for receipts too messy for regex (handwritten, foreign
  language, heavily stylized), replace `extract_receipt_fields` with a
  vision-capable model call (Claude or GPT-4o) that returns the same JSON
  shape, keeping `needs_review` as a hard gate on top of the model's own
  confidence.
- **Planning**: the `run_expense_agent` loop's per-step decisions could be
  handed to an LLM with function-calling instead of hardcoded branches — the
  tool signatures in `browser_tool.py` and `mock_gmail.py` are already
  shaped as clean callable tools, so this is a relatively small change.

## Extending this for the CRED-flavored pitch (Finance Assistant)

This expense agent is intentionally the smallest complete slice of the
larger "Autonomous Finance Assistant" idea. The natural next slices, in
order of effort:
1. Categorization + a spending dashboard over `submitted_expenses.json`
2. A persistent memory layer (e.g. remembers recurring vendors/categories
   across runs, stored in SQLite instead of the flat JSON file)
3. A second computer-use skill (e.g. downloading bank statements from a
   banking portal) reusing the same `browser_tool.py` pattern
