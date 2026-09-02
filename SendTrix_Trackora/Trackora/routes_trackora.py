from flask_server import app
import io,os,csv
import pandas as pd
from datetime import datetime, timedelta, timezone
from flask import render_template,request,jsonify,send_file
import requests
from openpyxl.utils import get_column_letter
from .trackora_nl_query import natural_language_to_sql,run_safe_query,is_safe_select
from db import get_connection, get_current_user_id
from Categories.category_service import get_template_folders
from Bulk_Email.draft_bulk_sender import send_bulk_from_draft
from graph_client import get_followup_drafts
from Bulk_Email.draft_bulk_sender import send_consolidated_from_draft
from .trackora_service import (
    get_recommended_action,
    get_send_mail_flag,
    run_comparison,
    run_compliance_engine,
    insert_raw_snapshot_bulk,
    insert_snapshot_bulk,
    ignore_all_changes_db,
    apply_all_changes_db,
    initialize_or_carry_analysis,
    carry_forward_mail_config,
    approve_change,
    ignore_change_db,
    get_comparison_files
)
@app.route("/nl_query", methods=["POST"])
def nl_query():
    print("=== NL QUERY ROUTE HIT ===", flush=True)
    question = request.form.get("question", "")

    result = natural_language_to_sql(question)
    print("Generated SQL:", result["sql"], flush=True)   # <-- this line was missing

    if not result["sql"]:
        return {"success": False, "error": result["explanation"]}

    query_result = run_safe_query(result["sql"], get_connection)

    return {
        "success": query_result["success"],
        "sql": result["sql"],
        "explanation": result["explanation"],
        "columns": query_result["columns"],
        "rows": query_result["rows"],
        "error": query_result["error"],
    }

@app.route("/nl_query/download", methods=["POST"])
def nl_query_download():
    sql = request.form.get("sql", "")

    if not is_safe_select(sql):
        return {"error": "Unsafe query, download blocked"}, 400

    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="trackora_query_results.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
@app.route("/applications")
def applications():
    return render_template("trackora_landing.html", title="")


@app.route("/applications/cots")
def applications_cots():
    conn = get_connection()
    cursor = conn.cursor()

    # Get all uploads
    cursor.execute("""
        SELECT id, file_name, created_at
        FROM uploads
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()

    # Get current master
    cursor.execute("""
        SELECT upload_id
        FROM master_control
        WHERE is_active = 1
        LIMIT 1
    """)
    row = cursor.fetchone()

    master_id = row[0] if row else None

    conn.close()

    uploads = []
    for r in rows:
        uploads.append({
            "id": r[0],
            "file_name": r[1],
            "created_at": r[2]
        })

    return render_template(
        "cots.html",
        uploads=uploads,
        master_exists=master_id is not None,
        master_id=master_id,
        title=""
    )

@app.route("/applications/demote-master", methods=["POST"])
def demote_master():
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        UPDATE master_control
        SET is_active = 0
        WHERE is_active = 1
    """)
 
    conn.commit()
    conn.close()
 
    return jsonify({"message": "Master removed successfully"})

