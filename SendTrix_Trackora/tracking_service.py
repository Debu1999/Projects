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