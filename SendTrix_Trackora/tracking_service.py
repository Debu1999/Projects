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