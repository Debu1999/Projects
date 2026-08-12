from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import sqlite3
import os
import traceback
import sys
import json
from auth import get_access_token
from graph_client import get_full_message,get_latest_message_in_conversation,get_current_user_email,get_messages_in_conversation

if getattr(sys,'frozen',False):
    BASE_DIR=os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "followups.db")
 
 
#def get_connection():
#    return sqlite3.connect(DB_NAME)
import sqlite3
import traceback
def get_connection():
    conn = sqlite3.connect(
        DB_NAME,
        timeout=30,
        isolation_level=None,   # <-- IMPORTANT
        check_same_thread=False
    )
    return conn
 
 
 
# ✅ Initialize Database
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
 
    # SETTINGS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            followup_text TEXT,
            max_attempts INTEGER NOT NULL,
            interval_minutes INTEGER NOT NULL,
            followup_mode TEXT DEFAULT 'manual',
            updated_at TEXT NOT NULL,
            UNIQUE(category_name,version)
        )
    """)
 
    # Ensure followup_mode column exists (for old DBs)
    cursor.execute("PRAGMA table_info(settings)")
    columns = [col[1] for col in cursor.fetchall()]
    if "followup_mode" not in columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN followup_mode TEXT DEFAULT 'manual'")
    if "version" not in columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN version INTEGER DEFAULT 1")
 
 
    # CATEGORY TEMPLATES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS category_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            order_number INTEGER NOT NULL,
            draft_id TEXT NOT NULL,
            draft_subject TEXT,
            UNIQUE(category_name,version,order_number)
            )
    """)
    cursor.execute("PRAGMA table_info(category_templates)")
    columns = [col[1] for col in cursor.fetchall()]
    if "draft_subject" not in columns:
        cursor.execute("ALTER TABLE category_templates ADD COLUMN draft_subject TEXT")
    if "version" not in columns:
        cursor.execute("ALTER TABLE category_templates ADD COLUMN version INTEGER DEFAULT 1")


    #FOLDERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS folder_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        primary_folder_id TEXT,
        secondary_folder_id TEXT
        )
    """)

 
    # FOLLOWUPS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL UNIQUE,
            category_name TEXT NOT NULL,
            category_version INTEGER DEFAULT 1,
            subject TEXT,
            status TEXT NOT NULL,
            attempt_count INTEGER DEFAULT 0,
            next_followup_at TEXT NOT NULL,
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("PRAGMA table_info(followups)")
    columns = [col[1] for col in cursor.fetchall()]
    if "category_version" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN category_version INTEGER DEFAULT 1")
    
    cursor.execute("PRAGMA table_info(followups)")
    columns = [col[1] for col in cursor.fetchall()]
    if "last_followup_sent_at" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN last_followup_sent_at TEXT")
    
    cursor.execute("PRAGMA table_info(followups)")
    columns = [col[1] for col in cursor.fetchall()]
    if "last_client_reply_at" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN last_client_reply_at TEXT")
    
    if "last_client_email" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN last_client_email TEXT")
    if "original_recipients" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN original_recipients TEXT")

    cursor.execute("PRAGMA table_info(followups)")
    columns = [col[1] for col in cursor.fetchall()]
    if "last_reply_subject" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN last_reply_subject TEXT")
    if "last_reply_body" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN last_reply_body TEXT")
    if "is_unread_reply" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN is_unread_reply INTEGER DEFAULT 0")
    if "is_ignored_reply" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN is_ignored_reply INTEGER DEFAULT 0")
    if "last_reply_message_id" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN last_reply_message_id TEXT")

    cursor.execute("PRAGMA table_info(followups)")
    columns = [col[1] for col in cursor.fetchall()]
    if "ai_draft_body" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN ai_draft_body TEXT")
    if "ai_draft_reasoning" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN ai_draft_reasoning TEXT")
    if "ai_draft_status" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN ai_draft_status TEXT DEFAULT 'none'")
    if "ai_classification" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN ai_classification TEXT")
    if "ai_analyzed_at" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN ai_analyzed_at TEXT")
    if "auto_followup_enabled" not in columns:
        cursor.execute("ALTER TABLE followups ADD COLUMN auto_followup_enabled INTEGER DEFAULT 1")
 
 
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_status_next
        ON followups(status, next_followup_at)
    """)
 
    # ACTIVITY LOGS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    # ===============================
    # APPLICATION TRACKING TABLE (NEW SYSTEM)
    # ===============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
 
    upload_id INTEGER,
 
    appser_number TEXT,
    appser_name TEXT,
    appser_install_status TEXT,
    so_u_sbg TEXT,
    owner_name TEXT,
    tech_owner_name TEXT,
    current_installed_version TEXT,
    vendor_name TEXT,
    reviewer_id TEXT,
    reviewed_date TEXT,
    u_run_operations_focal TEXT,
    compliance_mode TEXT DEFAULT 'FREQUENCY',
    remediation_due_date TEXT,
    exception_reason TEXT,
 
    status TEXT DEFAULT 'ACTIVE',
 
    created_at TEXT,
    
 
    UNIQUE(upload_id, appser_number)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications_raw_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
 
    upload_id INTEGER,
    appser_number TEXT,
 
    row_data TEXT,
 
    created_at TEXT
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_snapshot_upload
    ON applications_snapshot(upload_id);
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_snapshot_app
    ON applications_snapshot(appser_number)
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comparison_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_upload_id INTEGER,
    to_upload_id INTEGER,
    created_at TEXT,
    added_count INTEGER DEFAULT 0,
    modified_count INTEGER DEFAULT 0,
    missing_count INTEGER DEFAULT 0,
    master_count INTEGER DEFAULT 0,
    target_count INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comparison_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
 
    comparison_id INTEGER,
    appser_number TEXT,
 
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
 
    change_type TEXT,  -- ADDED / MODIFIED / MISSING
    approval_status TEXT DEFAULT 'PENDING',
 
    created_at TEXT,
    row_data TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appser_number TEXT,
    upload_id INTEGER,
    comment TEXT,
    created_at TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT,
    stored_name TEXT,
    created_at TEXT,
    file_type TEXT DEFAULT 'RAW_UPLOAD',
    comparison_id INTEGER,
    is_master INTEGER DEFAULT 0)
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS master_control (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER,
    is_active INTEGER DEFAULT 1,
    created_at TEXT)
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_mail_config (
    upload_id TEXT,
    appser_number TEXT,
    draft_id TEXT,
    category TEXT,
    PRIMARY KEY (upload_id, appser_number)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS action_template_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommended_action TEXT UNIQUE,
    draft_id TEXT,
    category_name TEXT,
    updated_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER,
    appser_number TEXT,
    frequency TEXT DEFAULT '',
    frequency_unit TEXT DEFAULT 'days',
    comments TEXT DEFAULT '',
    internal_status TEXT DEFAULT '',
    send_mail INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    updated_at TEXT,
    last_reviewed_date TEXT,
    next_due_date TEXT,
    last_sent_at TEXT,
    last_draft_id TEXT,
    last_category TEXT,
    send_status TEXT,
    conversation_id TEXT,
    compliance_mode TEXT DEFAULT 'FREQUENCY',
    remediation_due_date TEXT,
    exception_reason TEXT,
    vendor_status TEXT,
    recommended_action TEXT,
    action_status TEXT DEFAULT 'PENDING',
    review_start_date TEXT,
    UNIQUE(upload_id, appser_number)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER,
    appser_number TEXT,
    meeting_status TEXT DEFAULT 'SCHEDULED',
    meeting_start TEXT,
    meeting_end TEXT,
    meeting_link TEXT,
    event_id,
    created_at TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
 
    upload_id INTEGER,
    appser_number TEXT NOT NULL,
 
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT,
 
    uploaded_at TEXT,
    uploaded_by TEXT,
 
    -- OCR Output
    ocr_text TEXT,
 
    -- Ollama Output
    extracted_json TEXT,
 
    -- AI Analysis
    ai_status TEXT DEFAULT 'PENDING',
    ai_decision TEXT,
    ai_reasoning TEXT,
    confidence_score REAL,
 
    -- Analyst Review
    analyst_decision TEXT,
    analyst_remarks TEXT,
    reviewed_at TEXT,
 
    is_active INTEGER DEFAULT 1
    )
    """)
    # ===============================
    # WORKSPACES
    # ===============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    workspace_type TEXT DEFAULT 'MANUAL',
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
    )
    """)
    # ===============================
    # WORKSPACE CONVERSATIONS
    # ===============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workspace_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    conversation_id TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
 
    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,
 
    UNIQUE(conversation_id)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_workspace_conversations_workspace
    ON workspace_conversations(workspace_id)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_workspace_conversations_conversation
    ON workspace_conversations(conversation_id)
    """)

    conn.commit()
    conn.close()
 
 
 
# ===============================
# SETTINGS FUNCTIONS (PER CATEGORY)
# ===============================
def save_ai_draft(conversation_id, draft_body, reasoning, classification):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE followups
        SET ai_draft_body = ?,
            ai_draft_reasoning = ?,
            ai_classification = ?,
            ai_draft_status = 'pending',
            updated_at = ?
        WHERE conversation_id = ?
    """, (
        draft_body,
        reasoning,
        classification,
        datetime.now(timezone.utc).isoformat(),
        conversation_id
    ))
    conn.commit()
    conn.close()
