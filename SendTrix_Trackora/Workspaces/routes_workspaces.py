from flask_server import app
from process import process,refresh_conversations
from flask import flash,redirect,url_for,render_template,jsonify,request
from Workspaces.workspace_service import get_workspaces,get_workspace_rows,create_workspace,add_conversation_to_workspace,move_conversation_to_workspace
import sqlite3
from db import get_connection
from Tracking.tracking_service import get_unread_replies

@app.route("/workspace/<int:workspace_id>/run")
def run_workspace_process(workspace_id):
 
    try:
        process(workspace_id=workspace_id)
 
        flash("Workspace followups processed successfully.")
 
    except Exception as e:
        print("Workspace process error:", str(e))
        flash("Error processing workspace followups.")
 
    return redirect(
        url_for(
            "workspace_detail",
            workspace_id=workspace_id
        )
    )
@app.route("/workspace/<int:workspace_id>/refresh")
def refresh_workspace(workspace_id):
 
    try:
 
        refresh_conversations(
            workspace_id=workspace_id
        )
 
        flash(
            "Workspace conversations refreshed successfully."
        )
 
    except Exception as e:
 
        print(
            "Workspace refresh error:",
            str(e)
        )
 
        flash(
            "Error refreshing workspace conversations."
        )
 
    return redirect(
        url_for(
            "workspace_detail",
            workspace_id=workspace_id
        )
    )
@app.route("/workspaces")
def workspaces_page():
 
    workspaces = get_workspaces()
 
    return render_template(
        "workspaces.html",
        title="",
        workspaces=workspaces
    )
@app.route("/workspace/<int:workspace_id>")
def workspace_detail(workspace_id):
 
    try:
 
        conn = get_connection()
        cursor = conn.cursor()
 
        cursor.execute("""
            SELECT
                id,
                workspace_name,
                description,
                workspace_type,
                status
            FROM workspaces
            WHERE id = %s
            AND status = 'ACTIVE'
        """, (workspace_id,))
 
        workspace_row = cursor.fetchone()
 
        conn.close()
 
        if not workspace_row:
            return "Workspace not found.", 404
 
        workspace = {
            "id": workspace_row[0],
            "workspace_name": workspace_row[1],
            "description": workspace_row[2],
            "workspace_type": workspace_row[3],
            "status": workspace_row[4]
        }
 
        # Get ONLY conversations belonging to this workspace
        rows = get_workspace_rows(workspace_id)
 
        # Calculate workspace-specific counts
        active_count = sum(
            1 for row in rows
            if row[3] == "ACTIVE"
        )
 
        completed_count = sum(
            1 for row in rows
            if row[3] == "COMPLETED"
        )
 
        client_reply_count = sum(
            1 for row in rows
            if row[3] == "CLIENT_REPLY"
        )
 
        manual_pause_count = sum(
            1 for row in rows
            if row[3] == "MANUAL_PAUSED"
        )
 
        total_count = len(rows)
 
        return render_template(
            "workspace_detail.html",
            workspace_id=workspace_id,
            workspace=workspace,
            rows=rows,
            active_count=active_count,
            completed_count=completed_count,
            client_reply_count=client_reply_count,
            manual_pause_count=manual_pause_count,
            total_count=total_count,
 
            unread_replies=get_unread_replies(),
 
            search=""
        )
 
    except Exception as e:
 
        print(
            "Workspace detail error:",
            str(e)
        )
 
        return "Failed to load workspace.", 500
@app.route("/workspace/<int:workspace_id>/remove/<conversation_id>", methods=["POST"])
def remove_from_workspace(workspace_id, conversation_id):
 
    try:
 
        conn = get_connection()
        cursor = conn.cursor()
 
        cursor.execute("""
            DELETE FROM workspace_conversations
            WHERE workspace_id = %s
            AND conversation_id = %s
        """, (
            workspace_id,
            conversation_id
        ))
 
        conn.commit()
        conn.close()
 
        return jsonify({
            "success": True
        })
 
    except Exception as e:
 
        print(
            "Remove from workspace error:",
            str(e)
        )
 
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
 
