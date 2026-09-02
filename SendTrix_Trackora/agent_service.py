"""
agent_service.py

This module adds one "judgment checkpoint" to SendTrix's follow-up pipeline.

What it does:
    Given the actual latest message in a conversation (subject + body),
    plus how many follow-up attempts have been made, it asks Gemini:
        1. Should a follow-up actually be sent right now?
        2. If yes, what should it say (using real context, not a static template)?

Where it plugs in:
    process.py, in the "else" branch (manual follow-up mode), right before
    send_followup_reply_manual(...) is called.

Safety design:
    If the Gemini call fails for ANY reason (no internet, bad API key, quota
    hit, malformed response, etc.) this module falls back to your existing
    static followup_text automatically. A broken AI call will never silently
    stop your follow-ups from going out - it just behaves like before.
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

PROMPT_TEMPLATE = """You are helping decide whether to send a follow-up email
for a pending client conversation, and if so, what it should say.

Context:
- Category: {category_name}
- Attempt number: {attempt_number} of {max_attempts} max attempts
- Subject of latest message in this thread: {subject}
- Body of latest message in this thread: "{body}"

The default static follow-up message (for tone/style reference only) is:
"{fallback_text}"

Decide:
1. Should a follow-up be sent right now, given what's actually in the latest
   message? (e.g. if the client already answered the question, gave a firm
   timeline, or declined, a generic nudge may not be appropriate)
2. If yes, write a short, polite follow-up email body (3-5 sentences) that
   references the actual content above where relevant, in a similar tone to
   the default message.
3. If no, briefly explain why not.

Respond ONLY in this JSON format, with no other text, no markdown fences:
{{
  "send_followup": true or false,
  "reasoning": "...",
  "draft_email": "..." (empty string if send_followup is false)
}}
"""


def build_prompt(category_name, subject, body, attempt_number, max_attempts, fallback_text):
    # Trim very long email bodies so the prompt stays reasonably sized
    trimmed_body = (body or "")[:2000]
    return PROMPT_TEMPLATE.format(
        category_name=category_name,
        attempt_number=attempt_number,
        max_attempts=max_attempts,
        subject=subject or "(no subject)",
        body=trimmed_body,
        fallback_text=fallback_text or "(no default template set)",
    )


def call_gemini(prompt):
    if not GEMINI_API_KEY:
        print("[agent_service] GEMINI_API_KEY not set - skipping agent call")
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
        print(f"[agent_service] Gemini call failed: {e}")
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


def get_agent_followup_decision(
    category_name,
    subject,
    body,
    attempt_number,
    max_attempts,
    fallback_text,
):
    """
    Returns a dict: {"send_followup": bool, "reasoning": str, "draft_email": str}

    If Gemini is unreachable or returns something unparseable, this falls
    back to send_followup=True with the original static fallback_text -
    i.e. it behaves exactly like your current pipeline did before this
    integration, so nothing breaks silently.
    """
    prompt = build_prompt(
        category_name, subject, body, attempt_number, max_attempts, fallback_text
    )
    raw_response = call_gemini(prompt)
    parsed = try_parse_json(raw_response)

    if not parsed or "send_followup" not in parsed:
        print("[agent_service] Could not get a valid agent decision - falling back to static template")
        return {
            "send_followup": True,
            "reasoning": "Fallback: agent unavailable or response unparseable, used static template",
            "draft_email": fallback_text,
        }

    # If agent says send but forgot to include draft text, use the fallback
    if parsed.get("send_followup") and not parsed.get("draft_email"):
        parsed["draft_email"] = fallback_text

    return parsed


import re


def clean_email_body(html_body):
    """
    Strips HTML tags and extra whitespace from an Outlook message body,
    so we send clean plain text to Gemini instead of raw HTML markup.
    """
    if not html_body:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_body)   # remove tags
    text = re.sub(r"\s+", " ", text)            # collapse whitespace
    return text.strip()


REPLY_ANALYSIS_PROMPT_TEMPLATE = """You are helping an analyst reply to a client email.

The analyst is the one who originally sent this thread; you are drafting
their reply back to whoever sent the message below. Base your response
only on the conversation content \u2014 do not reference or infer any
identity beyond what is written in the message itself.

Context:
- Original thread subject: {subject}
- Latest reply in this thread (plain text): "{body}"

Analyze this reply and suggest a response.

Respond ONLY in this JSON format, no other text, no markdown fences:
{{
  "classification": "declined" or "needs_info" or "positive_progress" or "unclear",
  "reasoning": "1-2 sentence plain-English summary of what the client actually said",
  "draft_body": "a short, professional reply (3-5 sentences) that directly addresses what the client said, written naturally, not quoting their message back verbatim"
}}
"""

REPHRASE_PROMPT_TEMPLATE = """You previously drafted this reply to a client:

"{previous_draft}"

The analyst wants this change: "{instruction}"

Original context for reference:
- Subject: {subject}
- Client's message (plain text): "{body}"

Rewrite the reply according to the requested change. Keep it professional
and directly responsive to the client's message.

Respond ONLY in this JSON format, no other text, no markdown fences:
{{
  "draft_body": "the revised reply text"
}}
"""


def analyze_reply(subject, clean_body):
    """
    Called after a client reply is detected (body already cleaned of HTML).
    Sends only subject + message body to Gemini -- no client identity
    (name/email) is included in the prompt.
    Returns: {"classification": str, "reasoning": str, "draft_body": str}
    Returns None if the Gemini call fails - caller should leave the
    conversation paused with no analysis (safe default, matches old behavior).
    """
    prompt = REPLY_ANALYSIS_PROMPT_TEMPLATE.format(
        subject=subject or "(no subject)",
        body=(clean_body or "")[:2000],
    )
    raw_response = call_gemini(prompt)
    parsed = try_parse_json(raw_response)

    if not parsed or "draft_body" not in parsed:
        print("[agent_service] Could not analyze reply - leaving for manual handling")
        return None

    return parsed


def rephrase_draft_body(previous_draft, instruction, subject, clean_body):
    """
    Called when the analyst clicks 'rephrase' with an instruction like
    'make it shorter'. Returns the new draft text, or None if the
    call failed (caller should keep showing the previous draft).
    """
    prompt = REPHRASE_PROMPT_TEMPLATE.format(
        previous_draft=previous_draft,
        instruction=instruction,
        subject=subject or "(no subject)",
        body=(clean_body or "")[:2000],
    )
    raw_response = call_gemini(prompt)
    parsed = try_parse_json(raw_response)

    if not parsed or "draft_body" not in parsed:
        print("[agent_service] Could not rephrase draft - keeping previous version")
        return None

    return parsed["draft_body"]