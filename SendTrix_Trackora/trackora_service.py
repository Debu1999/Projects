def upsert_application(app_data):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
 
    cursor.execute("""
    INSERT INTO applications (
        appser_name,
        appser_number,
        appser_install_status,
        so_u_sbg,
        owner_name,
        tech_owner_name,
        current_installed_version,
        vendor_name,
        reviewer_id,
        reviewed_date,
        u_run_operations_focal,
        comments,
        verified_reviewed_date,
        internal_compliance_status,
        created_at,
        updated_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
 
    ON CONFLICT(appser_number) DO UPDATE SET
        appser_name=excluded.appser_name,
        appser_install_status=excluded.appser_install_status,
        so_u_sbg=excluded.so_u_sbg,
        owner_name=excluded.owner_name,
        tech_owner_name=excluded.tech_owner_name,
        current_installed_version=excluded.current_installed_version,
        vendor_name=excluded.vendor_name,
        reviewer_id=excluded.reviewer_id,
        reviewed_date=excluded.reviewed_date,
        u_run_operations_focal=excluded.u_run_operations_focal,
        updated_at=excluded.updated_at
    """, (
        app_data.get("appser_name"),
        app_data.get("appser_number"),
        app_data.get("appser_install_status"),
        app_data.get("so_u_sbg"),
        app_data.get("owner_name"),
        app_data.get("tech_owner_name"),
        app_data.get("current_installed_version"),
        app_data.get("vendor_name"),
        app_data.get("reviewer_id"),
        now,  # reviewed_date updated on upload
        app_data.get("u_run_operations_focal"),
        app_data.get("comments"),
        None,  # verified_reviewed_date (manual later)
        "Compliant",  # default
        now,
        now
    ))
 
    conn.commit()
    conn.close()
def insert_snapshot_bulk(cursor, upload_id, row):
 
    now = datetime.now(timezone.utc).isoformat()
 
    if not row.get("appser_number"):
        return
 
    cursor.execute("""
    INSERT INTO applications_snapshot (
        upload_id,
        appser_number,
        appser_name,
        appser_install_status,
        so_u_sbg,
        owner_name,
        tech_owner_name,
        current_installed_version,
        vendor_name,
        reviewer_id,
        reviewed_date,
        u_run_operations_focal,
        compliance_mode,
        remediation_due_date,
        exception_reason,
        status,
        created_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s)
    """, (
        upload_id,
        row.get("appser_number"),
        row.get("appser_name"),
        row.get("appser_install_status"),
        row.get("so_u_sbg"),
        row.get("owner_name"),
        row.get("tech_owner_name"),
        row.get("current_installed_version"),
        row.get("vendor_name"),
        row.get("reviewer_id"),
        now,
        row.get("u_run_operations_focal"),
        row.get("compliance_mode", "FREQUENCY"),
        row.get("remediation_due_date", ""),
        row.get("exception_reason", ""),
        now
    ))

def insert_raw_snapshot_bulk(
    cursor,
    upload_id,
    row
):
 
    import json
    from datetime import datetime, timezone
 
    now = datetime.now(
        timezone.utc
    ).isoformat()
 
    appser_number = str(
        row.get("appser_number", "")
    ).strip()
 
    cursor.execute("""
    INSERT INTO applications_raw_data (
        upload_id,
        appser_number,
        row_data,
        created_at
    )
    VALUES (%s, %s, %s, %s)
    """, (
        upload_id,
        appser_number,
        json.dumps(row,default=str),
        now
    ))
def get_latest_external_responder(asn):
    from graph_client import get_current_user_email,get_messages_in_conversation
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT upload_id
    FROM master_control
    WHERE is_active = 1
    """)
 
    row = cursor.fetchone()
 
    if not row:
        return None
 
    upload_id = row[0]
 
    cursor.execute("""
    SELECT conversation_id
    FROM application_analysis
    WHERE upload_id = %s
    AND appser_number = %s
    """, (
        upload_id,
        asn
    ))
 
    conv_row = cursor.fetchone()
 
    conn.close()
 
    if not conv_row:
        return None
 
    conversation_id = conv_row[0]
 
    messages = get_messages_in_conversation(conversation_id)
    messages.sort(key=lambda x: x.get("receivedDateTime", ""),reverse=True)
    MY_EMAIL = get_current_user_email().lower()
    for msg in messages:
        sender = (
            msg.get("from", {})
            .get("emailAddress", {})
        )
        sender_email = (
            sender.get("address", "")
            .lower()
            .strip()
        )
        if sender_email != MY_EMAIL:
            return {
                "name": sender.get("name"),
                "email": sender.get("address")
            }
    return None
def save_comment(appser_number, version_id, comment):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
 
    cursor.execute("""
    INSERT INTO application_comments (
        appser_number,
        version_id,
        comment,
        created_at
    ) VALUES (%s, %s, %s, %s)
    """, (appser_number, version_id, comment, now))
 
    conn.commit()
    conn.close()
def get_snapshot_by_upload(upload_id):
 
    import json
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT appser_number, row_data
    FROM applications_raw_data
    WHERE upload_id = %s
    """, (upload_id,))
 
    rows = cursor.fetchall()
 
    conn.close()
 
    result = {}
 
    for row in rows:
 
        appser_number = row[0]
 
        try:
            row_data = json.loads(row[1])
        except:
            row_data = {}
 
        result[appser_number] = row_data
    print(
    "UPLOAD:",
    upload_id,
    "DB_ROWS:",
    len(rows),
    "DICT_ROWS:",
    len(result))
 
    return result