def insert_evidence_upload(
    upload_id,
    appser_number,
    file_name,
    file_path,
    file_type,
    uploaded_at
):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        INSERT INTO evidence_uploads (
            upload_id,
            appser_number,
            file_name,
            file_path,
            file_type,
            uploaded_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        upload_id,
        appser_number,
        file_name,
        file_path,
        file_type,
        uploaded_at
    ))
    evidence_id= cursor.lastrowid
 
    conn.commit()
    conn.close()
    return evidence_id

import json
 
def update_ai_result(
    evidence_upload_id,
    evidence
):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    UPDATE evidence_uploads
    SET
        ocr_text = ?,
        extracted_json = ?,
        ai_status = ?,
        ai_decision = ?,
        ai_reasoning = ?
    WHERE id = ?
    """, (
        evidence.get("ocr_text", ""),
        json.dumps(evidence, indent=2),
        "COMPLETED",
        evidence.get("recommended_action", ""),
        evidence.get("compliance_note", ""),
        evidence_upload_id
    ))
 
    conn.commit()
    conn.close()
 
 
def get_ai_draft(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ai_draft_body, ai_draft_reasoning, ai_classification,
               ai_analyzed_at, ai_draft_status
        FROM followups WHERE conversation_id = ?
    """, (conversation_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[3]:
        return None
    return {
        "draft_body": row[0], "reasoning": row[1],
        "classification": row[2], "analyzed_at": row[3], "status": row[4],
    }


def update_ai_draft_status(conversation_id, status, new_body=None):
    conn = get_connection()
    cursor = conn.cursor()
    if new_body is not None:
        cursor.execute("""
            UPDATE followups
            SET ai_draft_status = ?, ai_draft_body = ?, updated_at = ?
            WHERE conversation_id = ?
        """, (status, new_body, datetime.now(timezone.utc).isoformat(), conversation_id))
    else:
        cursor.execute("""
            UPDATE followups
            SET ai_draft_status = ?, updated_at = ?
            WHERE conversation_id = ?
        """, (status, datetime.now(timezone.utc).isoformat(), conversation_id))
    conn.commit()
    conn.close()
def get_template_for_attempt(category_name,version,attempt_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT draft_id FROM category_templates
        WHERE category_name = ? AND version=? 
        ORDER BY order_number ASC
    """, (category_name,version))
    rows = cursor.fetchall()
    conn.close()
 
    if not rows:
        print("No template found for category")
        return None
 
    templates=[row[0] for row in rows]
    print("Templates found:",templates)
    print("Attempt Number:",attempt_number)

    if attempt_number<=len(templates):
        return {"draft_id":templates[attempt_number-1]}
    return {"draft_id":templates[-1]}

def get_template_folders():
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT primary_folder_id, secondary_folder_id
    FROM folder_settings
    WHERE primary_folder_id IS NOT NULL
    AND secondary_folder_id IS NOT NULL
    LIMIT 1
    """)
 
    row = cursor.fetchone()
    conn.close()

    return row

def save_template_folders_settings(primary_folder_id, secondary_folder_id):
    print("Saving to DB:", primary_folder_id, secondary_folder_id)
 
    conn = get_connection()
    cursor = conn.cursor()
 
    # Check if any row exists
    cursor.execute("SELECT COUNT(*) FROM folder_settings")
    count = cursor.fetchone()[0]
 
    if count == 0:
        # INSERT if no row exists
        cursor.execute("""
        INSERT INTO folder_settings (primary_folder_id, secondary_folder_id)
        VALUES (?, ?)
        """, (primary_folder_id, secondary_folder_id))
    else:
        # UPDATE existing row
        cursor.execute("""
        UPDATE folder_settings
        SET primary_folder_id = ?, secondary_folder_id = ?
        """, (primary_folder_id, secondary_folder_id))
 
    conn.commit()
    conn.close()
 
 
def get_settings(category_name,version):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT followup_text, max_attempts, interval_minutes,followup_mode
        FROM settings
        WHERE category_name = ? AND version=?
    """, (category_name,version))
 
    row = cursor.fetchone()
    conn.close()
    return row

def log_activity(conversation_id, action):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        INSERT INTO activity_logs (conversation_id, action, created_at)
        VALUES (?, ?, ?)
    """, (
        conversation_id,
        action,
        datetime.now(timezone.utc).isoformat()
    ))
 
    conn.commit()
    conn.close()

