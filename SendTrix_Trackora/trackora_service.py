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