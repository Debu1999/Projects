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
        VALUES (%s, %s, 'MANUAL', 'ACTIVE', %s, %s)RETURNING id
    """, (
        workspace_name.strip(),
        description.strip(),
        now,
        now
    ))
 
    workspace_id = cursor.fetchone()[0]
 
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
            SET workspace_name = %s,
                updated_at = %s
            WHERE id = %s
        """, (
            workspace_name.strip(),
            now,
            workspace_id
        ))
 
    else:
 
        cursor.execute("""
            UPDATE workspaces
            SET workspace_name = %s,
                description = %s,
                updated_at = %s
            WHERE id = %s
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
            updated_at = %s
        WHERE id = %s
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
        WHERE id = %s
        AND status = 'ACTIVE'
    """, (workspace_id,))
 
    if not cursor.fetchone():
        conn.close()
        raise Exception("Workspace not found.")
 
    # Conversation can belong to only ONE workspace
    cursor.execute("""
        SELECT workspace_id
        FROM workspace_conversations
        WHERE conversation_id = %s
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
        VALUES (%s, %s, %s)
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
        WHERE id = %s
        AND status = 'ACTIVE'
    """, (new_workspace_id,))
 
    if not cursor.fetchone():
        conn.close()
        raise Exception("Target workspace not found.")
 
    cursor.execute("""
        UPDATE workspace_conversations
        SET workspace_id = %s,
            assigned_at = %s
        WHERE conversation_id = %s
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
        WHERE conversation_id = %s
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
        WHERE wc.workspace_id = %s
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
def get_workspace_rows(workspace_id):
 
    rows = get_rows()
 
    workspace_conversations = get_workspace_conversations(
        workspace_id
    )
 
    conversation_ids = {
        str(item["conversation_id"])
        for item in workspace_conversations
    }
 
    print("===================================")
    print("WORKSPACE ID:", workspace_id)
    print("WORKSPACE CONVERSATIONS:", workspace_conversations)
    print("WORKSPACE CONVERSATION IDS:", conversation_ids)
 
    print("ALL SENDTRIX ROW IDS:")
 
    for row in rows:
        print(
            "ID:",
            row[13],
            "TYPE:",
            type(row[13])
        )
 
    print("===================================")
 
    filtered_rows = [
        row
        for row in rows
        if str(row[13]) in conversation_ids
    ]
 
    print(
        "MATCHED WORKSPACE ROWS:",
        len(filtered_rows)
    )
 
    return filtered_rows
def get_workspace_conversation_ids(workspace_id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT conversation_id
        FROM workspace_conversations
        WHERE workspace_id = %s
    """, (workspace_id,))
 
    rows = cursor.fetchall()
    conn.close()
 
    return [row[0] for row in rows]
 