def pause_tracking(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        UPDATE followups
        SET status = 'CLIENT_REPLY',
            updated_at = ?
        WHERE conversation_id = ?
    """, (datetime.utcnow().isoformat(), conversation_id))
 
    conn.commit()
    conn.close()
def resume_tracking(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc)
 
    # Get category + version
    cursor.execute("""
    SELECT category_name, category_version
    FROM followups
    WHERE conversation_id = ?
    """, (conversation_id,))
    
    row = cursor.fetchone()
    print("DB status before update:",row)
    if not row:
        conn.close()
        return
 
    category_name, version = row
 
    settings = get_settings(category_name, version)
    if not settings:
        conn.close()
        return
 
    _, _, interval_minutes, _ = settings
 
    next_time = now + timedelta(minutes=interval_minutes)
 
    cursor.execute("""
    UPDATE followups
    SET status = 'ACTIVE',
        next_followup_at = ?,
        updated_at = ?
    WHERE conversation_id = ?
    AND status = 'CLIENT_REPLY'
    """, (
        next_time.isoformat(),
        now.isoformat(),
        conversation_id
    ))
    print("Rows Updated:",cursor.rowcount)
    print("Conversation_ID:",conversation_id)
 
    conn.commit()
    conn.close()
 
    log_activity(conversation_id, "Resumed Automatically")
 
def get_latest_category_version(category_name):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT MAX(version)
    FROM settings
    WHERE category_name = ?
    """, (category_name,))
 
    row = cursor.fetchone()
    conn.close()
 
    return row[0] if row and row[0] else 0

def save_settings(category_name, followup_text, max_attempts, interval_minutes,
                  followup_mode="manual", selected_draft_ids=None):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
 
    # ------------------------------------
    # Determine new version number
    # ------------------------------------
    latest_version = get_latest_category_version(category_name)
    new_version = latest_version + 1
 
    # ------------------------------------
    # Insert new settings version
    # ------------------------------------
    cursor.execute("""
        INSERT INTO settings
        (category_name, version, followup_text, max_attempts,
         interval_minutes, followup_mode, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        category_name,
        new_version,
        followup_text,
        max_attempts,
        interval_minutes,
        followup_mode,
        now
    ))
 
    # ------------------------------------
    # TEMPLATE HANDLING (snapshot)
    # ------------------------------------
    if followup_mode == "template" and selected_draft_ids:
 
        import re
 
        draft_list = [
            d.strip() for d in re.split(r"[;,|]", selected_draft_ids) if d.strip()
        ]
 
        print("Saving templates for category:", category_name, "version:", new_version)
 
        # Single template
        if len(draft_list) == 1:
 
            subject = get_draft_subject(draft_list[0]) or "No Subject"
 
            cursor.execute("""
                INSERT INTO category_templates
                (category_name, version, order_number, draft_id, draft_subject)
                VALUES (?, ?, ?, ?, ?)
            """, (
                category_name,
                new_version,
                1,
                draft_list[0],
                subject
            ))
 
        # Multiple templates
        else:
 
            for index, draft_id in enumerate(draft_list, start=1):
 
                subject = get_draft_subject(draft_id) or "No Subject"
 
                cursor.execute("""
                    INSERT INTO category_templates
                    (category_name, version, order_number, draft_id, draft_subject)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    category_name,
                    new_version,
                    index,
                    draft_id,
                    subject
                ))
 
    conn.commit()
    conn.close()
 
    return new_version
 
 
def get_bulk_runs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT
    conversation_id,subject,category_name,status,started_at FROM followups ORDER BY started_at DESC""")
    rows = cursor.fetchall()
    result = []

    for r in rows:
        result.append({
            "id": r[0],"subject": r[1],"category": r[2],"status": r[3],"recipient_count": 1,"created_at": r[4]})
    conn.close()
    return result
 

def get_status(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT status FROM followups
    WHERE conversation_id = ?
    """, (conversation_id,))
 
    row = cursor.fetchone()
    conn.close()
 
    return row[0] if row else None

def get_last_client_reply_time(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT last_client_reply_at FROM followups
    WHERE conversation_id = ?
    """, (conversation_id,))
 
    row = cursor.fetchone()
    conn.close()
 
    return row[0] if row else None

def get_client_reply_followups():
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT message_id, conversation_id, category_name, category_version,
           attempt_count, last_followup_sent_at, original_recipients
    FROM followups
    WHERE status = 'CLIENT_REPLY'
    """)
 
    rows = cursor.fetchall()
    conn.close()
    return rows
