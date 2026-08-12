from db import get_connection

def run(evidence):
    """
    Database Worker
 
    Loads application details required for AI decision making.
    """
 
    evidence.setdefault("logs", []).append(
        "Database Worker started."
    )
 
    appser_number = evidence.get("appser_number")
 
    details = get_application_details(appser_number)
 
    if not details:
        evidence.setdefault("errors", []).append(
            "Application details not found."
        )
        return evidence
 
    evidence.update(details)
 
    evidence["logs"].append(
        "Application details loaded successfully."
    )
 
    return evidence
 

def get_application_details(appser_number):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    # Get active upload
    cursor.execute("""
        SELECT upload_id
        FROM master_control
        WHERE is_active = 1
    """)
 
    row = cursor.fetchone()
 
    if not row:
        conn.close()
        return None
 
    upload_id = row[0]
 
    cursor.execute("""
    SELECT
        compliance_mode,
        frequency,
        frequency_unit,
        review_start_date,
        next_due_date
    FROM application_analysis
    WHERE appser_number = ?
      AND upload_id = ?
    """, (appser_number, upload_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    details = {
    "compliance_mode": row[0] or "FREQUENCY",
    "frequency": row[1] or 0,
    "frequency_unit": row[2] or "days",
    "review_start_date": row[3] or "",
    "next_due_date": row[4] or ""
    }
    conn.close()
    return details
 