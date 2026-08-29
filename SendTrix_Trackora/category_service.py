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
