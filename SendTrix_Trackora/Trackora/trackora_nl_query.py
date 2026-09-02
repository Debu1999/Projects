"""
trackora_nl_query.py

Lets an analyst type a plain-English question about the Master tab data,
and get back real results - without ever sending actual application data
to the AI. Only the TABLE STRUCTURE (column names + what they mean) is
sent to Gemini; Gemini's only job is to translate the question into a
SQL query, which your own code then runs locally against the real database.

Safety design:
    - Only SELECT statements are ever allowed to execute. Even if the model
      ever generated something else (by mistake or a malformed response),
      it gets rejected before touching the database.
    - Only applications_snapshot may be referenced; a query touching any
      other table is rejected outright.
    - Every query is forcibly scoped to the current user's own rows in
      code (scope_query_to_user()), regardless of whether the AI-generated
      SQL remembered to filter by user_id itself -- the AI is never trusted
      to enforce isolation on its own.
"""

import os
import re
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
# SCHEMA DESCRIPTION - this is the ONLY thing about your data that gets
# sent to the AI. No real rows, no actual application data, ever.
# ---------------------------------------------------------------------------

SCHEMA_DESCRIPTION = """
Table: applications_snapshot

Columns:
- id (integer, internal row id, not meaningful to the user)
- upload_id (integer, identifies which Master upload/batch this row belongs to)
- appser_number (text, the unique ASN identifier for the application)
- appser_name (text, application name)
- appser_install_status (text, install status of the application)
- so_u_sbg (text, business group / SBG the application belongs to)
- owner_name (text, business owner of the application)
- tech_owner_name (text, technical owner of the application)
- current_installed_version (text, version string currently installed)
- vendor_name (text, vendor providing the application)
- reviewer_id (text, id of person who last reviewed this application)
- reviewed_date (text, ISO date string of last review)
- u_run_operations_focal (text, operations focal point for this application)
- compliance_mode (text, usually 'FREQUENCY' - how compliance is evaluated)
- remediation_due_date (text, ISO date string, deadline to fix an issue)
- exception_reason (text, reason if this application has a compliance exception)
- status (text, usually 'ACTIVE' - whether this row is currently active)
- created_at (text, ISO datetime string of when this row was created)

Notes:
- Each upload_id represents one Master dump upload; to compare "latest" vs
  "previous", you'd order by upload_id descending.
- There is no single boolean "is_compliant" column here - compliance is
  usually derived from reviewed_date vs a frequency rule, or from
  remediation_due_date vs today's date, depending on the question.
"""

PROMPT_TEMPLATE = """You are a SQL assistant for a PostgreSQL database. You will
be given a table schema and a plain-English question. Convert the question
into a single, valid, read-only SQL query.

{schema}

Rules:
- ONLY generate SELECT statements. Never generate INSERT, UPDATE, DELETE,
  DROP, ALTER, ATTACH, PRAGMA, or any other statement type.
- Use only the table and columns described above - do not invent columns.
- If the question can't be answered with this schema, say so in the
  "explanation" field and leave "sql" as an empty string.
- This is PostgreSQL, not SQLite: dates are stored as ISO text, so cast
  with column::date where needed, and use PostgreSQL date functions
  (CURRENT_DATE, now(), AGE(), EXTRACT(...), INTERVAL) rather than SQLite
  functions like julianday() or date('now'), which do not exist here.
- For name-like text fields (owner_name, tech_owner_name, appser_name,
  vendor_name, reviewer_id, u_run_operations_focal), NEVER use an exact
  match. Always use: LOWER(column) LIKE LOWER('%value%') - since the
  person asking may only know a first name or partial name, and stored
  values may be full names in a different case.

Question: "{question}"

Respond ONLY in this JSON format, no other text, no markdown fences:
{{
  "sql": "the SQL query, or empty string if not answerable",
  "explanation": "1 sentence explaining what the query does, or why it can't be answered"
}}
"""


def call_gemini(prompt):
    if not GEMINI_API_KEY:
        print("[trackora_nl_query] GEMINI_API_KEY not set")
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
        print(f"[trackora_nl_query] Gemini call failed: {e}")
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


