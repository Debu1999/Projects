import requests
import time
import os
import base64
 
from template_engine import render_consolidated_template, render_dynamic, extract_placeholders
from graph_client import get_graph_token,get_draft_by_id
from validators import is_valid_email, clean_email_list
from Tracking.tracking_service import insert_or_resume_followup
from db import get_current_user_id,get_connection

 
BASE_URL = "https://graph.microsoft.com/v1.0"
 
 
# ==========================
# Outlook Category Helper
# ==========================
 
def ensure_outlook_category_exists(category_name, headers):
    import random
 
    print("Checking category:", category_name)
    color=f"preset{random.randint(0,24)}"
 
    response = requests.get(
        f"{BASE_URL}/me/outlook/masterCategories",
        headers=headers
    )
 
    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch categories: {response.status_code} - {response.text}"
        )
 
    existing = [
        c["displayName"]
        for c in response.json().get("value", [])
    ]
 
    if category_name in existing:
        print("Category already exists.")
        return
 
    print("Creating new category...")
 
    create_response = requests.post(
        f"{BASE_URL}/me/outlook/masterCategories",
        headers=headers,
        json={
            "displayName": category_name,
            "color": color
        }
    )
 
    if create_response.status_code != 201:
        raise Exception(
            f"Failed to create category: {create_response.status_code} - {create_response.text}"
        )
 
 
# ==========================
# Helpers
# ==========================
 
def build_recipients(email_list):
    return [
        {"emailAddress": {"address": email}}
        for email in email_list
    ]

def build_attachments(file_paths):
 
    attachments = []
 
    for file_path in file_paths:
 
        if not os.path.exists(file_path):
 
            print(f"Attachment not found: {file_path}")
            continue
 
        with open(file_path, "rb") as f:
 
            content_bytes = base64.b64encode(
                f.read()
            ).decode("utf-8")
 
        attachment = {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": os.path.basename(file_path),
            "contentBytes": content_bytes
        }
 
        attachments.append(attachment)
 
    return attachments

 
def extract_recipient_template(recipient_list):
    """
    Extract all draft recipients into a single comma-separated string.
    Supports multiple To / CC entries.
    """
 
    if not recipient_list:
        return ""
 
    emails = []
 
    for r in recipient_list:
        address = r.get("emailAddress", {}).get("address")
        if address:
            emails.append(address)
 
    return ",".join(emails)
 
 
def map_names_to_emails(raw_string, users_map):
    result = []
 
    items = [x.strip().lower() for x in raw_string.split(",") if x.strip()]
 
    for item in items:
 
        # If already email → keep
        if "@" in item:
            result.append(item)
            continue
 
        # ==========================
        # Strict matching only
        # ==========================
        matches = []
 
        for name_key, email in users_map.items():
            if item == name_key:
                matches.append(email)
 
        # ==========================
        # No match
        # ==========================
        if not matches:
            print("❌ No match for:", item)
            raise Exception(f"No email found for name: {item}")
 
        # ==========================
        # Multiple matches (future safe)
        # ==========================
        if len(matches) > 1:
            raise Exception(
                f"Multiple users found for '{item}': {', '.join(matches)}"
            )
 
        # ==========================
        # Single match
        # ==========================
        print(f"Mapping: {item} → {matches[0]}")
        result.append(matches[0])
 
    return result
 
 

def get_users_map():
    token = get_graph_token()
 
    headers = {
        "Authorization": f"Bearer {token}"
    }
 
    url = f"{BASE_URL}/users?$select=displayName,mail,userPrincipalName"
 
    users_map = {}
 
    while url:
        res = requests.get(url, headers=headers)
 
        if res.status_code != 200:
            raise Exception(res.text)
 
        data = res.json()
 
        for u in data.get("value", []):
            name = (u.get("displayName") or "").strip().lower()
            email = u.get("mail") or u.get("userPrincipalName")
 
            if name and email:
                users_map[name] = email
 
        url = data.get("@odata.nextLink")
 
    return users_map
 
# ==========================
# Core Function
# ==========================
 
