from flask_server import app
from Tracking.sendtrix_service import get_rows,get_dashboard_counts
from Tracking.tracking_service import (
    get_unread_replies,
    log_activity,
    get_all_activity,
    get_ai_draft,
    update_ai_draft_status,
    restart_followup,
    get_activity,
    save_ai_draft,
    ignore_reply
)
from graph_client import get_graph_token,send_followup_reply_manual
from agent_service import clean_email_body,analyze_reply,rephrase_draft_body
from process import process,refresh_conversations
from sync_categories import sync
from db import get_connection
from datetime import datetime,timezone
from flask import render_template, redirect, url_for, flash, request

@app.route("/")
def dashboard():
    search=request.args.get("search","")
    rows=get_rows()
    unread_replies=get_unread_replies()
 
    active, completed, client_reply,manual_pause, total = get_dashboard_counts()
 
    print("Counts:", active, completed, client_reply,manual_pause, total)
 
    return render_template(
        "dashboard.html",
        rows=rows,
        active_count=active,
        completed_count=completed,
        client_reply_count=client_reply,
        manual_pause_count=manual_pause,
        total_count=total,
        unread_replies=unread_replies,
        search=search
    )
@app.route("/run")
def run_process():
    try:
        get_graph_token()
    except:
        flash("Please login to Microsoft first.")
        return redirect(url_for("login_microsoft"))
 
    process()
    flash("Followup process executed successfully.")
    return redirect(url_for("dashboard"))
@app.route("/sync")
def run_sync():
    sync()
    #debug_followups()
    flash("Mailbox sync completed successfully.")
    return redirect(url_for("dashboard"))
@app.route("/refresh")
def refresh_process():
 
    try:
        get_graph_token()
    except:
        flash("Please login to Microsoft first.")
        return redirect(url_for("login_microsoft"))
 
    refresh_conversations()
 
    flash("Conversations refreshed successfully.")
    return redirect(url_for("dashboard"))

@app.route("/pause/<int:id>")
def pause(id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        UPDATE followups
        SET status='MANUAL_PAUSED', updated_at=?
        WHERE id=?
    """, (datetime.now(timezone.utc), id))
 
    conn.commit()
    conn.close()

    log_activity(id,"Paused by User")
 
    flash(f"Followup ID {id} paused successfully.")
    return redirect(url_for("dashboard"))
 
 
@app.route("/resume/<int:id>")
def resume(id):
    conn = get_connection()
    cursor = conn.cursor()
 
    now = datetime.now(timezone.utc)
 
    cursor.execute("""
        UPDATE followups 
        SET status='ACTIVE',
            next_followup_at=%s,
            updated_at=%s
        WHERE id=%s
    """, (now, now, id))
 
    conn.commit()
    conn.close()

    log_activity(id,"Resumed by User")
 
    flash(f"Followup ID {id} resumed successfully.")
    return redirect(url_for("dashboard"))
@app.route("/reset/<int:id>")
def reset(id):
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        UPDATE followups
        SET attempt_count=0,
            status='ACTIVE',
            updated_at=%s
        WHERE id=%s
    """, (datetime.now(timezone.utc), id))
 
    conn.commit()
    conn.close()
 
    flash(f"Followup ID {id} reset successfully.")
    return redirect(url_for("dashboard"))
