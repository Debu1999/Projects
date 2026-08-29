def get_template_for_attempt(category_name,version,attempt_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT draft_id FROM category_templates
        WHERE category_name = %s AND version=%s 
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
    user_id = get_current_user_id()
 
    conn = get_connection()
 
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT primary_folder_id, secondary_folder_id
                FROM folder_settings
                WHERE user_id = %s
                AND primary_folder_id IS NOT NULL
                AND secondary_folder_id IS NOT NULL
                LIMIT 1
            """, (user_id,))
 
            row = cursor.fetchone()
 
        return row
 
    finally:
        conn.close()
def save_template_folders_settings(primary_folder_id, secondary_folder_id):
    print("Saving to DB:", primary_folder_id, secondary_folder_id)
 
    user_id = get_current_user_id()
 
    conn = get_connection()
 
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO folder_settings (
                    primary_folder_id,
                    secondary_folder_id,
                    user_id
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    primary_folder_id = EXCLUDED.primary_folder_id,
                    secondary_folder_id = EXCLUDED.secondary_folder_id
            """, (
                primary_folder_id,
                secondary_folder_id,
                user_id
            ))
 
        conn.commit()
 
    finally:
        conn.close()