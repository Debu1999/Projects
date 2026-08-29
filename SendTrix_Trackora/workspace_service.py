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