def get_manual_paused_followups():
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT message_id,
           conversation_id,
           category_name,
           category_version,
           attempt_count,
           last_followup_sent_at,
           original_recipients
    FROM followups
    WHERE status = 'MANUAL_PAUSED'
    """)
 
    rows = cursor.fetchall()
    conn.close()
 
    return rows
 
 
# ===============================
# INSERT OR RESUME (PER CATEGORY)
# ===============================
def insert_or_resume_followup(message, category_name,recipients_str):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc)

    version=get_latest_category_version(category_name)
 
    settings = get_settings(category_name,version)
    if not settings:
        conn.close()
        return "no_settings"
 
    _, max_attempts, interval_minutes,_ = settings
    next_time = now + timedelta(minutes=interval_minutes)
 
    subject = message.get("subject", "")
 
    cursor.execute("""
        SELECT id, status FROM followups 
        WHERE conversation_id = ?
    """, (message["conversationId"],))
 
    existing = cursor.fetchone()
 
    # ===============================
    # If conversation already exists
    # ===============================
    if existing:
        row_id, status = existing
 
        # Do NOT override any existing status
        # User controls ACTIVE / PAUSED / COMPLETED
        conn.close()
        return "skipped_existing"

    #to_list = message.get("toRecipients", [])
    #cc_list = message.get("ccRecipients", [])
    
 
    # ===============================
    # If new conversation → insert
    # ===============================
    if not recipients_str:
        recipients_str=""
    cursor.execute("""
        INSERT INTO followups (
            message_id,
            conversation_id,
            category_name,
            category_version,
            subject,
            status,
            attempt_count,
            next_followup_at,
            started_at,
            updated_at,
            original_recipients
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?,?)
    """, (
        message["id"],
        message["conversationId"],
        category_name,
        version,
        subject,
        "ACTIVE",
        0,
        next_time.isoformat(),
        now.isoformat(),
        now.isoformat(),
        recipients_str
    ))
 
    conn.commit()
    conn.close()
    log_activity(message["conversationId"],"Inserted via Sync")
 
    return "inserted"
  
 
# ===============================
# GET DUE FOLLOWUPS (FULLY DYNAMIC)
# ===============================
def restart_followup(conversation_id,new_version=None):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc)
 
    # Get category to calculate next interval
    cursor.execute("""
        SELECT category_name,category_version FROM followups
        WHERE conversation_id = ?
    """, (conversation_id,))
    row = cursor.fetchone()
 
    if not row:
        conn.close()
        return
 
    category_name,version = row

    if new_version:
        version=new_version
        
    settings = get_settings(category_name,version)
 
    if not settings:
        conn.close()
        return
 
    _, _, interval_minutes,_ = settings
    next_time = now + timedelta(minutes=interval_minutes)
 
    cursor.execute("""
        UPDATE followups
        SET status = 'ACTIVE',
            attempt_count = 0,
            category_version=?,
            next_followup_at = ?,
            updated_at = ?
        WHERE conversation_id = ?
    """, (version,next_time.isoformat(), now.isoformat(), conversation_id))
 
    conn.commit()
    conn.close()

    log_activity(conversation_id,"Restarted by User")

def get_activity(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT action, created_at
        FROM activity_logs
        WHERE conversation_id = ?
        ORDER BY created_at DESC
    """, (conversation_id,))
 
    rows = cursor.fetchall()
    conn.close()
    return rows    

def get_all_activity():
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT 
            f.subject,
            a.action,
            a.created_at
        FROM activity_logs a
        JOIN followups f 
            ON a.conversation_id = f.conversation_id
        ORDER BY a.created_at DESC
    """)
 
    rows = cursor.fetchall()
    conn.close()
    return rows
 

def get_due_followups():
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
 
    cursor.execute("""
        SELECT message_id, conversation_id, category_name,category_version, attempt_count,last_followup_sent_at,original_recipients
        FROM followups
        WHERE status = 'ACTIVE'
        AND next_followup_at <= ?
        AND auto_followup_enabled=1
    """, (now,))
 
    rows = cursor.fetchall()
    conn.close()
 
    return rows
 
 
# ===============================
# UPDATE AFTER SEND
# ===============================

def update_after_send(conversation_id, category_name):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc)
    last_followup_sent_time=now
 
    cursor.execute("""
    SELECT attempt_count,category_version FROM followups
    WHERE conversation_id = ? AND category_name=? AND status = 'ACTIVE'
    """, (conversation_id, category_name))
 
    row = cursor.fetchone()
 
    if not row:
        conn.close()
        return
 
    attempt_count, version = row
    new_attempt = attempt_count + 1
 
    settings = get_settings(category_name, version)
 
    if not settings:
        conn.close()
        return
 
    _, max_attempts, interval_minutes, _ = settings
 
    # ===============================
    # If reached max attempts → COMPLETE
    # ===============================
 
    if new_attempt >= max_attempts:
        cursor.execute("""
        UPDATE followups
        SET attempt_count = ?,
        status = 'COMPLETED',
        updated_at = ?,
        last_followup_sent_at=?
        WHERE conversation_id = ?
        AND category_name=?
        AND category_version=?
        """, (new_attempt, now.isoformat(),last_followup_sent_time.isoformat(), conversation_id, category_name, version))
 
        conn.commit()
        conn.close()
 
        # ✅ Log attempt
        log_activity(conversation_id, f"Followup Attempt #{new_attempt} sent")
 
        # ✅ Log completion
        log_activity(conversation_id, "Marked as Completed")
 
    else:
        # ===============================
        # Otherwise → schedule next attempt
        # ===============================
 
        next_time = last_followup_sent_time + timedelta(minutes=interval_minutes)
 
        cursor.execute("""
        UPDATE followups
        SET attempt_count = ?,
        next_followup_at = ?,
        updated_at = ?,
        last_followup_sent_at=?
        WHERE conversation_id = ?
        AND category_name=?
        AND category_version=?
        """, (
            new_attempt,
            next_time.isoformat(),
            now.isoformat(),
            last_followup_sent_time.isoformat(),
            conversation_id,
            category_name,
            version
        ))
 
        conn.commit()
        conn.close()
 
        # ✅ Log attempt
        log_activity(conversation_id, f"Followup Attempt #{new_attempt} sent")

def clone_category_version(category_name, source_version):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    # get latest version safely
    cursor.execute("""
    SELECT MAX(version)
    FROM settings
    WHERE category_name=?
    """,(category_name,))
 
    row = cursor.fetchone()
    latest_version = row[0] if row and row[0] else 0
    new_version = latest_version + 1
 
    now = datetime.now(timezone.utc).isoformat()
 
    # copy settings
    cursor.execute("""
    INSERT INTO settings
    (category_name,version,followup_text,max_attempts,
    interval_minutes,followup_mode,updated_at)
 
    SELECT
    category_name,
    ?,
    followup_text,
    max_attempts,
    interval_minutes,
    followup_mode,
    ?
    FROM settings
    WHERE category_name=? AND version=?
    """,(new_version,now,category_name,source_version))
 
    # copy templates
    cursor.execute("""
    INSERT INTO category_templates
    (category_name,version,order_number,draft_id,draft_subject)
 
    SELECT
    category_name,
    ?,
    order_number,
    draft_id,
    draft_subject
    FROM category_templates
    WHERE category_name=? AND version=?
    """,(new_version,category_name,source_version))
 
    conn.commit()
    conn.close()
 
    return new_version
 
def save_client_reply(conversation_id, email, reply_time,subject,body,message_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    UPDATE followups
    SET last_client_reply_at = ?,
        last_client_email = ?,
        last_reply_subject=?,
        last_reply_body=?,
        last_reply_message_id=?,
        is_unread_reply=1,
        is_ignored_reply=0,
        auto_followup_enabled=0,
        updated_at = ?
    WHERE conversation_id = ?
    """, (
        reply_time.isoformat() if reply_time else None,
        email,
        subject,
        body,
        message_id,
        datetime.now(timezone.utc).isoformat(),
        conversation_id
    ))
 
    conn.commit()
    conn.close()