@app.route("/applications/send-master-mails", methods=["POST"])
def send_master_mails():
 
    data = request.json
    items = data.get("items", [])
 
    if not items:
        return jsonify({"sent": 0, "failed": 0})
 
    from db import get_connection
    conn = get_connection()
    cursor = conn.cursor()
 
    # 🔹 Get active upload
    cursor.execute("SELECT upload_id FROM master_control WHERE is_active = 1")
    row = cursor.fetchone()
 
    if not row:
        return jsonify({"error": "No active master"})
 
    upload_id = row[0]
 
    # 🔹 Get draft folder (reuse existing bulk config)
    folders = get_template_folders()
    if not folders:
        return jsonify({"error": "Folder not configured"})
 
    primary_folder_id = folders[0]
    #consolidated_applications = []
 
    total_sent = 0
    total_failed = 0
 
 
    for item in items:
 
        asn = item.get("asn")
        draft_id = item.get("draft_id")
        category = item.get("category")

        cursor.execute("""
        SELECT send_status
        FROM application_analysis
        WHERE upload_id=%s AND appser_number=%s
        """, (upload_id, asn))
        status_row = cursor.fetchone()
        if status_row and status_row[0] in ("ACTIVE","SENDING"):
            continue
 
        # 🔹 Fetch full row
        cursor.execute("""
        SELECT
            s.appser_number,
            s.appser_name,
            s.appser_install_status,
            s.owner_name,
            s.tech_owner_name,
            s.current_installed_version,
            s.vendor_name,
            a.frequency,
            a.comments,
            a.internal_status
 
        FROM applications_snapshot s
        LEFT JOIN application_analysis a
        ON s.appser_number = a.appser_number
        AND s.upload_id = a.upload_id
 
        WHERE s.upload_id = %s AND s.appser_number = %s
        """, (upload_id, asn))
 
        row_data = cursor.fetchone()
 
        if not row_data:
            total_failed += 1
            continue
 
        # 🔹 Convert row → dict
        columns = [col[0] for col in cursor.description]
        raw_data = dict(zip(columns, row_data))
 
        # 🔹 Clean column names (so drafts are easy to write)
        mapping = {
            "appser_number": "asn",
            "appser_name": "name",
            "appser_install_status": "status",
            "owner_name": "owner",
            "tech_owner_name": "tech_owner",
            "current_installed_version": "version",
            "vendor_name": "vendor"
        }
 
        recipient = {}
 
        for key, value in raw_data.items():
            new_key = mapping.get(key, key)
            recipient[new_key] = value if value else ""
 
        # 🔹 Required for mail sending
        recipient["to"] = recipient.get("owner")
        recipient["cc"] = recipient.get("tech_owner")
 
        try:
            cursor.execute("""
            UPDATE application_analysis
            SET send_status='SENDING'
            WHERE upload_id=%s AND appser_number=%s
            """, (upload_id, asn))
            conn.commit()
            result = send_bulk_from_draft(
                draft_id,
                primary_folder_id,
                [recipient],   # same format as Excel
                category
            )
            successes=result.get("success",[])
            failures=result.get("failed",[])

            if successes:
                conversation_id=successes[0].get("conversation_id")
                
                cursor.execute("""
                UPDATE application_analysis
                SET send_status='ACTIVE',
                last_sent_at=%s,
                conversation_id=%s
                WHERE upload_id=%s AND appser_number=%s
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    conversation_id,
                    upload_id,
                    asn
                ))
                conn.commit()
            elif failures:
                cursor.execute("""
                UPDATE application_analysis
                SET send_status='NOT_SENT'
                WHERE upload_id=%s AND appser_number=%s
                """, (upload_id, asn))
                conn.commit()
 
            total_sent += len(successes)
            total_failed += len(failures)
        except Exception as e:
            print("MASTER MAIL ERROR:", str(e))
            cursor.execute("""
            UPDATE application_analysis
            SET send_status='NOT_SENT'
            WHERE upload_id=%s AND appser_number=%s
            """, (upload_id, asn))
            conn.commit()
 
            total_failed += 1
 
    conn.close()
 
    return jsonify({
        "sent": total_sent,
        "failed": total_failed
    })
@app.route("/applications/send-master-consolidated", methods=["POST"])
def send_master_consolidated():
 
    data = request.json or {}
    items = data.get("items", [])
 
    if not items:
        return jsonify({
            "sent": 0,
            "failed": 0,
            "error": "No applications selected"
        }), 400
 
    from db import get_connection
 
    conn = get_connection()
    cursor = conn.cursor()
 
    try:
 
        # --------------------------------
        # Get active master upload
        # --------------------------------
 
        cursor.execute("""
            SELECT upload_id
            FROM master_control
            WHERE is_active = 1
        """)
 
        row = cursor.fetchone()
 
        if not row:
            return jsonify({
                "sent": 0,
                "failed": 0,
                "error": "No active master"
            }), 400
 
        upload_id = row[0]
 
        # --------------------------------
        # Get draft folder
        # --------------------------------
 
        folders = get_template_folders()
 
        if not folders:
            return jsonify({
                "sent": 0,
                "failed": 0,
                "error": "Folder not configured"
            }), 400
 
        primary_folder_id = folders[0]
 
        # --------------------------------
        # Build application list
        # --------------------------------
 
        consolidated_applications = []
 
        for item in items:
 
            asn = item.get("asn")
 
            if not asn:
                continue
 
            cursor.execute("""
                SELECT
                    s.appser_number,
                    s.appser_name,
                    s.appser_install_status,
                    s.owner_name,
                    s.tech_owner_name,
                    s.current_installed_version,
                    s.vendor_name,
                    a.frequency,
                    a.comments,
                    a.internal_status
 
                FROM applications_snapshot s
 
                LEFT JOIN application_analysis a
                    ON s.appser_number = a.appser_number
                    AND s.upload_id = a.upload_id
 
                WHERE s.upload_id = %s
                AND s.appser_number = %s
            """, (upload_id, asn))
 
            row_data = cursor.fetchone()
 
            if not row_data:
                print("Application not found:", asn)
                continue
 
            columns = [
                col[0]
                for col in cursor.description
            ]
 
            raw_data = dict(
                zip(columns, row_data)
            )
 
            application = {
                "asn": raw_data.get("appser_number") or "",
                "name": raw_data.get("appser_name") or "",
                "status": raw_data.get("appser_install_status") or "",
                "owner": raw_data.get("owner_name") or "",
                "tech_owner": raw_data.get("tech_owner_name") or "",
                "version": raw_data.get("current_installed_version") or "",
                "vendor": raw_data.get("vendor_name") or "",
                "frequency": raw_data.get("frequency") or "",
                "comments": raw_data.get("comments") or "",
                "internal_status": raw_data.get("internal_status") or ""
            }
 
            consolidated_applications.append(application)
 
        print("====================================")
        print(
            "CONSOLIDATED APPLICATIONS:",
            len(consolidated_applications)
        )
        print(consolidated_applications)
        print("====================================")
 
        if not consolidated_applications:
            return jsonify({
                "sent": 0,
                "failed": 0,
                "error": "No valid applications found"
            }), 400
 
        # --------------------------------
        # Get selected draft/category
        # --------------------------------
 
        draft_id = items[0].get("draft_id")
        category_name = items[0].get("category")
 
        if not draft_id:
            return jsonify({
                "sent": 0,
                "failed": 0,
                "error": "No draft selected"
            }), 400
 
        # --------------------------------
        # Render consolidated email
        # --------------------------------
 
        result = send_consolidated_from_draft(
            draft_id=draft_id,
            folder_id=primary_folder_id,
            applications=consolidated_applications,
            category_name=category_name
        )
 
        print("====================================")
        print("CONSOLIDATED PREVIEW RESULT")
        print(result)
        print("====================================")
 
        return jsonify({
            "sent": 0,
            "failed": 0,
            "message": "Consolidated email rendered successfully",
            "preview": result.get("preview", {})
        })
 
    except Exception as e:
 
        print(
            "CONSOLIDATED MASTER ERROR:",
            str(e)
        )
 
        return jsonify({
            "sent": 0,
            "failed": len(items),
            "error": str(e)
        }), 500
 
    finally:
 
        conn.close()
@app.route("/applications/master-data")
def get_master_data():
    conn = get_connection()
    cursor = conn.cursor()
 
    # 🔹 Get active master
    cursor.execute("""
        SELECT upload_id FROM master_control
        WHERE is_active = 1
    """)
    row = cursor.fetchone()
 
    if not row:
        return jsonify([])
 
    upload_id = row[0]
    run_compliance_engine(upload_id)
 
    # 🔥 JOIN snapshot + analysis
    cursor.execute("""
        SELECT 
            s.appser_number,
            s.appser_name,
            s.so_u_sbg,
            s.owner_name,
            s.tech_owner_name,
            s.current_installed_version,
            s.vendor_name,
 
            a.frequency,
            a.frequency_unit,
            a.review_start_date,
            a.next_due_date,
            a.comments,
            a.internal_status,
            a.send_mail,
            a.compliance_mode,
            a.remediation_due_date,
            a.exception_reason,
            a.vendor_status,
            a.recommended_action,
            a.action_status,
            a.send_status,

            m.draft_id,
            m.category
 
        FROM applications_snapshot s
        LEFT JOIN application_analysis a
        ON s.appser_number = a.appser_number
        AND s.upload_id = a.upload_id

        LEFT JOIN application_mail_config m
        ON s.appser_number=m.appser_number
        AND s.upload_id=m.upload_id
 
 
        WHERE s.upload_id = %s
    """, (upload_id,))
 
    rows = cursor.fetchall()
    conn.close()
 
    data = []
    for r in rows:
        data.append({
            "asn": r[0],
            "name": r[1],
            "so_u_sbg": r[2],
            "owner": r[3],
            "tech_owner": r[4],
            "version": r[5],
            "vendor": r[6],
            "upload_id":upload_id,
 
            "frequency": r[7] or "",
            "frequency_unit":r[8] or "",
            "review_start_date": r[9].strftime("%Y-%m-%d") if r[9] else "",
            "next_due_date":r[10] or "",
            "comments": r[11] or "",
            "internal_status": r[12] or "",
            "send_mail": r[13] or 0,
            "compliance_mode":r[14] or "FREQUENCY",
            "remediation_due_date":r[15] or "",
            "exception_reason":r[16] or "",
            "vendor_status":r[17] or "",
            "recommended_action":r[18] or "",
            "action_status":r[19] or "",
            "send_status":r[20] or "",

            "draft_id":r[21] or "",
            "category":r[22] or "",
        })
    print(data[0])
 
    return jsonify(data)
@app.route("/applications/master-data/download", methods=["GET"])
def download_master_data():
    from db import get_connection
    import pandas as pd
    from io import BytesIO
    from flask import Response
    from .trackora_report_narrative import compute_compliance_summary, generate_summary_narrative

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT upload_id FROM master_control WHERE is_active = 1
    """)
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "No active master set"}), 400
    upload_id = row[0]

    # Same JOIN as get_master_data()
    cursor.execute("""
        SELECT
            s.appser_number, s.appser_name, s.so_u_sbg,
            s.owner_name, s.tech_owner_name, s.current_installed_version,
            s.vendor_name,
            a.compliance_mode, a.frequency, a.frequency_unit,
            a.review_start_date, a.remediation_due_date, a.next_due_date,
            a.exception_reason, a.comments, a.internal_status,
            a.vendor_status, a.recommended_action, a.action_status,
            a.send_status
        FROM applications_snapshot s
        LEFT JOIN application_analysis a
            ON s.appser_number = a.appser_number AND s.upload_id = a.upload_id
        WHERE s.upload_id = %s
    """, (upload_id,))

    rows = cursor.fetchall()

    columns = [
        "ASN", "Name", "SBG", "Owner", "Tech Owner", "Version", "Vendor",
        "Mode", "Frequency", "Frequency Unit", "Start Date", "Due Date",
        "Next Due Date", "Exception Reason", "Comments", "Internal Status",
        "Vendor Status", "Recommended Action", "Action Status", "Mail Status",
    ]
    df = pd.DataFrame(rows, columns=columns)
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    # --- NEW: compute summary + AI narrative ---
    summary = compute_compliance_summary(upload_id, conn)
    narrative = generate_summary_narrative(summary)
    conn.close()

    # Build a small summary dataframe for the new sheet
    summary_rows = [
        ["Total Applications", summary["total"]],
        ["Compliant", summary["compliant"]],
        ["Non-Compliant", summary["non_compliant"]],
        ["", ""],
        ["Breakdown by SBG", ""],
    ]
    for sbg, counts in summary["sbg_breakdown"].items():
        summary_rows.append([sbg, f"{counts['compliant']} compliant / {counts['non_compliant']} non-compliant"])

    summary_rows.append(["", ""])
    summary_rows.append(["Breakdown by Compliance Mode", ""])
    for mode, counts in summary["mode_breakdown"].items():
        summary_rows.append([mode, f"{counts['compliant']} compliant / {counts['non_compliant']} non-compliant"])

    summary_rows.append(["", ""])
    summary_rows.append(["Breakdown by Frequency", ""])
    for freq, counts in summary["freq_breakdown"].items():
        summary_rows.append([freq, f"{counts['compliant']} compliant / {counts['non_compliant']} non-compliant"])

    summary_rows.append(["", ""])
    summary_rows.append(["AI Summary", narrative])

    summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
    for col in summary_df.columns:
        if pd.api.types.is_datetime64_any_dtype(summary_df[col]):
            summary_df[col] = summary_df[col].dt.tz_localize(None)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        df.to_excel(writer, index=False, sheet_name="Master Analysis")
        # Auto-size columns on both sheets
        def safe_len(x):
            if pd.isna(x):
                return 0
            return len(str(x))

        for sheet_name, sheet_df in [("Summary", summary_df), ("Master Analysis", df)]:
            worksheet = writer.sheets[sheet_name]
            for i, col in enumerate(sheet_df.columns, start=1):
                if len(sheet_df) > 0:
                    max_len = max(sheet_df[col].apply(safe_len).max(), len(str(col)))
                else:
                    max_len = len(str(col))
                worksheet.column_dimensions[get_column_letter(i)].width = max_len + 4
    output.seek(0)

    filename = f"Trackora_Master_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route("/applications/save-mail-config", methods=["POST"])
