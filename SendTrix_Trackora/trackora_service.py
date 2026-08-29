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
