"""
Real browser-automation tool. Drives an actual headless Chromium session
against the running form_app server -- this is the 'computer-using agent'
piece (as opposed to just calling a REST endpoint directly, which would be
easier but wouldn't demonstrate browser-level tool use).
"""
from playwright.sync_api import sync_playwright


def submit_expense_via_browser(base_url: str, record: dict, retries: int = 2) -> dict:
    """
    record: {vendor, date, amount, category, receipt_path}
    Fills the real HTML form field-by-field, uploads the receipt file,
    clicks submit, and reads back the JSON confirmation the server renders.
    Retries on transient failure (simulating real-world flakiness handling).
    """
    last_error = None
    for attempt in range(1, retries + 2):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(base_url, wait_until="domcontentloaded")

                page.fill("#vendor", str(record["vendor"]))
                page.fill("#date", str(record["date"]))
                page.fill("#amount", str(record["amount"]))
                page.fill("#category", str(record["category"]))
                page.set_input_files("#receipt", record["receipt_path"])

                with page.expect_response(lambda r: "/submit" in r.url) as resp_info:
                    page.click("#submit-btn")
                response = resp_info.value
                body = response.json()

                browser.close()
                return {"attempt": attempt, "success": True, "server_response": body}
        except Exception as e:
            last_error = str(e)
            continue

    return {"attempt": attempt, "success": False, "error": last_error}