def save_config():
    data = request.json
 
    upload_id = data["upload_id"]
    asn = data["asn"]
    draft = data.get("draft_id")
    category = data.get("category")
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    INSERT INTO application_mail_config (upload_id, appser_number, draft_id, category)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT(upload_id, appser_number)
    DO UPDATE SET draft_id = excluded.draft_id,
                  category = excluded.category
    """, (upload_id, asn, draft, category))
 
    conn.commit()
    conn.close()
 
    return jsonify({"status": "saved"})

 
@app.route("/applications/save-analysis", methods=["POST"])
def save_analysis():
    data = request.json
 
    upload_id = data.get("upload_id")
    appser_number = data.get("asn")
    frequency = data.get("frequency")
    
    comments = data.get("comments")
    internal_status = data.get("internal_status")
    send_mail = data.get("send_mail")
    vendor_status=data.get("vendor_status")
    compliance_mode = data.get(
        "compliance_mode",
        "FREQUENCY"
    )
    remediation_due_date = data.get(
        "remediation_due_date"
    )
    review_start_date=data.get("review_start_date")
    print("SAVE_DEBUG:",frequency,review_start_date,internal_status)
    frequency_unit=data.get("frequency_unit","days")
    exception_reason = data.get(
        "exception_reason"
    )
 
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc)
 
    # ==========================================
    # COMPLIANCE DATE LOGIC
    # ==========================================
    next_due_date = None
    last_reviewed_date = None
    # ------------------------------------------
    # FREQUENCY MODE
    # ------------------------------------------
    if (compliance_mode=="FREQUENCY" and frequency and internal_status == "Compliant"and review_start_date):
        print("Entered frequency block")
        try:
            freq_days = int(frequency)
        except:
            freq_days = 30
        if frequency_unit=="minutes":
            start_dt=now
        else:
            try:
                start_dt = datetime.fromisoformat(str(review_start_date))
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
            except Exception as e:
                print("Failed to parse review_start_date, falling back to now:", e)
                start_dt = now
        last_reviewed_date = review_start_date
        if frequency_unit == "minutes":
            next_due_date = (
                start_dt + timedelta(minutes=freq_days)
            ).isoformat()
        else:
            next_due_date = (
                start_dt + timedelta(days=freq_days)
            ).isoformat()
            print("NEXT_DUE_DATE:",next_due_date)
    # ------------------------------------------
    # DATE BASED MODE
    # ------------------------------------------
    elif (compliance_mode=="DATE_BASED" and remediation_due_date):
        due_dt=datetime.fromisoformat(remediation_due_date)
        due_dt=due_dt.replace(hour=23,minute=59,second=59)
        next_due_date = due_dt.isoformat()
        print("DATE_MODE_DUE:",next_due_date)
        last_reviewed_date = now.isoformat()

    recommended_action=get_recommended_action(internal_status,vendor_status)
    send_mail=get_send_mail_flag(recommended_action)
    cursor.execute("""
    SELECT
    recommended_action,
    action_status
    FROM application_analysis
    WHERE upload_id = %s
    AND appser_number = %s
    """, (
        upload_id,
        appser_number
    ))
    existing = cursor.fetchone()
    action_status = "NONE"
    pending_actions = [
    "SEND_EVIDENCE_REQUEST",
    "REQUEST_FOR_EVIDENCE_WITH_TIMESTAMP",
    "WAIT_FOR_VENDOR_ETA",
    "WAIT_FOR_DUE_DATE"
    ]
    if recommended_action in pending_actions:
        if existing:
            old_recommended_action = existing[0]
            old_action_status = existing[1]
            if old_recommended_action == recommended_action:
                action_status = old_action_status or "PENDING"
            else:
                action_status = "PENDING"
        else:
            action_status = "PENDING"
 

 
    # UPSERT logic (UPDATED)
    cursor.execute("""
    INSERT INTO application_analysis (
        upload_id, appser_number,
        frequency,frequency_unit, comments, internal_status, send_mail,compliance_mode,remediation_due_date,exception_reason,
        last_reviewed_date, next_due_date, updated_at,vendor_status,recommended_action,action_status,review_start_date
    )
    VALUES (%s, %s, %s, %s,%s, %s, %s, %s, %s, %s,%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT(upload_id, appser_number)
    DO UPDATE SET
        frequency=excluded.frequency,
        frequency_unit=excluded.frequency_unit,
        comments=excluded.comments,
        internal_status=excluded.internal_status,
        send_mail=excluded.send_mail,
        compliance_mode=excluded.compliance_mode,
        remediation_due_date=excluded.remediation_due_date,
        exception_reason=excluded.exception_reason,
        last_reviewed_date=COALESCE(excluded.last_reviewed_date, application_analysis.last_reviewed_date),
        next_due_date=COALESCE(excluded.next_due_date, application_analysis.next_due_date),
        updated_at=excluded.updated_at,
        vendor_status=excluded.vendor_status,
        recommended_action=excluded.recommended_action,
        action_status=excluded.action_status,
        review_start_date=excluded.review_start_date
    """, (
        upload_id, appser_number,
        frequency,frequency_unit, comments, internal_status, send_mail,
        compliance_mode,remediation_due_date,exception_reason,
        last_reviewed_date, next_due_date,
        now.isoformat(),vendor_status,recommended_action,action_status,review_start_date
    ))
 
    conn.commit()
    conn.close()
 
    return jsonify({
        "message": "Saved",
        "recommended_action":recommended_action,
        "send_mail":send_mail,
        "action_status":action_status
    })
@app.route("/rename-upload/<int:upload_id>", methods=["POST"])
def rename_upload(upload_id):
 
    data = request.json
    new_name = data.get("file_name","").strip()
    if not new_name:
        conn.close()
        return jsonify({
            "message": "File name cannot be empty"
        }), 400
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT file_name
        FROM uploads
        WHERE id = %s
    """, (upload_id,))
 
    row = cursor.fetchone()
 
    if not row:
        conn.close()
        return jsonify({
            "message": "Upload not found"
        }), 404
 
    old_name = row[0]
    old_ext = os.path.splitext(old_name)[1]
    if not new_name.lower().endswith(old_ext.lower()):
        new_name += old_ext
    cursor.execute("""
    UPDATE uploads
    SET file_name = %s
    WHERE id = %s
    """, (
        new_name,
        upload_id
    ))
    conn.commit()
    conn.close()
    return jsonify({
        "message":"File renamed successfully"
    })