def ignore_reply(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    UPDATE followups
    SET is_ignored_reply = 1,
        is_unread_reply = 0,
        last_followup_sent_at=last_client_reply_at,
        updated_at = ?
    WHERE conversation_id = ?
    """, (
        datetime.now(timezone.utc).isoformat(),
        conversation_id
    ))
 
    conn.commit()
    conn.close()

def get_unread_replies():
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT conversation_id, last_reply_subject, last_reply_body
    FROM followups
    WHERE is_unread_reply = 1
      AND is_ignored_reply = 0
    """)
 
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_reply_flags(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT is_ignored_reply
        FROM followups
        WHERE conversation_id = ?
    """, (conversation_id,))
 
    row = cursor.fetchone()
    conn.close()
 
    return row[0] if row else 0

def get_all_categories():
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT category_name, version
    FROM settings
    ORDER BY category_name, version DESC
    """)
 
    rows = cursor.fetchall()
    conn.close()
 
    categories = {}
 
    for name, version in rows:
        if name not in categories:
            categories[name] = []
 
        categories[name].append(version)
 
    result = []
 
    for name, versions in categories.items():
        result.append({
            "name": name,
            "versions": versions
        })
 
    return result


def get_category_details(category_name,version):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    # SETTINGS
    cursor.execute("""
    SELECT version,followup_text, max_attempts, interval_minutes,
    followup_mode, updated_at
    FROM settings
    WHERE category_name = ?
    AND version=?
    """, (category_name,version))
 
    settings = cursor.fetchone()
 
    if not settings:
        conn.close()
        return None
 
    version,followup_text, max_attempts, interval_minutes, mode, updated_at = settings
 
 
    # STATUS COUNTS
    cursor.execute("""
    SELECT
        COUNT(*),
        SUM(CASE WHEN status='ACTIVE' THEN 1 ELSE 0 END),
        SUM(CASE WHEN status='CLIENT_REPLY' THEN 1 ELSE 0 END),
        SUM(CASE WHEN status='MANUAL_PAUSED' THEN 1 ELSE 0 END),
        SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END)
    FROM followups
    WHERE category_name = ?
    """, (category_name,))
 
    stats = cursor.fetchone()
    total, active, client_paused,manual_paused, completed = stats or (0,0,0,0,0)
 
 
    # TEMPLATES
    cursor.execute("""
    SELECT order_number,draft_subject
    FROM category_templates
    WHERE category_name = ?
    AND version=?
    ORDER BY order_number
    """, (category_name,version))
 
    template_rows = cursor.fetchall()
 
    conn.close()
    templates=[
        {
            "order":row[0],
            "subject":row[1]
        }
        for row in template_rows
    ]
 
 
 
    # MODE LABEL
    if mode == "manual":
        mode_label = "Manual Text"
    elif len(templates) == 1:
        mode_label = "Single Template"
    elif len(templates) > 1:
        mode_label = f"Template Sequence ({len(templates)})"
    else:
        mode_label = "Template"
 
 
    updated = convert_to_ist(updated_at) if updated_at else None
 
 
    return {
        "category": category_name,
        "version":version,
        "interval_minutes": interval_minutes,
        "max_attempts": max_attempts,
        "mode": mode_label,
        "followup_text": followup_text,
        "templates": templates,
        "updated_at": updated,
        "stats": {
            "total": total or 0,
            "active": active or 0,
            "client_paused": client_paused or 0,
            "manual_paused":manual_paused or 0,
            "completed": completed or 0
        }
    }

import requests
 
def get_draft_subject(draft_id):
 
    try:
 
        token = get_access_token()   # your existing function
 
        headers = {
            "Authorization": f"Bearer {token}"
        }
 
        url = f"https://graph.microsoft.com/v1.0/me/messages/{draft_id}?$select=subject"
 
        r = requests.get(url, headers=headers)
 
        if r.status_code == 200:
            data = r.json()
            return data.get("subject")
 
        else:
            print("Graph error:", r.text)
 
    except Exception as e:
        print("Error fetching subject:", e)
 
    return None 
 