@app.route(
    "/workspace/<int:workspace_id>/move/<conversation_id>",
    methods=["POST"]
)
def move_workspace_conversation(workspace_id, conversation_id):
 
    try:
 
        data = request.get_json()
 
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required."
            }), 400
 
        new_workspace_id = data.get("workspace_id")
 
        if not new_workspace_id:
            return jsonify({
                "success": False,
                "error": "Target workspace is required."
            }), 400
 
        new_workspace_id = int(new_workspace_id)
 
        # Prevent moving to the same workspace
        if new_workspace_id == workspace_id:
            return jsonify({
                "success": False,
                "error": "Conversation is already in this workspace."
            }), 400
 
        # Make sure the conversation actually belongs
        # to the current workspace
        conn = get_connection()
        cursor = conn.cursor()
 
        cursor.execute("""
            SELECT id
            FROM workspace_conversations
            WHERE workspace_id = %s
            AND conversation_id = %s
        """, (
            workspace_id,
            conversation_id
        ))
 
        existing = cursor.fetchone()
 
        conn.close()
 
        if not existing:
            return jsonify({
                "success": False,
                "error": "Conversation is not in this workspace."
            }), 404
 
        # Use the existing DB function
        moved = move_conversation_to_workspace(
            conversation_id,
            new_workspace_id
        )
 
        if not moved:
            return jsonify({
                "success": False,
                "error": "Conversation could not be moved."
            }), 404
 
        return jsonify({
            "success": True
        })
 
    except Exception as e:
 
        print(
            "Move workspace conversation error:",
            str(e)
        )
 
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
@app.route("/workspaces/assign", methods=["POST"])
def assign_conversations_to_workspace():
 
    try:
        data = request.get_json()
 
        if not data:
            return jsonify({
                "error": "Request body is required."
            }), 400
 
        workspace_id = data.get("workspace_id")
        conversation_ids = data.get("conversation_ids", [])

        print("WORKSPACE ASSIGN REQUEST")
        print("Workspace:", workspace_id)
        print("Conversations:", conversation_ids)
 
 
        if not workspace_id:
            return jsonify({
                "error": "Workspace ID is required."
            }), 400
 
        if not conversation_ids:
            return jsonify({
                "error": "At least one conversation is required."
            }), 400
 
        assigned = []
        skipped = []
 
        for conversation_id in conversation_ids:
 
            try:
 
                add_conversation_to_workspace(
                    int(workspace_id),
                    conversation_id
                )
 
                assigned.append(conversation_id)
 
            except Exception as e:
 
                print(
                    f"Could not assign {conversation_id}: {e}"
                )
 
                skipped.append({
                    "conversation_id": conversation_id,
                    "reason": str(e)
                })
 
        return jsonify({
            "success": True,
            "assigned": assigned,
            "skipped": skipped
        }), 200
 
    except Exception as e:
 
        print(
            "Workspace assignment error:",
            str(e)
        )
 
        return jsonify({
            "error": str(e)
        }), 500
 
@app.route("/api/workspaces", methods=["GET"])
def api_get_workspaces():
 
    try:
 
        workspaces = get_workspaces()
 
        return jsonify(workspaces)
 
    except Exception as e:
 
        print("Error loading workspaces:", str(e))
 
        return jsonify({
            "error": str(e)
        }), 500
@app.route("/workspaces/create", methods=["POST"])
def create_workspace_route():
    try:
        data = request.get_json()
 
        if not data:
            return jsonify({
                "error": "Request body is required."
            }), 400
 
        workspace_name = str(
            data.get("workspace_name", "")
        ).strip()
 
        description = str(
            data.get("description", "")
        ).strip()
 
        if not workspace_name:
            return jsonify({
                "error": "Workspace name is required."
            }), 400
 
        workspace_id = create_workspace(
            workspace_name,
            description
        )
 
        return jsonify({
            "success": True,
            "workspace": {
                "id": workspace_id,
                "workspace_name": workspace_name,
                "description": description
            }
        }), 201
 
    except sqlite3.IntegrityError:
        return jsonify({
            "error": "A workspace with this name already exists."
        }), 409
 
    except Exception as e:
        print("Create workspace error:", str(e))
 
        return jsonify({
            "error": str(e)
        }), 500
@app.route("/workspaces/<int:workspace_id>/add-conversation", methods=["POST"])
def add_conversation_to_workspace_route(workspace_id):
 
    try:
        data = request.get_json()
 
        if not data:
            return jsonify({
                "error": "Request body is required."
            }), 400
 
        conversation_id = str(
            data.get("conversation_id", "")
        ).strip()
 
        if not conversation_id:
            return jsonify({
                "error": "Conversation ID is required."
            }), 400
 
        add_conversation_to_workspace(
            workspace_id,
            conversation_id
        )
 
        return jsonify({
            "success": True,
            "message": "Conversation added to workspace."
        })
 
    except Exception as e:
 
        print("Add conversation to workspace error:", str(e))
 
        return jsonify({
            "error": str(e)
        }), 400
 