@app.route("/delete-upload/<int:upload_id>", methods=["POST"])
def delete_upload(upload_id):
 
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT stored_name
    FROM uploads
    WHERE id = %s
    """, (upload_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({
            "message": "Upload not found"
        }), 404
    stored_name = row[0]
    file_path = os.path.join("uploads", stored_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    cursor.execute("""
    DELETE FROM master_control
    WHERE upload_id = %s
    """, (upload_id,))

    cursor.execute("""
    DELETE FROM applications_snapshot
    WHERE upload_id = %s
    """, (upload_id,))
    
    cursor.execute("""
    DELETE FROM applications_raw_data
    WHERE upload_id = %s
    """, (upload_id,))
    
    cursor.execute("""
    DELETE FROM uploads
    WHERE id = %s
    """, (upload_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "message": "Upload deleted successfully"
    })
@app.route("/applications/update-change-status", methods=["POST"])
def update_change_status():
 
    from db import get_connection
 
    data = request.json
 
    change_id = data.get("change_id")
    status = data.get("status")
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    UPDATE comparison_changes
    SET approval_status = %s
    WHERE id = %s
    """, (status, change_id))
 
    conn.commit()
    conn.close()
 
    return jsonify({
        "success": True
    })
 

@app.route("/applications/get-drafts")
def get_master_drafts():
    folders = get_template_folders()
 
    if not folders:
        return jsonify([])
 
    primary_folder_id = folders[0]
 
    drafts_response = get_followup_drafts(primary_folder_id)
    drafts = drafts_response.get("value", [])
 
    result = []
 
    for d in drafts:
        result.append({
            "id": d.get("id"),
            "subject": d.get("subject", "No Subject")
        })
 
    return jsonify(result)