def get_followups_by_status(status):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT subject, category_name, attempt_count,
               next_followup_at, updated_at
        FROM followups
        WHERE status = ?
        ORDER BY next_followup_at
    """, (status,))
 
    rows = cursor.fetchall()
    conn.close()
    return rows
 
 
def convert_to_ist(utc_string):
    if not utc_string:
        return ""
 
    utc_dt = datetime.fromisoformat(utc_string)
    ist = ZoneInfo("Asia/Kolkata")
    ist_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ist)
 
    return ist_dt.strftime("%d %b %Y, %I:%M %p IST")

def upsert_application(app_data):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
 
    cursor.execute("""
    INSERT INTO applications (
        appser_name,
        appser_number,
        appser_install_status,
        so_u_sbg,
        owner_name,
        tech_owner_name,
        current_installed_version,
        vendor_name,
        reviewer_id,
        reviewed_date,
        u_run_operations_focal,
        comments,
        verified_reviewed_date,
        internal_compliance_status,
        created_at,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
 
    ON CONFLICT(appser_number) DO UPDATE SET
        appser_name=excluded.appser_name,
        appser_install_status=excluded.appser_install_status,
        so_u_sbg=excluded.so_u_sbg,
        owner_name=excluded.owner_name,
        tech_owner_name=excluded.tech_owner_name,
        current_installed_version=excluded.current_installed_version,
        vendor_name=excluded.vendor_name,
        reviewer_id=excluded.reviewer_id,
        reviewed_date=excluded.reviewed_date,
        u_run_operations_focal=excluded.u_run_operations_focal,
        updated_at=excluded.updated_at
    """, (
        app_data.get("appser_name"),
        app_data.get("appser_number"),
        app_data.get("appser_install_status"),
        app_data.get("so_u_sbg"),
        app_data.get("owner_name"),
        app_data.get("tech_owner_name"),
        app_data.get("current_installed_version"),
        app_data.get("vendor_name"),
        app_data.get("reviewer_id"),
        now,  # reviewed_date updated on upload
        app_data.get("u_run_operations_focal"),
        app_data.get("comments"),
        None,  # verified_reviewed_date (manual later)
        "Compliant",  # default
        now,
        now
    ))
 
    conn.commit()
    conn.close()

def create_new_version(file_name):
    conn = get_connection()
    cursor = conn.cursor()
 
    # Get latest version number
    cursor.execute("SELECT MAX(version_number) FROM master_versions")
    row = cursor.fetchone()
    latest_version = row[0] if row and row[0] else 0
 
    new_version = latest_version + 1
 
    now = datetime.now(timezone.utc).isoformat()
 
    # Mark all old versions as inactive
    cursor.execute("UPDATE master_versions SET is_active = 0")
 
    # Insert new version
    cursor.execute("""
    INSERT INTO master_versions (version_number, file_name, created_at, is_active)
    VALUES (?, ?, ?, 1)
    """, (new_version, file_name, now))
 
    conn.commit()
 
    version_id = cursor.lastrowid
 
    conn.close()
 
    return version_id, new_version

def insert_snapshot(cursor,upload_id, row):
 
    now = datetime.now(timezone.utc).isoformat()
 
    if not row.get("appser_number"):
        return
 
    cursor.execute("""
    INSERT INTO applications_snapshot (
        upload_id,
        appser_number,
        appser_name,
        appser_install_status,
        so_u_sbg,
        owner_name,
        tech_owner_name,
        current_installed_version,
        vendor_name,
        reviewer_id,
        reviewed_date,
        u_run_operations_focal,
        compliance_mode,
        remediation_due_date,
        exception_reason,
        status,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?, 'ACTIVE', ?)
    """, (
        upload_id,
        row.get("appser_number"),
        row.get("appser_name"),
        row.get("appser_install_status"),
        row.get("so_u_sbg"),
        row.get("owner_name"),
        row.get("tech_owner_name"),
        row.get("current_installed_version"),
        row.get("vendor_name"),
        row.get("reviewer_id"),
        now,
        row.get("u_run_operations_focal"),
        row.get("compliance_mode","FREQUENCY"),
        row.get("remediation_due_date",""),
        row.get("exception_reason",""),
        now
    ))
def get_latest_external_responder(asn):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT upload_id
    FROM master_control
    WHERE is_active = 1
    """)
 
    row = cursor.fetchone()
 
    if not row:
        return None
 
    upload_id = row[0]
 
    cursor.execute("""
    SELECT conversation_id
    FROM application_analysis
    WHERE upload_id = ?
    AND appser_number = ?
    """, (
        upload_id,
        asn
    ))
 
    conv_row = cursor.fetchone()
 
    conn.close()
 
    if not conv_row:
        return None
 
    conversation_id = conv_row[0]
 
    messages = get_messages_in_conversation(conversation_id)
    messages.sort(key=lambda x: x.get("receivedDateTime", ""),reverse=True)
    MY_EMAIL = get_current_user_email().lower()
    for msg in messages:
        sender = (
            msg.get("from", {})
            .get("emailAddress", {})
        )
        sender_email = (
            sender.get("address", "")
            .lower()
            .strip()
        )
        if sender_email != MY_EMAIL:
            return {
                "name": sender.get("name"),
                "email": sender.get("address")
            }
    return None
 
 

 