def send_bulk_from_draft(draft_id,folder_id,recipients, category_name):

    print("Entered send_bulk_from_draft")
    print("Draft_ID:",draft_id)
    print("Folder_ID:",folder_id)
 
    results = {
        "success": [],
        "failed": []
    }
 
    if not recipients:
        raise Exception("No recipients provided from Excel.")
 
    draft = get_draft_by_id(draft_id,folder_id)
    print("Draft subject:", draft.get("subject"))
    print("TO recipients raw:", draft.get("toRecipients"))
 
    if not draft:
        raise Exception("Draft not found in Outlook.")
 
    # ==========================
    # Templates
    # ==========================
 
    subject_template = draft.get("subject", "")
    body_template = draft.get("body", {}).get("content", "")
 
    to_template = extract_recipient_template(draft.get("toRecipients"))
    cc_template = extract_recipient_template(draft.get("ccRecipients"))
 
    if not to_template:
        raise Exception("Draft must contain at least one TO recipient.")
 
    # ==========================
    # Structural Validation
    # ==========================
 
    all_placeholders = set()
 
    all_placeholders |= extract_placeholders(subject_template)
    all_placeholders |= extract_placeholders(body_template)
    all_placeholders |= extract_placeholders(to_template)
    all_placeholders |= extract_placeholders(cc_template)
 
    #excel_columns = set(recipients[0].keys())
    excel_columns = set(k.lower() for k in recipients[0].keys())
    all_placeholders = set(p.lower() for p in all_placeholders)
 
    missing_columns = all_placeholders - excel_columns
 
    if missing_columns:
        raise Exception(
            f"Excel is missing required columns: {', '.join(missing_columns)}"
        )
 
    # ==========================
    # Auth
    # ==========================
 
    token = get_graph_token()
 
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    users_map=get_users_map()
    print("Users map loaded:",len(users_map))
 
    # Create category once
    if category_name:
        ensure_outlook_category_exists(category_name, headers)
 
    # ==========================
    # Bulk Loop
    # ==========================
 
    for recipient in recipients:
 
        try:
 
            subject = render_dynamic(subject_template, recipient, strict=True)
            body = render_dynamic(body_template, recipient, strict=True)
 
            rendered_to = render_dynamic(to_template, recipient, strict=True)
            rendered_cc = render_dynamic(cc_template, recipient, strict=False)

            print("Rendered TO:",rendered_to)
            print("Rendered CC:",rendered_cc)
 
            to_emails = map_names_to_emails(rendered_to,users_map)
            cc_emails = map_names_to_emails(rendered_cc,users_map)

            print("Mapped TO:",to_emails)
            print("Mapped CC:",cc_emails)
 
            if not to_emails:
                raise Exception("No TO recipient after rendering.")
 
            for email in to_emails:
                if not is_valid_email(email):
                    raise Exception(f"Invalid TO email: {email}")
 
            for email in cc_emails:
                if not is_valid_email(email):
                    raise Exception(f"Invalid CC email: {email}")
 
            payload = {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body
                },
                "toRecipients": build_recipients(to_emails),
                "ccRecipients": build_recipients(cc_emails)
            }
            attachments=recipient.get("attachments",[])
            if attachments:
                payload["attachments"]=build_attachments(attachments)
 
            # ==========================
            # Retry Logic
            # ==========================
 
            for attempt in range(3):
 
                # STEP 1: Create Message
 
                create_response = requests.post(
                    f"{BASE_URL}/me/messages",
                    headers=headers,
                    json=payload
                )
 
                if create_response.status_code == 401:
                    token = get_graph_token()
                    headers["Authorization"] = f"Bearer {token}"
                    continue
 
                if create_response.status_code == 429:
                    retry_after = int(create_response.headers.get("Retry-After", 5))
                    time.sleep(retry_after)
                    continue
 
                if create_response.status_code != 201:
                    raise Exception(create_response.text)
 
                message = create_response.json()
 
                message_id = message["id"]
                conversation_id = message.get("conversationId")
 
                # STEP 2: Apply Category
 
                if category_name:
                    try:
 
                        patch_response = requests.patch(
                            f"{BASE_URL}/me/messages/{message_id}",
                            headers=headers,
                            json={"categories": [category_name]}
                        )
 
                        if patch_response.status_code not in (200, 202):
                            print("Category patch failed:", patch_response.text)
 
                    except Exception as patch_error:
                        print("Category patch error:", str(patch_error))
 
                # STEP 3: Send Message
 
                send_response = requests.post(
                    f"{BASE_URL}/me/messages/{message_id}/send",
                    headers=headers
                )
 
                if send_response.status_code == 401:
                    token = get_graph_token()
                    headers["Authorization"] = f"Bearer {token}"
                    continue
 
                if send_response.status_code == 429:
                    retry_after = int(send_response.headers.get("Retry-After", 5))
                    time.sleep(retry_after)
                    continue
 
                if send_response.status_code != 202:
                    raise Exception(send_response.text)
 
                # STEP 4: Store follow-up tracking
 
                if category_name:
                    try:
 
                        message_data = {
                            "id": message_id,
                            "conversationId": conversation_id,
                            "subject": subject
                        }
 
                        #insert_or_resume_followup(message_data, category_name)
                        all_recipients = list(set(to_emails + cc_emails))
                        insert_or_resume_followup(message_data,category_name,",".join(all_recipients))
 
                    except Exception as follow_error:
                        print("Follow-up error:", str(follow_error))
 
                results["success"].append({
                    "recipient":recipient,
                    "conversation_id":conversation_id
                    })
                break
 
            else:
 
                results["failed"].append({
                    "recipient": recipient,
                    "error": "Max retry attempts exceeded"
                })
 
            time.sleep(0.5)
 
        except Exception as e:
            print("Error for Recipient:",recipient)
            print("Error details:",str(e))
 
            results["failed"].append({
                "recipient": recipient,
                "error": str(e)
            })
 
    return results