@app.route("/applications/set-master/<int:upload_id>", methods=["POST"])
def set_master(upload_id):
    from db import get_connection
 
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
 
    # 🔹 Get current active master (if any)
    cursor.execute("""
        SELECT upload_id FROM master_control
        WHERE is_active = 1
    """)
    row = cursor.fetchone()
    if row:
        old_master_id=row[0]
    else:
        old_master_id=upload_id
 
    # ❌ Remove existing master
    cursor.execute("""
        UPDATE master_control
        SET is_active = 0
        WHERE is_active = 1
    """)
 
    # ✅ Set new master
    cursor.execute("""
        INSERT INTO master_control (upload_id, is_active, created_at)
        VALUES (%s, 1, %s)
    """, (upload_id, now))
 
    conn.commit()
    conn.close()
 
    # 🔥 NEW: Initialize or carry forward analysis
    #initialize_or_carry_analysis(old_master_id, upload_id)
    #carry_forward_mail_config(old_master_id,upload_id)
    #carry_forward_meetings(old_master_id,upload_id)

    run_compliance_engine(upload_id)
 
    return jsonify({"message": "Master set successfully"})

@app.route("/applications/compare/<int:upload_id>", methods=["POST"])
def compare_upload(upload_id):
    from db import get_connection
    #from comparison import run_comparison
 
    conn = get_connection()
    cursor = conn.cursor()
 
    # ✅ Get active master
    cursor.execute("""
    SELECT upload_id FROM master_control
    WHERE is_active = 1
    LIMIT 1
    """)
 
    row = cursor.fetchone()
    conn.close()
 
    if not row:
        return jsonify({"error": "No master selected"}), 400
 
    master_upload_id = row[0]
    print("MASTER_UPLOAD_ID:", master_upload_id)
    print("TARGET_UPLOAD_ID:", upload_id)
 
    comparison_id = run_comparison(master_upload_id, upload_id)
    
    return jsonify(
        {
            "message":"Comparison Completed",
            "comparison_id":comparison_id
        }
    )
