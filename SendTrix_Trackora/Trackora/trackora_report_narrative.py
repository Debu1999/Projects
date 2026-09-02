"""
trackora_report_narrative.py

Two-part feature:
1. compute_compliance_summary() - pure Python/SQL counting, NO AI involved.
   Groups applications by SBG, by compliance mode, and by frequency+unit,
   counting compliant vs non-compliant in each group.

2. generate_summary_narrative() - takes ONLY the aggregate counts from
   step 1 (never individual application rows, ASNs, owner names, etc.)
   and asks Gemini to write a short readable paragraph describing them.

Because only counts/labels go to the AI (e.g. "Security: 12 compliant,
3 non-compliant"), no application-level or client-identifying data is
ever sent externally.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)


# ---------------------------------------------------------------------------
# STEP 1: Pure computation - no AI, fully deterministic
# ---------------------------------------------------------------------------

def compute_compliance_summary(upload_id, conn):
    """
    Returns a dict of aggregate counts only:
    {
        "total": int,
        "compliant": int,
        "non_compliant": int,
        "sbg_breakdown": {sbg_name: {"compliant": n, "non_compliant": n}, ...},
        "mode_breakdown": {mode_name: {"compliant": n, "non_compliant": n}, ...},
        "freq_breakdown": {"N unit": {"compliant": n, "non_compliant": n}, ...},
    }
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.so_u_sbg, a.compliance_mode, a.frequency, a.frequency_unit, a.internal_status
        FROM applications_snapshot s
        LEFT JOIN application_analysis a
            ON s.appser_number = a.appser_number AND s.upload_id = a.upload_id
        WHERE s.upload_id = %s
    """, (upload_id,))
    rows = cursor.fetchall()

    total = len(rows)
    compliant = sum(1 for r in rows if r[4] == "Compliant")
    non_compliant = sum(1 for r in rows if r[4] == "Non-Compliant")

    def bump(breakdown, key, status):
        key = key or "Unspecified"
        breakdown.setdefault(key, {"compliant": 0, "non_compliant": 0})
        if status == "Compliant":
            breakdown[key]["compliant"] += 1
        elif status == "Non-Compliant":
            breakdown[key]["non_compliant"] += 1

    sbg_breakdown = {}
    mode_breakdown = {}
    freq_breakdown = {}

    for sbg, mode, freq, freq_unit, status in rows:
        bump(sbg_breakdown, sbg, status)
        bump(mode_breakdown, mode, status)
        if mode == "FREQUENCY":
            freq_key = f"{freq} {freq_unit}" if freq and freq_unit else "Unspecified"
            bump(freq_breakdown, freq_key, status)

    return {
        "total": total,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "sbg_breakdown": sbg_breakdown,
        "mode_breakdown": mode_breakdown,
        "freq_breakdown": freq_breakdown,
    }


# ---------------------------------------------------------------------------
# STEP 2: AI narrative - only receives the counts computed above
# ---------------------------------------------------------------------------

NARRATIVE_PROMPT_TEMPLATE = """You are writing a short summary paragraph for
an internal compliance report. You are given ONLY aggregate counts - no
individual application names or identifying details.

Overall:
- Total applications: {total}
- Compliant: {compliant}
- Non-compliant: {non_compliant}

Breakdown by business group (SBG):
{sbg_lines}

Breakdown by compliance mode:
{mode_lines}

Breakdown by frequency (for applications using frequency-based compliance):
{freq_lines}

Write a concise, professional paragraph (4-6 sentences) summarizing this
data for a report audience. Mention the overall compliance rate, call out
which SBG(s) have the most non-compliance, and note anything worth
flagging about the frequency-based breakdown. Do not invent any numbers
not given above.

Respond ONLY in this JSON format, no other text, no markdown fences:
{{
  "narrative": "the summary paragraph"
}}
"""


def _format_breakdown_lines(breakdown):
    lines = []
    for key, counts in breakdown.items():
        lines.append(f"- {key}: {counts['compliant']} compliant, {counts['non_compliant']} non-compliant")
    return "\n".join(lines) if lines else "- (no data)"


def call_gemini(prompt):
    if not GEMINI_API_KEY:
        print("[trackora_report_narrative] GEMINI_API_KEY not set")
        return None
    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[trackora_report_narrative] Gemini call failed: {e}")
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


def generate_summary_narrative(summary):
    """
    summary: the dict returned by compute_compliance_summary()
    Returns the narrative string, or a safe fallback message if the
    Gemini call fails - never blocks the report from being generated.
    """
    prompt = NARRATIVE_PROMPT_TEMPLATE.format(
        total=summary["total"],
        compliant=summary["compliant"],
        non_compliant=summary["non_compliant"],
        sbg_lines=_format_breakdown_lines(summary["sbg_breakdown"]),
        mode_lines=_format_breakdown_lines(summary["mode_breakdown"]),
        freq_lines=_format_breakdown_lines(summary["freq_breakdown"]),
    )
    raw_response = call_gemini(prompt)
    parsed = try_parse_json(raw_response)

    if not parsed or "narrative" not in parsed:
        return "(AI summary unavailable - please review the counts above manually.)"

    return parsed["narrative"]