def send_consolidated_from_draft(
    draft_id,
    folder_id,
    applications,
    category_name
):
    """
    Send ONE consolidated email for multiple applications.
 
    Individual sending remains handled by send_bulk_from_draft().
    This function creates and sends exactly ONE Outlook message.
    """
 
    print("Entered send_consolidated_from_draft")
    print("Draft_ID:", draft_id)
    print("Folder_ID:", folder_id)
    print("Applications:", len(applications))
 
    if not applications:
        raise Exception("No applications provided.")
 
    # ==========================================
    # Get draft
    # ==========================================
 
    draft = get_draft_by_id(draft_id, folder_id)
 
    if not draft:
        raise Exception("Draft not found in Outlook.")
 
    print("Draft subject:", draft.get("subject"))
 
    # ==========================================
    # Templates
    # ==========================================
 
    subject_template = draft.get("subject", "")
 
    body_template = (
        draft.get("body", {})
        .get("content", "")
    )
 
    to_template = extract_recipient_template(
        draft.get("toRecipients")
    )
 
    cc_template = extract_recipient_template(
        draft.get("ccRecipients")
    )
 
    print("TO template:", to_template)
    print("CC template:", cc_template)
 
    if not to_template:
        raise Exception(
            "Draft must contain at least one TO recipient."
        )
 
    # ==========================================
    # Validate same owner
    # ==========================================
 
    owners = set()
    tech_owners = set()
 
    for application in applications:
 
        owner = str(
            application.get("owner", "")
        ).strip()
 
        if owner:
            owners.add(owner)
 
        tech_owner = str(
            application.get("tech_owner", "")
        ).strip()
 
        if tech_owner:
            tech_owners.add(tech_owner)
 
    if len(owners) != 1:
        raise Exception(
            "Selected applications must belong to "
            "the same service owner."
        )
 
    owner = next(iter(owners))
    tech_owners={
        tech_owner
        for tech_owner in tech_owners
        if tech_owner.lower() != owner.lower()
    }
    print("Owner:", owner)
    print("Technical Owners:", tech_owners)
 
    # ==========================================
    # Build consolidated template data
    # ==========================================
 
    selected_asns = [
        str(application.get("asn", "")).strip()
        for application in applications
        if application.get("asn")
    ]
 
    bulk_data = {
        "owner": owner,
        "tech_owner":", ".join(sorted(tech_owners)),
        "application_count": len(applications),
        "selected_asns": ", ".join(selected_asns)
    }
 
    print("Bulk template data:")
    print(bulk_data)
 
    # ==========================================
    # Render Subject
    # ==========================================
 
    subject = render_consolidated_template(
        subject_template,
        bulk_data,
        applications
    )
 
    # ==========================================
    # Render Body
    # ==========================================
 
    body = render_consolidated_template(
        body_template,
        bulk_data,
        applications
    )
 
    # ==========================================
    # Authentication
    # ==========================================
 
    token = get_graph_token()
 
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
 
    # ==========================================
    # Resolve TO / CC
    # ==========================================
 
    users_map = get_users_map()
 
    print("Users map loaded:", len(users_map))
 
    rendered_to = render_dynamic(
        to_template,
        bulk_data,
        strict=True
    )
 
    rendered_cc = render_dynamic(
        cc_template,
        bulk_data,
        strict=False
    )
 
    print("Rendered TO:", rendered_to)
    print("Rendered CC:", rendered_cc)
 
    to_emails = map_names_to_emails(
        rendered_to,
        users_map
    )
 
    cc_emails = map_names_to_emails(
        rendered_cc,
        users_map
    )
 
    # Remove duplicates
    to_emails = list(dict.fromkeys(to_emails))
    cc_emails = list(dict.fromkeys(cc_emails))
 
    # Do not put the same person in CC if already in TO
    cc_emails = [
        email
        for email in cc_emails
        if email.lower() not in {
            x.lower() for x in to_emails
        }
    ]
 
    print("Mapped TO:", to_emails)
    print("Mapped CC:", cc_emails)
 
    if not to_emails:
        raise Exception(
            "No TO recipient after rendering."
        )
 
    # ==========================================
    # Validate email addresses
    # ==========================================
 
    for email in to_emails:
 
        if not is_valid_email(email):
            raise Exception(
                f"Invalid TO email: {email}"
            )
 
    for email in cc_emails:
 
        if not is_valid_email(email):
            raise Exception(
                f"Invalid CC email: {email}"
            )
 
    # ==========================================
    # Category
    # ==========================================
 
    if category_name:
        ensure_outlook_category_exists(
            category_name,
            headers
        )
 
    # ==========================================
    # Build ONE Outlook message
    # ==========================================
 
    payload = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": body
        },
        "toRecipients": build_recipients(
            to_emails
        ),
        "ccRecipients": build_recipients(
            cc_emails
        )
    }
 
    print("\n================================")
    print("CONSOLIDATED EMAIL")
    print("================================")
    print("Subject:", subject)
    print("TO:", to_emails)
    print("CC:", cc_emails)
 
    # ==========================================
    # Retry Logic
    # ==========================================
 
    for attempt in range(3):
 
        try:
 
            # ----------------------------------
            # Create message
            # ----------------------------------
 
            create_response = requests.post(
                f"{BASE_URL}/me/messages",
                headers=headers,
                json=payload
            )
 
            if create_response.status_code == 401:
 
                token = get_graph_token()
 
                headers["Authorization"] = (
                    f"Bearer {token}"
                )
 
                continue
 
            if create_response.status_code == 429:
 
                retry_after = int(
                    create_response.headers.get(
                        "Retry-After",
                        5
                    )
                )
 
                time.sleep(retry_after)
 
                continue
 
            if create_response.status_code != 201:
 
                raise Exception(
                    create_response.text
                )
 
            message = create_response.json()
 
            message_id = message["id"]
 
            conversation_id = message.get(
                "conversationId"
            )
 
            print(
                "Message created:",
                message_id
            )
 
            print(
                "Conversation ID:",
                conversation_id
            )
 
            # ----------------------------------
            # Apply category
            # ----------------------------------
 
            if category_name:
 
                try:
 
                    patch_response = requests.patch(
                        f"{BASE_URL}/me/messages/{message_id}",
                        headers=headers,
                        json={
                            "categories": [
                                category_name
                            ]
                        }
                    )
 
                    if patch_response.status_code not in (
                        200,
                        202
                    ):
 
                        print(
                            "Category patch failed:",
                            patch_response.text
                        )
 
                except Exception as patch_error:
 
                    print(
                        "Category patch error:",
                        str(patch_error)
                    )
 
            # ----------------------------------
            # Send message
            # ----------------------------------
 
            send_response = requests.post(
                f"{BASE_URL}/me/messages/{message_id}/send",
                headers=headers
            )
 
            if send_response.status_code == 401:
 
                token = get_graph_token()
 
                headers["Authorization"] = (
                    f"Bearer {token}"
                )
 
                continue
 
            if send_response.status_code == 429:
 
                retry_after = int(
                    send_response.headers.get(
                        "Retry-After",
                        5
                    )
                )
 
                time.sleep(retry_after)
 
                continue
 
            if send_response.status_code != 202:
 
                raise Exception(
                    send_response.text
                )
 
            print(
                "Consolidated email sent successfully."
            )
 
            # ----------------------------------
            # Follow-up tracking
            # ----------------------------------
 
            if category_name:
 
                try:
 
                    message_data = {
                        "id": message_id,
                        "conversationId": conversation_id,
                        "subject": subject
                    }
 
                    all_recipients = list(
                        set(
                            to_emails +
                            cc_emails
                        )
                    )
 
                    insert_or_resume_followup(
                        message_data,
                        category_name,
                        ",".join(all_recipients)
                    )
 
                except Exception as follow_error:
 
                    print(
                        "Follow-up error:",
                        str(follow_error)
                    )
 
            # ==================================
            # SUCCESS
            # ==================================
 
            return {
                "success": [{
                    "conversation_id":
                        conversation_id,
                    "message_id":
                        message_id,
                    "to":
                        to_emails,
                    "cc":
                        cc_emails
                }],
                "failed": []
            }
 
        except Exception as e:
 
            print(
                f"Consolidated send attempt "
                f"{attempt + 1} failed:",
                str(e)
            )
 
            if attempt == 2:
 
                return {
                    "success": [],
                    "failed": [{
                        "error": str(e)
                    }]
                }
 
            time.sleep(1)
 
    return {
        "success": [],
        "failed": [{
            "error":
                "Maximum retry attempts exceeded."
        }]
    }
def get_bulk_runs():
    user_id = get_current_user_id()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT
    conversation_id,subject,category_name,status,started_at FROM followups WHERE user_id = %s ORDER BY started_at DESC""", (user_id,))
    rows = cursor.fetchall()
    result = []

    for r in rows:
        result.append({
            "id": r[0],"subject": r[1],"category": r[2],"status": r[3],"recipient_count": 1,"created_at": r[4]})
    conn.close()
    return result
 