@app.route("/applications/comparison-files")
def comparison_files():
    return jsonify(get_comparison_files())

@app.route("/applications/comparison-data/<int:comparison_id>", methods=["GET"])
def get_comparison_data(comparison_id):
 
    from db import get_connection
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
    SELECT
        id,
        appser_number,
        field_name,
        old_value,
        new_value,
        change_type,
        approval_status
    FROM comparison_changes
    WHERE comparison_id = %s
    ORDER BY id DESC
    """, (comparison_id,))
 
    rows = cursor.fetchall()
 
    conn.close()
 
    data = []
 
    for r in rows:
 
        data.append({
            "id": r[0],
            "asn": r[1],
            "field": r[2],
            "old": r[3],
            "new": r[4],
            "type": r[5],
            "status": r[6]
        })
 
    return jsonify(data)
@app.route(
    "/applications/review-data/<int:comparison_id>",
    methods=["GET"]
)
def get_review_data(comparison_id):
 
    from db import get_connection
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT
            appser_number,
            COUNT(*) as change_count,
            MAX(change_type) as change_type,
            MAX(approval_status) as approval_status
        FROM comparison_changes
        WHERE comparison_id = %s
        GROUP BY appser_number
        ORDER BY appser_number
    """, (comparison_id,))
 
    rows = cursor.fetchall()
    conn.close()
 
    data = []
 
    for r in rows:
        data.append({
            "asn": r[0],
            "change_count": r[1],
            "type": r[2],
            "status": r[3]
        })
 
    return jsonify(data)
