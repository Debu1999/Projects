from db import get_connection,get_current_user_id,convert_to_ist
from datetime import datetime,timezone

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
 
def get_settings(category_name,version):
    user_id=get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT followup_text, max_attempts, interval_minutes,followup_mode
        FROM settings
        WHERE user_id=%s AND category_name = %s AND version=%s
    """, (user_id, category_name, version))
 
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row
def save_settings(category_name, followup_text, max_attempts, interval_minutes,
                  followup_mode="manual", selected_draft_ids=None):
    from graph_client import get_draft_subject
 
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
 
    # ------------------------------------
    # Determine new version number
    # ------------------------------------
    latest_version = get_latest_category_version(category_name)
    new_version = latest_version + 1
 
    # ------------------------------------
    # Insert new settings version
    # ------------------------------------
    cursor.execute("""
        INSERT INTO settings
        (user_id, category_name, version, followup_text, max_attempts,
         interval_minutes, followup_mode, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        user_id,
        category_name,
        new_version,
        followup_text,
        max_attempts,
        interval_minutes,
        followup_mode,
        now
    ))
 
    # ------------------------------------
    # TEMPLATE HANDLING (snapshot)
    # ------------------------------------
    if followup_mode == "template" and selected_draft_ids:
 
        import re
 
        draft_list = [
            d.strip() for d in re.split(r"[;,|]", selected_draft_ids) if d.strip()
        ]
 
        print("Saving templates for category:", category_name, "version:", new_version,"user_id:", user_id)
 
        # Single template
        if len(draft_list) == 1:
 
            subject = get_draft_subject(draft_list[0]) or "No Subject"
 
            cursor.execute("""
                INSERT INTO category_templates
                (user_id, category_name, version, order_number, draft_id, draft_subject)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                category_name,
                new_version,
                1,
                draft_list[0],
                subject
            ))
 
        # Multiple templates
        else:
 
            for index, draft_id in enumerate(draft_list, start=1):
 
                subject = get_draft_subject(draft_id) or "No Subject"
 
                cursor.execute("""
                    INSERT INTO category_templates
                    (user_id, category_name, version, order_number, draft_id, draft_subject)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    category_name,
                    new_version,
                    index,
                    draft_id,
                    subject
                ))
 
    conn.commit()
    cursor.close()
    conn.close()
 
    return new_version
def get_latest_category_version(category_name):
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT MAX(version)
    FROM settings
    WHERE user_id = %s AND category_name = %s
    """, (user_id, category_name))
 
    row = cursor.fetchone()
    cursor.close()
    conn.close()
 
    return row[0] if row and row[0] else 0
def clone_category_version(category_name, source_version):
    user_id = get_current_user_id()
 
    conn = get_connection()
    cursor = conn.cursor()
 
    # get latest version safely
    cursor.execute("""
    SELECT MAX(version)
    FROM settings
    WHERE user_id=%s AND category_name=%s
    """,(user_id, category_name,))
 
    row = cursor.fetchone()
    latest_version = row[0] if row and row[0] else 0
    new_version = latest_version + 1
 
    now = datetime.now(timezone.utc)
 
    # copy settings
    cursor.execute("""
    INSERT INTO settings
    (user_id, category_name, version, followup_text, max_attempts,
     interval_minutes, followup_mode, updated_at)
 
    SELECT
    user_id,
    category_name,
    %s,
    followup_text,
    max_attempts,
    interval_minutes,
    followup_mode,
    %s
    FROM settings
    WHERE user_id=%s AND category_name=%s AND version=%s
    """,(new_version,now,user_id,category_name,source_version))
 
    # copy templates
    cursor.execute("""
    INSERT INTO category_templates
    (user_id,category_name,version,order_number,draft_id,draft_subject)
 
    SELECT
    user_id,
    category_name,
    %s,
    order_number,
    draft_id,
    draft_subject
    FROM category_templates
    WHERE user_id=%s AND category_name=%s AND version=%s
    """,(new_version,user_id,category_name,source_version))
 
    conn.commit()
    cursor.close()
    conn.close()
 
    return new_version
def get_all_categories():
    user_id = get_current_user_id()
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT category_name, version
    FROM settings
    WHERE user_id=%s
    ORDER BY category_name, version DESC
    """,(user_id,))
 
    rows = cursor.fetchall()
    conn.close()
 
    categories = {}
 
    for name, version in rows:
        if name not in categories:
            categories[name] = []
 
        categories[name].append(version)
 
    result = []
 
    for name, versions in categories.items():
        result.append({
            "name": name,
            "versions": versions
        })
 
    return result


def get_category_details(category_name,version):
    user_id = get_current_user_id()
 
    conn = get_connection()
    cursor = conn.cursor()
 
    # SETTINGS
    cursor.execute("""
    SELECT version,followup_text, max_attempts, interval_minutes,
    followup_mode, updated_at
    FROM settings
    WHERE user_id = %s
    AND category_name = %s
    AND version=%s
    """, (user_id, category_name, version))
 
    settings = cursor.fetchone()
 
    if not settings:
        conn.close()
        return None
 
    version,followup_text, max_attempts, interval_minutes, mode, updated_at = settings
 
 
    # STATUS COUNTS
    cursor.execute("""
    SELECT
        COUNT(*),
        SUM(CASE WHEN status='ACTIVE' THEN 1 ELSE 0 END),
        SUM(CASE WHEN status='CLIENT_REPLY' THEN 1 ELSE 0 END),
        SUM(CASE WHEN status='MANUAL_PAUSED' THEN 1 ELSE 0 END),
        SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END)
    FROM followups
    WHERE user_id = %s AND category_name = %s
    """, (user_id, category_name))
 
    stats = cursor.fetchone()
    total, active, client_paused,manual_paused, completed = stats or (0,0,0,0,0)
 
 
    # TEMPLATES
    cursor.execute("""
    SELECT order_number,draft_subject
    FROM category_templates
    WHERE user_id = %s 
    AND category_name = %s
    AND version=%s
    ORDER BY order_number
    """, (user_id, category_name, version))
 
    template_rows = cursor.fetchall()
    cursor.close()
    conn.close()
    templates=[
        {
            "order":row[0],
            "subject":row[1]
        }
        for row in template_rows
    ]
    # MODE LABEL
    if mode == "manual":
        mode_label = "Manual Text"
    elif len(templates) == 1:
        mode_label = "Single Template"
    elif len(templates) > 1:
        mode_label = f"Template Sequence ({len(templates)})"
    else:
        mode_label = "Template"
 
 
    updated = convert_to_ist(updated_at) if updated_at else None
 
 
    return {
        "category": category_name,
        "version":version,
        "interval_minutes": interval_minutes,
        "max_attempts": max_attempts,
        "mode": mode_label,
        "followup_text": followup_text,
        "templates": templates,
        "updated_at": updated,
        "stats": {
            "total": total or 0,
            "active": active or 0,
            "client_paused": client_paused or 0,
            "manual_paused":manual_paused or 0,
            "completed": completed or 0
        }
    }