def get_active_version():
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT id, version_number
    FROM master_versions
    WHERE is_active = 1
    LIMIT 1
    """)
 
    row = cursor.fetchone()
    conn.close()
 
    return row  # (version_id, version_number)

def save_comment(appser_number, version_id, comment):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
 
    cursor.execute("""
    INSERT INTO application_comments (
        appser_number,
        version_id,
        comment,
        created_at
    ) VALUES (?, ?, ?, ?)
    """, (appser_number, version_id, comment, now))
 
    conn.commit()
    conn.close()



'''def get_snapshot_by_upload(upload_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT
            appser_number,
            appser_name,
            appser_install_status,
            so_u_sbg,
            owner_name,
            tech_owner_name,
            current_installed_version,
            vendor_name
        FROM applications_snapshot
        WHERE upload_id = ?
    """, (upload_id,))
 
    rows = cursor.fetchall()
    conn.close()
 
    data = {}
 
    for r in rows:
        data[r[0]] = {
            "appser_name": r[1] or "",
            "appser_install_status": r[2] or "",
            "so_u_sbg": r[3] or "",
            "owner_name": r[4] or "",
            "tech_owner_name": r[5] or "",
            "current_installed_version": r[6] or "",
            "vendor_name": r[7] or ""
        }
 
    return data'''
def get_snapshot_by_upload(upload_id):
 
    import json
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT appser_number, row_data
    FROM applications_raw_data
    WHERE upload_id = ?
    """, (upload_id,))
 
    rows = cursor.fetchall()
 
    conn.close()
 
    result = {}
 
    for row in rows:
 
        appser_number = row[0]
 
        try:
            row_data = json.loads(row[1])
        except:
            row_data = {}
 
        result[appser_number] = row_data
    print(
    "UPLOAD:",
    upload_id,
    "DB_ROWS:",
    len(rows),
    "DICT_ROWS:",
    len(result))
 
    return result
 


def create_comparison(cursor,master_upload_id, target_upload_id,master_count,target_count):
    now = datetime.now(timezone.utc).isoformat()
 
    cursor.execute("""
        INSERT INTO comparison_logs (from_upload_id,to_upload_id,created_at,master_count,target_count)
        VALUES (?, ?, ?,?,?)
    """, (master_upload_id,target_upload_id, now,master_count,target_count))
 
    return cursor.lastrowid
def update_comparison_summary(
    comparison_id,
    added_count,
    modified_count,
    missing_count
):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        UPDATE comparison_logs
        SET
            added_count = ?,
            modified_count = ?,
            missing_count = ?
        WHERE id = ?
    """, (
        added_count,
        modified_count,
        missing_count,
        comparison_id
    ))
 
    conn.commit()
    conn.close()
 
def comparison_exists(master_upload_id, target_upload_id):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT id
        FROM comparison_logs
        WHERE from_upload_id = ?
        AND to_upload_id = ?
    """, (
        master_upload_id,
        target_upload_id
    ))
 
    row = cursor.fetchone()
 
    conn.close()
 
    return row[0] if row else None

def run_comparison(master_upload_id, target_upload_id):
    from datetime import datetime, timezone

    print("MASTER_UPLOAD_ID:",master_upload_id)
    print("TARGET_UPLOAD_ID:",target_upload_id)
    old_data = get_snapshot_by_upload(master_upload_id)
    new_data = get_snapshot_by_upload(target_upload_id)
    print("OLD COUNT:", len(old_data))
    print("NEW COUNT:", len(new_data))
    master_count=len(old_data)
    target_count=len(new_data)
    
    print("ASN0001470 IN OLD:",
      "ASN0001470" in old_data)
    print("ASN0001470 IN NEW:",
      "ASN0001470" in new_data)
 
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
    existing=comparison_exists(
        master_upload_id,
        target_upload_id
    )
    print("EXISTING_COMPARISON:",existing)
    if existing:
        return existing
    # ✅ Create comparison
    comparison_id = create_comparison(cursor, master_upload_id, target_upload_id,master_count,target_count)
 
    changes = []
 
    added = 0
    modified = 0
    missing = 0
 
    # 🔹 ADDED & MODIFIED
    for asn, new_row in new_data.items():
        # =========================
        # ADDED APPLICATION
        # =========================
        if asn not in old_data:
            changes.append((
                comparison_id,
                asn,
                "-",
                "-",
                "New Record",
                "ADDED",
                now,
                json.dumps(new_row)
            ))
            added += 1
        # =========================
        # MODIFIED APPLICATION
        # =========================
        else:
            old_row = old_data[asn]
            for field in new_row:
                old_value = str(old_row.get(field) or "").strip()
                new_value = str(new_row.get(field) or "").strip()
                # Skip ASN itself
                if field == "appser_number":
                    continue
                if old_value != new_value:
                    changes.append((
                        comparison_id,
                        asn,
                        field,
                        old_value,
                        new_value,
                        "MODIFIED",
                        now,
                        None
                    ))
                    modified += 1
    # 🔹 MISSING

    for asn in old_data:
        if asn not in new_data:
            changes.append((
                comparison_id, asn, "-", "Exists", "Missing", "MISSING", now,None
            ))
            missing += 1
 
    # ✅ BULK INSERT (VERY IMPORTANT)
    
    cursor.executemany("""
        INSERT INTO comparison_changes (
            comparison_id,
            appser_number,
            field_name,
            old_value,
            new_value,
            change_type,
            created_at,
            row_data
        )
        VALUES (?, ?, ?, ?, ?, ?, ?,?)
    """, changes)
 
    conn.commit()
    conn.close()
 
    # Optional summary
    update_comparison_summary(comparison_id, added, modified, missing)
 
    return comparison_id

def insert_snapshot_bulk(cursor, upload_id, row):
 
    now = datetime.now(timezone.utc).isoformat()
 
    if not row.get("appser_number"):
        return
 
    cursor.execute("""
    INSERT INTO applications_snapshot (
        upload_id,
        appser_number,
        appser_name,
        appser_install_status,
        so_u_sbg,
        owner_name,
        tech_owner_name,
        current_installed_version,
        vendor_name,
        reviewer_id,
        reviewed_date,
        u_run_operations_focal,
        compliance_mode,
        remediation_due_date,
        exception_reason,
        status,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
    """, (
        upload_id,
        row.get("appser_number"),
        row.get("appser_name"),
        row.get("appser_install_status"),
        row.get("so_u_sbg"),
        row.get("owner_name"),
        row.get("tech_owner_name"),
        row.get("current_installed_version"),
        row.get("vendor_name"),
        row.get("reviewer_id"),
        now,
        row.get("u_run_operations_focal"),
        row.get("compliance_mode", "FREQUENCY"),
        row.get("remediation_due_date", ""),
        row.get("exception_reason", ""),
        now
    ))
def insert_raw_snapshot_bulk(
    cursor,
    upload_id,
    row
):
 
    import json
    from datetime import datetime, timezone
 
    now = datetime.now(
        timezone.utc
    ).isoformat()
 
    appser_number = str(
        row.get("appser_number", "")
    ).strip()
 
    cursor.execute("""
    INSERT INTO applications_raw_data (
        upload_id,
        appser_number,
        row_data,
        created_at
    )
    VALUES (?, ?, ?, ?)
    """, (
        upload_id,
        appser_number,
        json.dumps(row,default=str),
        now
    ))
def get_active_followups():
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT
            message_id,
            conversation_id,
            category_name,
            category_version,
            attempt_count,
            last_followup_sent_at,
            original_recipients
        FROM followups
        WHERE status = 'ACTIVE'
    """)
 
    rows = cursor.fetchall()
 
    conn.close()
 
    return rows
 
 
def get_comparison_files():
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT
        id,
        created_at
    FROM comparison_logs
    ORDER BY id DESC
    """)
 
    rows = cursor.fetchall()
 
    conn.close()
 
    result = []
 
    for row in rows:
 
        result.append({
            "id": row[0],
            "created_at": row[1],
            "status": "PENDING REVIEW"
        })
 
    return result
def approve_change(change_id):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    UPDATE comparison_changes
    SET approval_status = 'APPROVED'
    WHERE id = ?
    """, (change_id,))
 
    conn.commit()
    conn.close()
 
def ignore_change_db(change_id):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    UPDATE comparison_changes
    SET approval_status = 'IGNORED'
    WHERE id = ?
    """, (change_id,))
 
    conn.commit()
    conn.close()

def insert_raw_snapshot(cursor,upload_id, row):
 
    import json
    from datetime import datetime, timezone
 
    now = datetime.now(timezone.utc).isoformat()
 
    appser_number = str(
        row.get("appser_number", "")
    ).strip()
 
    cursor.execute("""
    INSERT INTO applications_raw_data (
        upload_id,
        appser_number,
        row_data,
        created_at
    )
    VALUES (?, ?, ?, ?)
    """, (
        upload_id,
        appser_number,
        json.dumps(row),
        now
    ))

def get_recommended_action(
    internal_status,
    vendor_status
):
 
    if (internal_status == "Compliant" and vendor_status=="Patch Available"):
        return "NEXT_FREQUENCY_REVIEW"
 
    if (internal_status == "Pending Validation" and vendor_status=="No TimeStamp present"):
        return "REQUEST_FOR_EVIDENCE_WITH_TIMESTAMP"
 
    if (
        internal_status == "Non-compliant"
        and vendor_status == "Not Assessed"
    ):
        return "SEND_EVIDENCE_REQUEST"
 
    if (
        internal_status == "Exception Approved"
        and vendor_status == "No Vendor Update"
    ):
        return "REVIEW_IN_90_DAYS"
 
    if (
        internal_status == "Exception Approved"
        and vendor_status == "Funding Pending"
    ):
        return "WAIT_FOR_DUE_DATE"
 
    if (
        internal_status == "Exception Approved"
        and vendor_status == "Vendor Dependency"
    ):
        return "WAIT_FOR_VENDOR_ETA"
 
    if (
        internal_status == "Exception Approved"
        and vendor_status == "Upgrade Planned"
    ):
        return "TRACK_UPGRADE"
 
    return "MANUAL_REVIEW"


def get_send_mail_flag(recommended_action):
 
    if recommended_action in [
        "SEND_EVIDENCE_REQUEST",
        "REQUEST_TIMESTAMP_EVIDENCE",
        "REQUEST_VENDOR_ETA"
    ]:
        return 1
 
    return 0

def get_action_mail_type(recommended_action):
 
    mapping = {
        "SEND_EVIDENCE_REQUEST":
            "evidence_request",
 
        "REQUEST_TIMESTAMP_EVIDENCE":
            "timestamp_request",
 
        "WAIT_FOR_VENDOR_ETA":
            "vendor_eta_request",
 
        "WAIT_FOR_DUE_DATE":
            "funding_confirmation"
    }
 
    return mapping.get(recommended_action)

def get_all_recommended_actions():
 
    return [
        "SEND_EVIDENCE_REQUEST",
        "REQUEST_FOR_EVIDENCE_WITH_TIMESTAMP",
        "WAIT_FOR_VENDOR_ETA",
        "WAIT_FOR_DUE_DATE",
        "REVIEW_IN_90_DAYS",
        "TRACK_UPGRADE",
        "NEXT_FREQUENCY_REVIEW"
    ]
def get_action_mappings():
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT
        recommended_action,
        draft_id,
        category_name
    FROM action_template_mapping
    """)
 
    rows = cursor.fetchall()
    conn.close()
 
    return rows
  
def get_action_mapping(recommended_action):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT
        draft_id,
        category_name
    FROM action_template_mapping
    WHERE recommended_action = ?
    """, (recommended_action,))
 
    row = cursor.fetchone()
 
    conn.close()
 
    if not row:
        return None
 
    return {
        "draft_id": row[0],
        "category_name": row[1]
    }
def apply_all_changes_db(comparison_id):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    UPDATE comparison_changes
    SET approval_status = 'APPROVED'
    WHERE comparison_id = ?
    """, (comparison_id,))
 
    conn.commit()
    conn.close()
 
def ignore_all_changes_db(comparison_id):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    UPDATE comparison_changes
    SET approval_status = 'IGNORED'
    WHERE comparison_id = ?
    """, (comparison_id,))
 
    conn.commit()
    conn.close()
from datetime import datetime
 
 
def create_workspace(workspace_name, description=""):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now().isoformat()
 
    cursor.execute("""
        INSERT INTO workspaces (
            workspace_name,
            description,
            workspace_type,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, 'MANUAL', 'ACTIVE', ?, ?)
    """, (
        workspace_name.strip(),
        description.strip(),
        now,
        now
    ))
 
    workspace_id = cursor.lastrowid
 
    conn.commit()
    conn.close()
 
    return workspace_id
 
 
def get_workspaces():
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT
            id,
            workspace_name,
            description,
            workspace_type,
            status,
            created_at,
            updated_at
        FROM workspaces
        WHERE status = 'ACTIVE'
        ORDER BY updated_at DESC
    """)
 
    rows = cursor.fetchall()
    conn.close()
 
    return [
        {
            "id": row[0],
            "workspace_name": row[1],
            "description": row[2],
            "workspace_type": row[3],
            "status": row[4],
            "created_at": row[5],
            "updated_at": row[6]
        }
        for row in rows
    ]

def rename_workspace(workspace_id, workspace_name, description=None):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now().isoformat()
 
    if description is None:
 
        cursor.execute("""
            UPDATE workspaces
            SET workspace_name = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            workspace_name.strip(),
            now,
            workspace_id
        ))
 
    else:
 
        cursor.execute("""
            UPDATE workspaces
            SET workspace_name = ?,
                description = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            workspace_name.strip(),
            description.strip(),
            now,
            workspace_id
        ))
 
    conn.commit()
 
    updated = cursor.rowcount > 0
 
    conn.close()
 
    return updated
 
def archive_workspace(workspace_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now().isoformat()
 
    cursor.execute("""
        UPDATE workspaces
        SET status = 'ARCHIVED',
            updated_at = ?
        WHERE id = ?
    """, (
        now,
        workspace_id
    ))
 
    conn.commit()
 
    archived = cursor.rowcount > 0
 
    conn.close()
 
    return archived
 
def add_conversation_to_workspace(workspace_id, conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now().isoformat()
 
    # Verify workspace exists
    cursor.execute("""
        SELECT id
        FROM workspaces
        WHERE id = ?
        AND status = 'ACTIVE'
    """, (workspace_id,))
 
    if not cursor.fetchone():
        conn.close()
        raise Exception("Workspace not found.")
 
    # Conversation can belong to only ONE workspace
    cursor.execute("""
        SELECT workspace_id
        FROM workspace_conversations
        WHERE conversation_id = ?
    """, (conversation_id,))
 
    existing = cursor.fetchone()
 
    if existing:
        conn.close()
        raise Exception(
            "Conversation already belongs to a workspace."
        )
 
    cursor.execute("""
        INSERT INTO workspace_conversations (
            workspace_id,
            conversation_id,
            assigned_at
        )
        VALUES (?, ?, ?)
    """, (
        workspace_id,
        conversation_id,
        now
    ))
 
    conn.commit()
    conn.close()
 
    return True
 
def move_conversation_to_workspace(
    conversation_id,
    new_workspace_id
):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now().isoformat()
 
    # Verify target workspace
    cursor.execute("""
        SELECT id
        FROM workspaces
        WHERE id = ?
        AND status = 'ACTIVE'
    """, (new_workspace_id,))
 
    if not cursor.fetchone():
        conn.close()
        raise Exception("Target workspace not found.")
 
    cursor.execute("""
        UPDATE workspace_conversations
        SET workspace_id = ?,
            assigned_at = ?
        WHERE conversation_id = ?
    """, (
        new_workspace_id,
        now,
        conversation_id
    ))
 
    updated = cursor.rowcount > 0
 
    conn.commit()
    conn.close()
 
    return updated
 
def remove_conversation_from_workspace(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        DELETE FROM workspace_conversations
        WHERE conversation_id = ?
    """, (conversation_id,))
 
    removed = cursor.rowcount > 0
 
    conn.commit()
    conn.close()
 
    return removed
 
def get_workspace_conversations(workspace_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT
            wc.conversation_id,
            wc.assigned_at
        FROM workspace_conversations wc
        WHERE wc.workspace_id = ?
        ORDER BY wc.assigned_at DESC
    """, (workspace_id,))
 
    rows = cursor.fetchall()
    conn.close()
 
    return [
        {
            "conversation_id": row[0],
            "assigned_at": row[1]
        }
        for row in rows
    ]
 
 
 
 
 