@app.route(
    "/applications/asn-changes/<int:comparison_id>/<asn>",
    methods=["GET"]
)
def get_asn_changes(comparison_id, asn):
 
    from db import get_connection
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT
        id,
        field_name,
        old_value,
        new_value,
        change_type,
        approval_status
        FROM comparison_changes
        WHERE comparison_id = %s
        AND appser_number = %s
        ORDER BY field_name
    """, (
        comparison_id,
        asn
    ))
 
    rows = cursor.fetchall()
 
    conn.close()
 
    data = []
 
    for r in rows:
        data.append({
            "id":r[0],
            "field": r[1],
            "old": r[2],
            "new": r[3],
            "type": r[4],
            "status": r[5]
        })
 
    return jsonify(data)
 
@app.route("/applications/apply-change/<int:change_id>", methods=["POST"])
def apply_change(change_id):
 
    approve_change(change_id)
 
    return jsonify({
        "message": "Change applied"
    })
 
@app.route("/applications/ignore-change/<int:change_id>", methods=["POST"])
def ignore_change(change_id):
 
    ignore_change_db(change_id)
 
    return jsonify({
        "message": "Change ignored"
    })
@app.route(
    "/applications/apply-all/<int:comparison_id>",
    methods=["POST"]
)
def apply_all_changes(comparison_id):
 
    apply_all_changes_db(comparison_id)
 
    return jsonify({
        "message": "All changes applied"
    })
 
@app.route(
    "/applications/ignore-all/<int:comparison_id>",
    methods=["POST"]
)
def ignore_all_changes(comparison_id):
 
    ignore_all_changes_db(comparison_id)
 
    return jsonify({
        "message": "All changes ignored"
    })
 
@app.route("/applications/download-final/<int:comparison_id>")
def download_final_excel(comparison_id):
 
    from excel_report import (
        generate_excel_from_upload
    )
 
 
    conn = get_connection()
    cursor = conn.cursor()
 
    # =====================================
    # GET CONSOLIDATED UPLOAD
    # =====================================
 
    cursor.execute("""
    SELECT id
    FROM uploads
    WHERE comparison_id = %s
    AND file_type = 'CONSOLIDATED'
    ORDER BY id DESC
    LIMIT 1
    """, (comparison_id,))
 
    row = cursor.fetchone()
 
    conn.close()
 
    if not row:
 
        return jsonify({
            "error": "No consolidated sheet found"
        }), 404
 
    upload_id = row[0]
 
    # =====================================
    # GENERATE EXCEL FROM CONSOLIDATED DATA
    # =====================================
 
    excel_path = generate_excel_from_upload(
        upload_id,
        comparison_id
    )
 
    return send_file(
        excel_path,
        as_attachment=True
    )
 
@app.route(
    "/applications/generate-consolidated/<int:comparison_id>",
    methods=["POST"]
)
def generate_consolidated(comparison_id):
 
    from excel_report import (
        create_upload_from_comparison
    )
 
    from db import get_connection
 
    conn = get_connection()
    cursor = conn.cursor()
 
    # =====================================
    # GET COMPARISON DETAILS
    # =====================================
 
    cursor.execute("""
    SELECT
        from_upload_id,
        to_upload_id
    FROM comparison_logs
    WHERE id = %s
    """, (comparison_id,))
 
    row = cursor.fetchone()
 
    conn.close()
 
    if not row:
        return jsonify({
            "error": "Comparison not found"
        }), 404
 
    master_upload_id = row[0]
    target_upload_id = row[1]
 
    # =====================================
    # CREATE CONSOLIDATED UPLOAD
    # =====================================
 
    new_upload_id = (
        create_upload_from_comparison(
            comparison_id,
            master_upload_id,
            target_upload_id
        )
    )
    initialize_or_carry_analysis(master_upload_id,new_upload_id)
    carry_forward_mail_config(master_upload_id,new_upload_id)
    #carry_forward_meetings(master_upload_id,new_upload_id)
 
    return jsonify({
        "message": "Consolidated sheet generated",
        "upload_id": new_upload_id
    })
@app.route("/upload", methods=["POST"])
def upload_application_file():
    import time
    import os
    user_id=get_current_user_id()
 
    file = request.files.get("file")

    if not file:
        return jsonify({"message": "No file uploaded"}), 400

    allowed = [".csv", ".xlsx"]
    if not any(file.filename.lower().endswith(ext)for ext in allowed):
        return jsonify({
            "message":"Only CSV and XLSX files are supported"
        }), 400
 
    UPLOAD_FOLDER = "uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
 
    original_name = file.filename
    unique_name = f"{int(time.time())}_{file.filename}"
 
    file_path = os.path.join(UPLOAD_FOLDER, unique_name)
 
    # ✅ Save permanently
    file.save(file_path)
 
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc).isoformat()
 
    # ✅ Save upload record
    cursor.execute("""
    INSERT INTO uploads (file_name, stored_name, created_at,user_id)
    VALUES (%s, %s, %s,%s)RETURNING id
    """, (original_name, unique_name, now, user_id))
 
    upload_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
 
    # ✅ Insert snapshot data
    count = 0
    conn=get_connection()
    cursor=conn.cursor()
 
    if file.filename.lower().endswith(".csv"):
        with open(file_path,newline='',encoding='latin-1') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get("appser_number"):
                    insert_snapshot_bulk(cursor,upload_id, row)
                    insert_raw_snapshot_bulk(cursor,upload_id, row)
                    count += 1
    elif file.filename.lower().endswith(".xlsx"):
        df = pd.read_excel(file_path)
        df = df.fillna("")
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            if row_dict.get("appser_number"):
                insert_snapshot_bulk(cursor,upload_id,row_dict)
                insert_raw_snapshot_bulk(cursor,upload_id,row_dict)
                count += 1
    conn.commit()
    cursor.execute("""
    SELECT COUNT(*)
    FROM applications_raw_data
    WHERE upload_id = %s AND user_id = %s
    """, (upload_id, user_id))
    raw_count = cursor.fetchone()[0]
    
    cursor.execute("""
    SELECT COUNT(*)
    FROM applications_snapshot
    WHERE upload_id = %s AND user_id = %s
    """, (upload_id, user_id))
    snapshot_count = cursor.fetchone()[0]
    
    print(
        "UPLOAD COMPLETE:",
        upload_id,
        "RAW:",
        raw_count,
        "SNAPSHOT:",
        snapshot_count
    )
    conn.close()

    return jsonify({
        "message": "Upload successful",
        "upload_id": upload_id,
        "records_inserted": count
    })