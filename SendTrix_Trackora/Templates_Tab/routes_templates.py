from flask_server import app
from graph_client import (
    get_outlook_drafts,
    get_draft_child_folders,
    get_draft_content,
    move_draft,
    create_draft_child_folder,
    get_followup_drafts
    )
from Categories.category_service import get_template_folders,save_template_folders_settings
from flask import request,jsonify,render_template

@app.route("/templates")
def templates():
 
    drafts_by_folder = get_outlook_drafts()
 
    folder_data = get_draft_child_folders()
    folders = folder_data.get("value", [])
 
    folders.insert(0,{
        "id":"Drafts",
        "displayName":"Drafts"
    })
 
    # NEW: fetch saved template folder settings
    folder_settings = get_template_folders()
 
    primary_folder_id = None
    secondary_folder_id = None
 
    if folder_settings:
        primary_folder_id = folder_settings[0]
        secondary_folder_id = folder_settings[1]
 
    return render_template(
        "templates_page.html",
        drafts_by_folder=drafts_by_folder,
        folders=folders,
        primary_folder_id=primary_folder_id,
        secondary_folder_id=secondary_folder_id
    )
@app.route("/template_preview/<message_id>")
def template_preview(message_id):
 
    draft = get_draft_content(message_id)
 
    # Extract recipients
    to_list = [
        r.get("emailAddress", {}).get("address")
        for r in draft.get("toRecipients", [])
    ]
 
    cc_list = [
        r.get("emailAddress", {}).get("address")
        for r in draft.get("ccRecipients", [])
    ]
 
    return jsonify({
        "subject": draft.get("subject"),
        "body": draft.get("body", {}).get("content", ""),
        "to": to_list,
        "cc": cc_list
    })

@app.route("/move_template", methods=["POST"])
def move_template():
 
    message_id = request.json.get("message_id")
    folder_id = request.json.get("folder_id")
 
    move_draft(message_id, folder_id)
 
    return {"status": "success"}

@app.route("/create_template_folder", methods=["POST"])
def create_template_folder():
 
    folder_name = request.json.get("folder_name")
 
    create_draft_child_folder(folder_name)
 
    return {"status":"success"}
@app.route("/fetch_drafts")
def fetch_drafts():
    print("Fetch Drafts Called")
 
    folders = get_template_folders()
    print("Folders from DB:",folders)
 
    if not folders:
        print("No folders found in DB")
        return {"value": []}

    primary_folder_id,secondary_folder_id=folders
    print("Folders from DB:",folders)
    print("Primary_Folder:",primary_folder_id)
    print("Using Folder:",secondary_folder_id)
 
    drafts_response = get_followup_drafts(secondary_folder_id)
    print("Graph Response:",drafts_response)
 
    return drafts_response

@app.route("/save_template_folders", methods=["POST"])
def save_template_folders():
    data = request.json
    initiate_id = data.get("primary_folder_id")
    followup_id = data.get("secondary_folder_id")
    save_template_folders_settings(initiate_id, followup_id)
    return {"status":"success"}