@app.route("/restart/<int:id>")
def restart(id):

    version=request.args.get("version")
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT conversation_id
        FROM followups
        WHERE id = %s
    """, (id,))
    row = cursor.fetchone()
    conn.close()
 
    if row:
        conversation_id = row[0]
        if version:
            restart_followup(conversation_id,int(version))
        else:
            restart_followup(conversation_id)
            flash(f"Followup ID {id} restarted successfully.")
 
    return redirect(url_for("dashboard"))

@app.route("/toggle_auto_followup/<int:id>", methods=["POST"])
def toggle_auto_followup(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT conversation_id, auto_followup_enabled FROM followups WHERE id = %s", (id,))
    conversation_id, current = cursor.fetchone()
    new_value = 0 if current else 1
    cursor.execute("UPDATE followups SET auto_followup_enabled = ? WHERE id = ?", (new_value, id))
    conn.commit()
    conn.close()
    log_activity(id, f"Auto-followup toggled {'ON' if new_value else 'OFF'} by user")
    return {"auto_followup_enabled": new_value}

@app.route("/approve_reply/<int:id>", methods=["POST"])
def approve_reply(id):
    final_response = request.form.get("final_response", "")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT conversation_id, last_reply_message_id FROM followups WHERE id = %s", (id,))
    conversation_id, message_id = cursor.fetchone()
    conn.close()

    send_followup_reply_manual(message_id, final_response)
    update_ai_draft_status(conversation_id, "approved", new_body=final_response)
    log_activity(id, "AI reply approved and sent")

    flash(f"Reply sent for Followup ID {id}.")
    return redirect(url_for("dashboard"))


@app.route("/rephrase_reply/<int:id>", methods=["POST"])
def rephrase_reply(id):
    instruction = request.form.get("instruction", "")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT conversation_id, last_reply_subject, last_reply_body, ai_draft_body
        FROM followups WHERE id = %s
    """, (id,))
    conversation_id, subject, body, previous_draft = cursor.fetchone()
    conn.close()

    clean_body = clean_email_body(body)
    new_draft = rephrase_draft_body(previous_draft, instruction, subject, clean_body)

    if new_draft:
        update_ai_draft_status(conversation_id, "pending", new_body=new_draft)
        return {"suggested_response": new_draft}
    else:
        return {"suggested_response": previous_draft, "error": "Rephrase failed, showing previous version"}


@app.route("/decline_reply/<int:id>", methods=["POST"])
def decline_reply(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT conversation_id FROM followups WHERE id = %s", (id,))
    (conversation_id,) = cursor.fetchone()
    conn.close()

    update_ai_draft_status(conversation_id, "declined")
    log_activity(id, "AI reply declined by user")

    flash(f"AI reply declined for Followup ID {id}. Conversation remains paused.")
    return redirect(url_for("dashboard"))
@app.route("/get_reply/<int:id>")
def get_reply(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT conversation_id, last_reply_subject, last_reply_body,
               last_client_reply_at,last_client_email
        FROM followups WHERE id = %s
    """, (id,))
    row = cursor.fetchone()
    conn.close()

    conversation_id, subject, body, last_reply_at,client_email = row

    saved = get_ai_draft(conversation_id)

    if saved and saved["analyzed_at"] and last_reply_at and last_reply_at <= saved["analyzed_at"]:
        print("Using saved AI analysis")
        analysis = saved
    else:
        print("Generating new AI analysis")
        clean_body = clean_email_body(body)
        result = analyze_reply(subject, clean_body,client_email)
        if result:
            save_ai_draft(conversation_id, result["draft_body"], result["reasoning"], result["classification"])
            analysis = result
        else:
            analysis = {"draft_body": "", "reasoning": "", "classification": "unclear"}

    return {
        "subject": subject,
        "body": body,
        "suggested_response": analysis["draft_body"],
        "summary": analysis["reasoning"],
        "classification": analysis["classification"],
    }
@app.route("/ignore_reply", methods=["POST"])
def ignore_reply_api():
    #data = request.json()
    conversation_id = request.form.get("conversation_id")
 
    if not conversation_id:
        return {"error": "Missing conversation_id"}, 400
 
    ignore_reply(conversation_id)
 
    return redirect("/")
@app.route("/activity/<int:id>")
def activity(id):
    conn =get_connection()
    cursor = conn.cursor()
 
    cursor.execute("SELECT conversation_id FROM followups WHERE id=%s", (id,))
    row = cursor.fetchone()
    conn.close()
 
    if not row:
        flash("Conversation not found.")
        return redirect(url_for("dashboard"))
 
    conversation_id = row[0]
    logs = get_activity(conversation_id)
 
    return render_template("activity.html", logs=logs) 
@app.route("/activity")
def activity_page():
    from db import convert_to_ist
    logs = get_all_activity()
 
    formatted_logs = []
    for log in logs:
        subject, action, created_at = log
        formatted_logs.append(
            (subject, action, convert_to_ist(created_at))
        )
 
    return render_template("activity.html", logs=formatted_logs)
