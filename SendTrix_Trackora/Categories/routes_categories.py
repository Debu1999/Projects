from flask_server import app
from flask import render_template, redirect, url_for, flash, request,jsonify
from Categories.category_service import get_all_categories,get_category_details,clone_category_version,save_settings
from db import get_connection
from graph_client import get_graph_token
from Bulk_Email.draft_bulk_sender import ensure_outlook_category_exists

@app.route("/categories")
def categories():
    return render_template("categories.html")

@app.route("/api/categories")
def categories_api():
    return jsonify(get_all_categories())

@app.route("/category/<name>/<int:version>")
def category_details(name,version):
 
    data = get_category_details(name,version)
 
    if not data:
        return jsonify({"error": "Category not found"}), 404
 
    return jsonify(data)

@app.route("/clone_category", methods=["POST"])
def clone_category():
 
    data = request.get_json()
 
    if not data:
        return jsonify({"error": "No JSON received"}), 400
 
    category_name = data.get("category_name")
    version = data.get("version")
 
    if not category_name or not version:
        return jsonify({"error": "Invalid request"}), 400
 
    try:
 
        new_version = clone_category_version(category_name, int(version))
 
        return jsonify({
            "success": True,
            "new_version": new_version
        })
 
    except Exception as e:
        print("CLONE ERROR:", e)
        return jsonify({"error": str(e)}), 500
@app.route("/update_category", methods=["POST"])
def update_category():
 
    data = request.get_json()
 
    category_name = data.get("category_name")
    max_attempts = int(data.get("max_attempts"))
    interval_minutes = int(data.get("interval_minutes"))
    mode = data.get("mode")
    followup_text = data.get("followup_text", "")
    restart_sequences = data.get("restart_sequences", False)
 
    templates = data.get("templates", [])
 
    selected_draft_ids = ""
 
    if templates:
        selected_draft_ids = ",".join(
            [t.get("id") for t in templates if t.get("id")]
        )
 
    # 🔹 create new version using db.py
    new_version = save_settings(
        category_name,
        followup_text,
        max_attempts,
        interval_minutes,
        mode,
        selected_draft_ids
    )
 
    # 🔹 restart active sequences if requested
    if restart_sequences:
 
        conn = get_connection()
        cursor = conn.cursor()
 
        cursor.execute("""
        UPDATE followups
        SET attempt_count = 0,
            next_followup_at = CURRENT_TIMESTAMP,
            category_version = %s
        WHERE category_name = %s
        AND status = 'ACTIVE'
        """, (
            new_version,
            category_name
        ))
 
        conn.commit()
        conn.close()
 
    return jsonify({
        "status": "ok",
        "new_version": new_version
    })
@app.route("/save_category", methods=["POST"])
def save_category():
    category_name = request.form.get("category_name", "").strip()
    followup_mode = request.form.get("followup_mode", "manual")
    followup_text = request.form.get("followup_text", "").strip()
    max_attempts = request.form.get("max_attempts")
    interval_minutes = request.form.get("interval_minutes")
    selected_draft_ids=request.form.get("selected_draft_ids","").strip()
 
    # Basic required validation
    if not category_name or not max_attempts or not interval_minutes:
        flash("Category name, attempts and interval are required.")
        return redirect(url_for("dashboard"))
 
    # Manual mode requires followup text
    if followup_mode == "manual" and not followup_text:
        flash("Followup text is required in Manual mode.")
        return redirect(url_for("dashboard"))
 
    try:
        save_settings(
            category_name,
            followup_text if followup_mode == "manual" else "",  # store empty if template mode
            int(max_attempts),
            int(interval_minutes),
            followup_mode,
            selected_draft_ids
        )
        token=get_graph_token()
        headers={
            "Authorization":f"Bearer {token}",
            "Content-Type":"application/json"
        }

        ensure_outlook_category_exists(category_name,headers)
 
        flash(f"Category '{category_name}' saved successfully and created in Outlook.")
 
    except Exception as e:
        flash(f"Error saving category: {e}")
 
    return redirect(url_for("dashboard"))
@app.route("/category_versions/<category_name>")
def category_versions(category_name):
 
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT version
        FROM settings
        WHERE category_name = %s
        ORDER BY version
    """, (category_name,))
 
    rows = cursor.fetchall()
    conn.close()
 
    versions = [r[0] for r in rows]
 
    return {"versions": versions}