def create_comparison(cursor,master_upload_id, target_upload_id,master_count,target_count):
    now = datetime.now(timezone.utc).isoformat()
 
    cursor.execute("""
        INSERT INTO comparison_logs (from_upload_id,to_upload_id,created_at,master_count,target_count)
        VALUES (%s, %s, %s, %s, %s)
    """, (master_upload_id,target_upload_id, now,master_count,target_count))
 
    return cursor.fetchone()[0]
def update_comparison_summary(
    comparison_id,
    added_count,
    modified_count,
    missing_count
):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        UPDATE comparison_logs
        SET
            added_count = %s,
            modified_count = %s,
            missing_count = %s
        WHERE id = %s
    """, (
        added_count,
        modified_count,
        missing_count,
        comparison_id
    ))
 
    conn.commit()
    conn.close()
def comparison_exists(master_upload_id, target_upload_id):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT id
        FROM comparison_logs
        WHERE from_upload_id = %s
        AND to_upload_id = %s
    """, (
        master_upload_id,
        target_upload_id
    ))
 
    row = cursor.fetchone()
 
    conn.close()
 
    return row[0] if row else None

def run_comparison(master_upload_id, target_upload_id):
    from datetime import datetime, timezone

    print("MASTER_UPLOAD_ID:",master_upload_id)
    print("TARGET_UPLOAD_ID:",target_upload_id)
    old_data = get_snapshot_by_upload(master_upload_id)
    new_data = get_snapshot_by_upload(target_upload_id)
    print("OLD COUNT:", len(old_data))
    print("NEW COUNT:", len(new_data))
    master_count=len(old_data)
    target_count=len(new_data)
    
    print("ASN0001470 IN OLD:",
      "ASN0001470" in old_data)
    print("ASN0001470 IN NEW:",
      "ASN0001470" in new_data)
 
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
    existing=comparison_exists(
        master_upload_id,
        target_upload_id
    )
    print("EXISTING_COMPARISON:",existing)
    if existing:
        return existing
    # ✅ Create comparison
    comparison_id = create_comparison(cursor, master_upload_id, target_upload_id,master_count,target_count)
 
    changes = []
 
    added = 0
    modified = 0
    missing = 0
 
    # 🔹 ADDED & MODIFIED
    for asn, new_row in new_data.items():
        # =========================
        # ADDED APPLICATION
        # =========================
        if asn not in old_data:
            changes.append((
                comparison_id,
                asn,
                "-",
                "-",
                "New Record",
                "ADDED",
                now,
                json.dumps(new_row)
            ))
            added += 1
        # =========================
        # MODIFIED APPLICATION
        # =========================
        else:
            old_row = old_data[asn]
            for field in new_row:
                old_value = str(old_row.get(field) or "").strip()
                new_value = str(new_row.get(field) or "").strip()
                # Skip ASN itself
                if field == "appser_number":
                    continue
                if old_value != new_value:
                    changes.append((
                        comparison_id,
                        asn,
                        field,
                        old_value,
                        new_value,
                        "MODIFIED",
                        now,
                        None
                    ))
                    modified += 1
    # 🔹 MISSING

    for asn in old_data:
        if asn not in new_data:
            changes.append((
                comparison_id, asn, "-", "Exists", "Missing", "MISSING", now,None
            ))
            missing += 1
 
    # ✅ BULK INSERT (VERY IMPORTANT)
    
    cursor.executemany("""
        INSERT INTO comparison_changes (
            comparison_id,
            appser_number,
            field_name,
            old_value,
            new_value,
            change_type,
            created_at,
            row_data
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, changes)
 
    conn.commit()
    conn.close()
 
    # Optional summary
    update_comparison_summary(comparison_id, added, modified, missing)
 
    return comparison_id