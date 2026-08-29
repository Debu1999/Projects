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
