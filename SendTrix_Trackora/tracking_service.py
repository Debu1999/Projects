def save_ai_draft(conversation_id, draft_body, reasoning, classification):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE followups
        SET ai_draft_body = %s,
            ai_draft_reasoning = %s,
            ai_classification = %s,
            ai_draft_status = 'pending',
            updated_at = %s
        WHERE user_id = %s AND conversation_id = %s
    """, (
        draft_body,
        reasoning,
        classification,
        datetime.now(timezone.utc),
        user_id,
        conversation_id
    ))
    conn.commit()
    conn.close()
def update_ai_draft_status(conversation_id, status, new_body=None):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    if new_body is not None:
        cursor.execute("""
            UPDATE followups
            SET ai_draft_status = %s, ai_draft_body = %s, updated_at = %s
            WHERE conversation_id = %s AND user_id = %s
        """, (status, new_body, datetime.now(timezone.utc), conversation_id, user_id))
    else:
        cursor.execute("""
            UPDATE followups
            SET ai_draft_status = %s, updated_at = %s
            WHERE conversation_id = %s AND user_id = %s
        """, (status, datetime.now(timezone.utc), conversation_id, user_id))
    conn.commit()
    conn.close()
def get_ai_draft(conversation_id):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ai_draft_body, ai_draft_reasoning, ai_classification,
               ai_analyzed_at, ai_draft_status
        FROM followups WHERE conversation_id = %s AND user_id = %s
    """, (conversation_id, user_id))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[3]:
        return None
    return {
        "draft_body": row[0], "reasoning": row[1],
        "classification": row[2], "analyzed_at": row[3], "status": row[4],
    }
def update_ai_result(
    evidence_upload_id,
    evidence
):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    UPDATE evidence_uploads
    SET
        ocr_text = %s,
        extracted_json = %s,
        ai_status = %s,
        ai_decision = %s,
        ai_reasoning = %s
    WHERE id = %s
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

def log_activity(conversation_id, action):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        INSERT INTO activity_logs (conversation_id, action, created_at)
        VALUES (%s, %s, %s)
    """, (
        conversation_id,
        action,
        datetime.now(timezone.utc).isoformat()
    ))
 
    conn.commit()
    conn.close()
def get_activity(conversation_id):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT action, created_at
        FROM activity_logs
        WHERE conversation_id = %s AND user_id = %s
        ORDER BY created_at DESC
    """, (conversation_id, user_id))
 
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
def pause_tracking(conversation_id):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        UPDATE followups
        SET status = 'CLIENT_REPLY',
            updated_at = %s
        WHERE conversation_id = %s AND user_id = %s
    """, (datetime.now(timezone.utc), conversation_id, user_id))
 
    conn.commit()
    conn.close()

def resume_tracking(conversation_id):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc)
 
    # Get category + version
    cursor.execute("""
    SELECT category_name, category_version
    FROM followups
    WHERE conversation_id = %s AND user_id = %s
    """, (conversation_id, user_id))
    
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
        next_followup_at = %s,
        updated_at = %s
    WHERE conversation_id = %s AND user_id = %s
    AND status = 'CLIENT_REPLY'
    """, (
        next_time.isoformat(),
        now.isoformat(),
        conversation_id,
        user_id
    ))
    print("Rows Updated:",cursor.rowcount)
    print("Conversation_ID:",conversation_id)
 
    conn.commit()
    conn.close()
 
    log_activity(conversation_id, "Resumed Automatically")
def restart_followup(conversation_id,new_version=None):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc)
 
    # Get category to calculate next interval
    cursor.execute("""
        SELECT category_name,category_version FROM followups
        WHERE conversation_id = %s AND user_id = %s
    """, (conversation_id, user_id))
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
            category_version=%s,
            next_followup_at = %s,
            updated_at = %s
        WHERE conversation_id = %s AND user_id = %s
    """, (version,next_time, now, conversation_id, user_id))
 
    conn.commit()
    conn.close()

    log_activity(conversation_id,"Restarted by User")
def get_status(conversation_id):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT status FROM followups
    WHERE conversation_id = %s AND user_id = %s
    """, (conversation_id, user_id))
 
    row = cursor.fetchone()
    conn.close()
 
    return row[0] if row else None
def get_due_followups():
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc)
 
    cursor.execute("""
        SELECT message_id, conversation_id, category_name,category_version, attempt_count,last_followup_sent_at,original_recipients
        FROM followups
        WHERE status = 'ACTIVE'
        AND next_followup_at <= %s
        AND auto_followup_enabled=1
        AND user_id = %s
    """, (now, user_id))
 
    rows = cursor.fetchall()
    conn.close()
 
    return rows

def get_active_followups():
    user_id = get_current_user_id()
 
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
        WHERE status = 'ACTIVE' AND user_id = %s
    """, (user_id,))
 
    rows = cursor.fetchall()
 
    conn.close()
 
    return rows
def get_followups_by_status(status):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT subject, category_name, attempt_count,
               next_followup_at, updated_at
        FROM followups
        WHERE status = %s AND user_id = %s
        ORDER BY next_followup_at
    """, (status, user_id))
 
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_last_client_reply_time(conversation_id):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT last_client_reply_at FROM followups
    WHERE conversation_id = %s AND user_id = %s
    """, (conversation_id, user_id))
 
    row = cursor.fetchone()
    conn.close()
 
    return row[0] if row else None
def get_client_reply_followups():
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT message_id, conversation_id, category_name, category_version,
           attempt_count, last_followup_sent_at, original_recipients
    FROM followups
    WHERE status = 'CLIENT_REPLY' AND user_id = %s
    """, (user_id,))
 
    rows = cursor.fetchall()
    conn.close()
    return rows
def get_manual_paused_followups():
    user_id = get_current_user_id()
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
    WHERE status = 'MANUAL_PAUSED' AND user_id = %s
    """, (user_id,))
 
    rows = cursor.fetchall()
    conn.close()
 
    return rows

def insert_or_resume_followup(message, category_name,recipients_str):
    user_id = get_current_user_id()
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
        WHERE conversation_id = %s AND user_id = %s
    """, (message["conversationId"], user_id))
 
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
            user_id,
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
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        user_id,
        message["id"],
        message["conversationId"],
        category_name,
        version,
        subject,
        "ACTIVE",
        0,
        next_time,
        now,
        now,
        recipients_str
    ))
 
    conn.commit()
    conn.close()
    log_activity(message["conversationId"],"Inserted via Sync")
 
    return "inserted"