# ---------------------------------------------------------------------------
# SAFETY: hard rule that only SELECT statements can ever execute,
# regardless of what the model returns.
# ---------------------------------------------------------------------------

FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "attach", "detach",
    "pragma", "create", "replace", "truncate", "vacuum", "reindex",
]

# Every other table in the schema -- if any of these appear in a generated
# query, reject it. The AI is only ever shown applications_snapshot in its
# schema description, so a reference to any of these means either a model
# mistake or an attempt to reach data outside what was described.
OTHER_KNOWN_TABLES = [
    "users", "user_token_caches", "settings", "category_templates",
    "folder_settings", "followups", "activity_logs", "workspaces",
    "workspace_conversations", "uploads", "applications_raw_data",
    "comparison_logs", "comparison_changes", "application_comments",
    "master_control", "application_analysis", "evidence_uploads",
    "application_meetings", "action_template_mapping", "application_mail_config",
]


def is_safe_select(sql):
    """
    Returns True only if this looks like a single, safe SELECT statement
    that references only applications_snapshot.
    """
    if not sql:
        return False

    cleaned = sql.strip().rstrip(";").strip()

    # Must start with SELECT (case-insensitive)
    if not re.match(r"^\s*select\b", cleaned, re.IGNORECASE):
        return False

    lowered = cleaned.lower()

    # Must not contain any forbidden keywords anywhere in the query
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            return False

    # Must not reference any table other than applications_snapshot
    for table in OTHER_KNOWN_TABLES:
        if re.search(rf"\b{table}\b", lowered):
            return False

    # Must not contain a semicolon in the middle (blocks stacked statements)
    if ";" in cleaned:
        return False

    return True


def scope_query_to_user(sql, user_id):
    """
    Rewrites the AI-generated query so it can only ever see this user's
    own rows in applications_snapshot -- regardless of whether the
    generated SQL remembered to filter by user_id itself.

    Wraps applications_snapshot in a CTE pre-filtered to the current
    user, then redirects every reference to applications_snapshot in the
    AI's query to that CTE instead of the real table.
    """
    scoped_sql = re.sub(
        r"\bapplications_snapshot\b",
        "scoped_applications_snapshot",
        sql,
        flags=re.IGNORECASE,
    )
    wrapped = (
        "WITH scoped_applications_snapshot AS ("
        "SELECT * FROM applications_snapshot WHERE user_id = %(user_id)s"
        ") "
        + scoped_sql
    )
    return wrapped


def natural_language_to_sql(question):
    """
    Returns: {"sql": str, "explanation": str}
    Returns {"sql": "", "explanation": "..."} if the model couldn't
    produce a valid answerable query, or if the call failed.
    """
    prompt = PROMPT_TEMPLATE.format(schema=SCHEMA_DESCRIPTION, question=question)
    raw_response = call_gemini(prompt)
    parsed = try_parse_json(raw_response)

    if not parsed or "sql" not in parsed:
        return {"sql": "", "explanation": "Could not generate a query - please try rephrasing."}

    return parsed


def run_safe_query(sql, db_connection_getter, user_id):
    """
    Executes the given SQL only if it passes is_safe_select(), and only
    ever against this user's own rows -- user_id is enforced here in code,
    not left to the AI-generated query to remember on its own (an earlier
    version relied on that implicitly and could have returned every
    user's data; see scope_query_to_user()).

    db_connection_getter should be your existing get_connection() function
    from db_core.py, so this reuses your normal DB connection setup.

    Returns: {"success": bool, "rows": list, "columns": list, "error": str}
    """
    if not user_id:
        return {
            "success": False,
            "rows": [],
            "columns": [],
            "error": "No authenticated user -- query rejected.",
        }

    if not is_safe_select(sql):
        return {
            "success": False,
            "rows": [],
            "columns": [],
            "error": "Query rejected - only simple SELECT statements against applications_snapshot are allowed.",
        }

    scoped_sql = scope_query_to_user(sql, user_id)

    try:
        conn = db_connection_getter()
        cursor = conn.cursor()
        cursor.execute(scoped_sql, {"user_id": user_id})
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        return {"success": True, "rows": rows, "columns": columns, "error": ""}
    except Exception as e:
        return {"success": False, "rows": [], "columns": [], "error": str(e)}