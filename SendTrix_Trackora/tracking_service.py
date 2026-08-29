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