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