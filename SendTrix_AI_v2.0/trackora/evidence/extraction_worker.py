"""
screenshot_analysis.py

Takes the raw text already extracted by your OCR pipeline (extract.py +
EasyOCR) and identifies:
    1. The application version shown
    2. The PC's system clock timestamp shown (taskbar time, not any other
       date that might appear in the application content itself)
    3. Whether that timestamp looks "fresh" compared to when the
       screenshot was actually submitted to you

Uses LOCAL Ollama, not a cloud API - since this text is derived from real
screenshots, it should not leave your machine. Requires Ollama running
locally with a model pulled (e.g. llama3.2:3b, which you've already tested).
"""

import json
import requests
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"  # change if you're using a different local model

EXTRACTION_PROMPT_TEMPLATE = """You are given raw OCR text extracted from a
screenshot. The screenshot shows a software application along with the PC's
system clock (usually visible in a taskbar, corner of the screen, or similar).
OCR text is often messy - split across lines out of order, with extra
symbols, misread characters, or duplicated fragments. Read through all of
it before deciding.

Your job:
1. Identify the PRIMARY APPLICATION being assessed for compliance.
 
IMPORTANT:
 
- Ignore Windows applications such as:
  - Remote Desktop Connection
  - File Explorer
  - Windows Explorer
  - Microsoft Edge
  - Google Chrome
  - Command Prompt
  - PowerShell
  - Windows taskbar
 
- If the screenshot is taken inside a Remote Desktop session, identify the application running INSIDE the remote machine, not "Remote Desktop Connection".
 
- Prefer the application that has nearby labels such as:
  Product Version
  Version
  Build
  Release
  About
 
- If "About <Application>" is visible, use that application name.
 
Examples:
✔ BarTender Designer
✔ BarTender
✔ SIPLACE Pro Desk
 
NOT:
✘ Remote Desktop Connection
✘ Windows
✘ Desktop

2. Identify the VERSION number (e.g. "4.2.1", "Build 2024.03", "v10.5",
   "Release 7"). Only pick something that plausibly looks like a version
   identifier - do not confuse it with a random number, a date, or a port
   number.
3. Identify the PC's SYSTEM CLOCK timestamp - the actual date/time the
screenshot was taken. This is normally visible in the Windows taskbar,
system tray, or a corner of the screen.
 
IMPORTANT:
- Do NOT use dates shown inside the application itself (such as software
version numbers, build numbers, release dates, licence expiry dates,
calendar entries, logs, or report dates).
- If no Windows taskbar or system clock is visible, return an empty
string ("") for both "timestamp_raw" and "timestamp_iso".
- Never guess or invent a timestamp.
- If several timestamps are visible, choose only the one that belongs to
the operating system clock.
4. Convert the timestamp to ISO 8601 format (YYYY-MM-DDTHH:MM) only if a genuine Windows system clock timestamp was found. Otherwise leave both timestamp fields empty.
5. If more than one plausible version or more than one plausible timestamp
   appears, list them ALL as candidates rather than guessing - do not
   silently discard alternatives.

--- EXAMPLE (FOR FORMAT ILLUSTRATION ONLY - these are fictional placeholder
values, NOT real data. NEVER copy any value from this example into your
actual answer. Your answer must come ONLY from the real OCR TEXT provided
after this example.) ---
OCR TEXT:
"MyComplianceApp\\nVersion 3.4.1\\nSystem ready\\n10:15 AM\\n7/9/2026\\nUser: jdoe"

CORRECT OUTPUT:
{{
  "application_name": "MyComplianceApp",
  "version": "3.4.1",
  "timestamp_raw": "10:15 AM 7/9/2026",
  "timestamp_iso": "2026-07-09T10:15",
  "version_candidates": ["3.4.1"],
  "timestamp_candidates": ["10:15 AM 7/9/2026"],
  "confidence_notes": "Clear single version and timestamp found."
}}
--- END EXAMPLE - the above values (MyComplianceApp, 3.4.1, 10:15 AM,
7/9/2026, jdoe) are FICTIONAL and must NEVER appear in your real answer
unless they happen to also appear in the real OCR TEXT below. ---

Note: OCR sometimes merges a time and drops the colon, e.g. "813AM" means
"8:13 AM", and "1245PM" means "12:45 PM". Watch for this pattern near
taskbar-related text like "Type here to search".

Now analyze this REAL OCR TEXT (this is the actual data - your answer
must be based only on this):
\"\"\"
{ocr_text}
\"\"\"

Respond ONLY in this JSON format, no other text, no markdown fences:
{{
  "application_name": "the application name found, or empty string if unclear",
  "version": "the single best-guess version string, or empty string if none found",
  "timestamp_raw": "the single best-guess timestamp as it appeared in the OCR output",
  "timestamp_iso": "ISO 8601 format YYYY-MM-DDTHH:MM, or empty string if unclear",
  "version_candidates": ["list of all plausible version strings found, even if just one"],
  "timestamp_candidates": ["list of all plausible timestamp strings found, even if just one"],
  "confidence_notes": "brief note on any ambiguity, multiple candidates, or issues found"
}}
"""


def call_ollama(prompt):
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except Exception as e:
        print(f"[Extraction Worker] Ollama call failed: {e}")
        return None


def try_parse_json(text):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return None

def extract_version_and_timestamp(ocr_text):
    """
    Returns: {"application_name": str, "version": str, "timestamp_raw": str,
              "timestamp_iso": str, "version_candidates": list,
              "timestamp_candidates": list, "confidence_notes": str}
    Returns None if the local model call failed or gave an unparseable
    response - caller should fall back to manual review in that case.
    """
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(ocr_text=ocr_text[:3000])
    raw_response = call_ollama(prompt)
    parsed = try_parse_json(raw_response)
    #missing_fields = validate_result(parsed)

    if not parsed or "timestamp_raw" not in parsed:
        print("[Extraction Worker] Could not extract version/timestamp - needs manual review")
        return None

    return parsed


def check_compliance_window(timestamp_iso, review_start_date_iso, next_due_date_iso):
    """
    Compares the extracted screenshot timestamp against the application's
    OWN compliance window (already computed in Trackora's application_analysis
    table: review_start_date -> next_due_date). No separate "submission time"
    tracking is needed - this reuses data you already have.

    Returns: {"status": "compliant" | "late" | "suspicious" | "missing" | "unparseable",
              "note": str}
    """
    if not timestamp_iso:
        return {"status": "missing",
                "note": "No timestamp could be read from the screenshot - flag for manual review."}

    try:
        screenshot_time = datetime.fromisoformat(timestamp_iso)
        review_start = datetime.fromisoformat(review_start_date_iso)
        next_due = datetime.fromisoformat(next_due_date_iso)
    except Exception:
        return {"status": "unparseable",
                "note": "Timestamp or date fields could not be compared - verify manually."}

    if screenshot_time < review_start:
        return {"status": "suspicious",
                "note": f"Screenshot timestamp ({screenshot_time.date()}) predates the current "
                        f"review period (started {review_start.date()}) - may be a reused screenshot "
                        f"from a previous cycle."}

    if screenshot_time > next_due:
        return {"status": "late",
                "note": f"Screenshot timestamp ({screenshot_time.date()}) is after the compliance "
                        f"deadline ({next_due.date()}) - evidence arrived too late."}

    return {"status": "compliant",
            "note": f"Screenshot timestamp ({screenshot_time.date()}) falls within the current "
                    f"compliance window (by {next_due.date()}) - evidence looks valid."}