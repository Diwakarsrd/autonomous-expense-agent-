"""
The orchestration core.

This is written as an explicit state machine rather than a single opaque
LLM call, so every decision the 'agent' makes is inspectable -- which is
exactly what you want to be able to explain in an interview. An optional
LLM call (see `plan_step_with_llm`) can replace the rule-based `decide_*`
functions without changing the tool-calling contract.

Pipeline per email:
  search inbox -> download attachment -> extract fields -> validate
  -> (if ambiguous: flag for human confirmation instead of guessing)
  -> fill + submit expense form via real browser automation
  -> send confirmation email
  -> log outcome
"""
import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data import mock_gmail
from agent.extract import extract_receipt_fields, guess_category
from agent.browser_tool import submit_expense_via_browser

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "run_log.jsonl")


class AgentTrace:
    """Tiny structured logger so the run produces an inspectable trace,
    the same way you'd want observability on a real production agent."""

    def __init__(self, path=LOG_PATH):
        self.path = path
        self.events = []
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()

    def log(self, step: str, detail: dict):
        entry = {"ts": datetime.now().isoformat(), "step": step, **detail}
        self.events.append(entry)
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"[{entry['ts'].split('T')[1][:8]}] {step:<22} {json.dumps(detail, default=str)}")


def run_expense_agent(form_base_url: str, user_email: str = "intern@example.com"):
    trace = AgentTrace()
    trace.log("PLAN", {"goal": "Find expense receipts in inbox, file expense reports, confirm to user"})

    # Step 1: search
    messages = mock_gmail.search_messages()
    trace.log("TOOL_CALL:search_messages", {"found": len(messages), "ids": [m["id"] for m in messages]})

    results = []
    for m in messages:
        trace.log("STEP", {"processing_message": m["id"], "subject": m["subject"]})

        # Step 2: download attachment
        if not m["attachment"]:
            trace.log("SKIP", {"message": m["id"], "reason": "no attachment"})
            continue
        attach_path = mock_gmail.get_attachment_path(m["id"])
        trace.log("TOOL_CALL:get_attachment_path", {"message": m["id"], "path": attach_path})

        # Step 3: extract fields (real PDF parsing)
        fields = extract_receipt_fields(attach_path)
        trace.log("TOOL_CALL:extract_receipt_fields", {
            "vendor": fields["vendor"], "amount": fields["amount"],
            "date": fields["date"], "needs_review": fields["needs_review"],
        })

        # Step 4: validation / error-recovery branch
        if fields["needs_review"]:
            trace.log("ERROR_RECOVERY", {
                "message": m["id"],
                "action": "flagged_for_human_confirmation",
                "reasons": fields["review_reasons"],
            })
            results.append({
                "message_id": m["id"], "status": "needs_review",
                "reasons": fields["review_reasons"], "extracted": fields,
            })
            continue  # do NOT guess a financial figure -- ask instead

        category = guess_category(fields["vendor"])

        record = {
            "vendor": fields["vendor"],
            "date": fields["date"],
            "amount": fields["amount"],
            "category": category,
            "receipt_path": attach_path,
        }

        # Step 5: real browser automation to file the expense
        trace.log("TOOL_CALL:submit_expense_via_browser", {"record": {k: v for k, v in record.items() if k != "receipt_path"}})
        submit_result = submit_expense_via_browser(form_base_url, record)
        trace.log("TOOL_RESULT:submit_expense_via_browser", submit_result)

        if not submit_result["success"]:
            trace.log("ERROR_RECOVERY", {"message": m["id"], "action": "gave_up_after_retries", "error": submit_result["error"]})
            results.append({"message_id": m["id"], "status": "failed", "error": submit_result["error"]})
            continue

        # Step 6: confirmation email
        email_result = mock_gmail.send_email(
            to=user_email,
            subject=f"Expense filed: {fields['vendor']} - Rs {fields['amount']}",
            body=(
                f"Filed expense for {fields['vendor']} dated {fields['date']} "
                f"for Rs {fields['amount']} under category '{category}'."
            ),
        )
        trace.log("TOOL_CALL:send_email", email_result)

        results.append({"message_id": m["id"], "status": "filed", "record": record})

    trace.log("DONE", {"total_processed": len(messages), "filed": sum(1 for r in results if r["status"] == "filed"),
                        "needs_review": sum(1 for r in results if r["status"] == "needs_review"),
                        "failed": sum(1 for r in results if r["status"] == "failed")})
    return results
