def get_rows():
    #conn = sqlite3.connect(DB_NAME)
    user_id = get_current_user_id()
    conn=get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT f.id,
               f.subject,
               f.category_name,
               f.category_version,
               f.status,
               f.attempt_count,
               s.max_attempts,
               f.next_followup_at,
               f.last_followup_sent_at,
               f.updated_at,
               f.last_reply_subject,
               f.last_reply_body,
               f.last_client_email,
               f.is_unread_reply,
               f.conversation_id,
               f.last_reply_message_id,
               f.ai_draft_body,
               f.ai_draft_reasoning,
               f.ai_draft_status,
               f.auto_followup_enabled
        FROM followups f
        LEFT JOIN settings s
        ON f.user_id = s.user_id
        AND f.category_name = s.category_name
        AND f.category_version=s.version
        WHERE f.user_id = %s
        ORDER BY f.next_followup_at
    """, (user_id,))
 
    rows = cursor.fetchall()
    conn.close()
 
    formatted = []
    for row in rows:
        print("STATUS FROM DB:",row[4])
        formatted_row=(
            row[0],  # id
            row[1],  # subject
            f"{row[2]}(v{row[3]})",  # category + version
            row[4],  # status
            row[5],  # attempt_count
            row[6] if row[6] else 0,  # max_attempts
            convert_to_ist(row[7]),
            convert_to_ist(row[9]),
            convert_to_ist(row[8]),
            row[10],
            row[11],
            row[12],
            row[13],
            row[14],
            row[15],
            row[16],
            row[17],
            row[18],
            row[19]
            #print("Debug Message ID:",row[14])
        )
        print("COPYING CONVERSATION ID:",row[14])
        print("FORMATTED CONVERSATION ID:",formatted_row[13])
        formatted.append(formatted_row)
    return formatted
def get_dashboard_counts():
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("SELECT COUNT(*) FROM followups WHERE status = 'ACTIVE'")
    active = cursor.fetchone()[0]
 
    cursor.execute("SELECT COUNT(*) FROM followups WHERE status = 'COMPLETED'")
    completed = cursor.fetchone()[0]
 
    cursor.execute("SELECT COUNT(*) FROM followups WHERE status = 'CLIENT_REPLY'")
    client_reply = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM followups WHERE status = 'MANUAL_PAUSED'")
    manual_pause = cursor.fetchone()[0]
 
    cursor.execute("SELECT COUNT(*) FROM followups")
    total = cursor.fetchone()[0]
 
    conn.close()
 
    return active, completed, client_reply,manual_pause, total