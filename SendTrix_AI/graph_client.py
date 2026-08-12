import requests
from auth import get_access_token
from datetime import datetime, timedelta, timezone


 
BASE_URL = "https://graph.microsoft.com/v1.0"

 
 
# -------------------------------------------------
# Get sent messages (basic)
# -------------------------------------------------
def get_sent_messages():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
 
    url = f"{BASE_URL}/me/mailFolders/SentItems/messages?$top=5"
    response = requests.get(url, headers=headers)
 
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
 
    return response.json()
 
def get_full_message(message_id):
    from auth import get_access_token
    import requests
 
    token = get_access_token()
 
    headers = {
        "Authorization": f"Bearer {token}"
    }
 
    # ✅ IMPORTANT: use $select to get recipients
    url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}?$select=toRecipients,ccRecipients,subject"
 
    response = requests.get(url, headers=headers)
 
    if response.status_code != 200:
        print("❌ Error fetching full message:", response.text)
        return {}
 
    return response.json()
 
# -------------------------------------------------
# Get sent messages with specific category
# -------------------------------------------------
def get_sent_with_category(category_name):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
 
    safe_category = category_name.replace("'", "''")
 
    url = (
        f"{BASE_URL}/me/mailFolders/SentItems/messages"
        f"?$filter=categories/any(c:c eq '{safe_category}')"
        f"&$select=id,conversationId,categories,subject,toRecipients,ccRecipients"
    )
 
    messages = []
 
    while url:
        response = requests.get(url, headers=headers)
 
        if response.status_code != 200:
            raise Exception(response.status_code, response.text)
 
        data = response.json()
        messages.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
 
    return messages

# -------------------------------------------------
# Get full draft content (for template preview)
# -------------------------------------------------
def get_draft_content(message_id):
 
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
 
    url = f"{BASE_URL}/me/messages/{message_id}"
 
    response = requests.get(url, headers=headers)
 
    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch draft: {response.status_code} - {response.text}"
        )
 
    return response.json()
# -------------------------------------------------
# Move draft to another folder
# -------------------------------------------------
# -------------------------------------------------
# Get draft child folders
# -------------------------------------------------
def get_draft_child_folders():
 
    token = get_access_token()
 
    headers = {
        "Authorization": f"Bearer {token}"
    }
 
    url = f"{BASE_URL}/me/mailFolders/Drafts/childFolders"
 
    response = requests.get(url, headers=headers)
 
    if response.status_code != 200:
        raise Exception("Failed to fetch folders", response.text)
 
    return response.json()

def move_draft(message_id, destination_folder_id):
 
    token = get_access_token()
 
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
 
    url = f"{BASE_URL}/me/messages/{message_id}/move"
 
    payload = {
        "destinationId": destination_folder_id
    }
 
    response = requests.post(url, headers=headers, json=payload)
 
    if response.status_code not in [200, 201]:
        raise Exception("Move draft failed", response.text)
 
    return response.json()

# -------------------------------------------------
# Create child folder inside Drafts
# -------------------------------------------------
def create_draft_child_folder(folder_name):
 
    token = get_access_token()
 
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
 
    url = f"{BASE_URL}/me/mailFolders/Drafts/childFolders"
 
    payload = {
        "displayName": folder_name
    }
 
    response = requests.post(url, headers=headers, json=payload)
 
    if response.status_code not in [200,201]:
        raise Exception("Folder creation failed", response.text)
 
    return response.json()
 
def get_followup_drafts(folder_id):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
 
    url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages?$select=id,subject&$top=50"
    print("Calling Graph with folder_id:",folder_id)
    print("URL:",url)
 
    response = requests.get(url, headers=headers)
 
    if response.status_code != 200:
        return {"value": []}
 
    return response.json()
 
def get_current_user_email():
 
    token = get_access_token()
 
    headers = {
        "Authorization": f"Bearer {token}"
    }
 
    response = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers=headers
    )
 
    data = response.json()
 
    return data["mail"]
# -------------------------------------------------
# 🟢 MANUAL MODE
# -------------------------------------------------
def send_followup_reply_manual(message_id, followup_text):
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
 
    # Step 1: Create reply-all draft
    create_url = f"{BASE_URL}/me/messages/{message_id}/createReplyAll"
    response = requests.post(create_url, headers=headers)
 
    if response.status_code != 201:
        raise Exception("CreateReply failed", response.text)
 
    draft = response.json()
    draft_id = draft["id"]
 
    # Step 2: Update body (HTML preferred)
    update_url = f"{BASE_URL}/me/messages/{draft_id}"
    update_payload = {
        "body": {
            "contentType": "HTML",
            "content": followup_text
        }
    }
 
    response = requests.patch(update_url, headers=headers, json=update_payload)
 
    if response.status_code != 200:
        raise Exception("Updating draft failed", response.text)
 
    # Step 3: Send
    send_url = f"{BASE_URL}/me/messages/{draft_id}/send"
    response = requests.post(send_url, headers=headers)
 
    if response.status_code != 202:
        raise Exception("Send failed", response.text)
 
    print("[+] Follow-up sent (Manual Mode)")
 
 
# -------------------------------------------------
# 🔵 TEMPLATE MODE (Draft-Based)
# -------------------------------------------------
def send_followup_reply_template(message_id, template_draft_id):
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
 
    # Step 1: Create reply-all draft (recipients auto-set)
    create_url = f"{BASE_URL}/me/messages/{message_id}/createReplyAll"
    response = requests.post(create_url, headers=headers)
 
    if response.status_code != 201:
        raise Exception("CreateReply failed", response.text)
 
    reply_draft = response.json()
    reply_draft_id = reply_draft["id"]
 
    # Step 2: Fetch template draft (only body needed)
    template_url = f"{BASE_URL}/me/messages/{template_draft_id}"
    response = requests.get(template_url, headers=headers)
 
    if response.status_code != 200:
        raise Exception("Fetching template draft failed", response.text)
 
    template = response.json()
    template_body = template.get("body", {}).get("content", "")
 
    if not template_body:
        raise Exception("Template draft has empty body.")
 
    # Step 3: Replace reply draft body ONLY
    update_url = f"{BASE_URL}/me/messages/{reply_draft_id}"
    update_payload = {
        "body": {
            "contentType": "HTML",
            "content": template_body
        }
    }
 
    response = requests.patch(update_url, headers=headers, json=update_payload)
 
    if response.status_code != 200:
        raise Exception("Updating reply draft failed", response.text)
 
    # Step 4: Send reply draft
    send_url = f"{BASE_URL}/me/messages/{reply_draft_id}/send"
    response = requests.post(send_url, headers=headers)
 
    if response.status_code != 202:
        raise Exception("Send failed", response.text)
 
    print("[+] Follow-up sent (Template Mode)")
 
 
# -------------------------------------------------
# Get latest message in conversation
# -------------------------------------------------
def get_latest_message_in_conversation(conversation_id):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
 
    url = (
        f"{BASE_URL}/me/messages"
        f"?$filter=conversationId eq '{conversation_id}'"
        f"&$select=id,subject,body,from,receivedDateTime"
        f"&$top=50"
    )
 
    response = requests.get(url, headers=headers)
 
    if response.status_code != 200:
        raise Exception("Fetching conversation messages failed", response.text)
 
    messages = response.json().get("value", [])
 
    if not messages:
        return None
 
    messages.sort(
        key=lambda x: x.get("receivedDateTime", ""),
        reverse=True
    )
 
    return messages[0]

def get_messages_in_conversation(conversation_id):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
 
    all_messages = []
 
    # 1️⃣ Inbox (with pagination)
    url = (
        f"{BASE_URL}/me/messages"
        f"?$filter=conversationId eq '{conversation_id}'"
        f"&$select=id,subject,from,toRecipients,ccRecipients,sentDateTime,receivedDateTime"
    )
 
    while url:
        res = requests.get(url, headers=headers)
 
        if res.status_code != 200:
            print("Error fetching inbox messages:", res.text)
            break
 
        data = res.json()
        all_messages.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
 
    # 2️⃣ Sent Items (with pagination)
    url = (
        f"{BASE_URL}/me/mailFolders/SentItems/messages"
        f"?$filter=conversationId eq '{conversation_id}'"
        f"&$select=id,subject,from,toRecipients,ccRecipients,sentDateTime,receivedDateTime"
    )
 
    while url:
        res = requests.get(url, headers=headers)
 
        if res.status_code != 200:
            print("Error fetching sent messages:", res.text)
            break
 
        data = res.json()
        all_messages.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
 
    return all_messages
 
 

# -------------------------------------------------
# Get all drafts for Templates tab
# -------------------------------------------------
def get_outlook_drafts():
 
    token = get_access_token()
 
    headers = {
        "Authorization": f"Bearer {token}"
    }
 
    folder_map = {}
 
    # -------------------------------------------------
    # 1️⃣ Default Drafts
    # -------------------------------------------------
 
    url = f"{BASE_URL}/me/mailFolders/Drafts/messages?$select=id,subject,bodyPreview,toRecipients,ccRecipients,parentFolderId&$top=50"
 
    response = requests.get(url, headers=headers)
 
    if response.status_code == 200:
        folder_map["Drafts"] = response.json().get("value", [])
    else:
        folder_map["Drafts"] = []
 
 
    # -------------------------------------------------
    # 2️⃣ Fetch Draft child folders
    # -------------------------------------------------
 
    folder_url = f"{BASE_URL}/me/mailFolders/Drafts/childFolders"
 
    response = requests.get(folder_url, headers=headers)
 
    if response.status_code != 200:
        return folder_map
 
    folders = response.json().get("value", [])
 
 
    # -------------------------------------------------
    # 3️⃣ Fetch drafts inside each folder
    # -------------------------------------------------
 
    for folder in folders:
 
        folder_name = folder["displayName"]
        folder_id = folder["id"]
 
        url = f"{BASE_URL}/me/mailFolders/{folder_id}/messages?$select=id,subject,bodyPreview,toRecipients,ccRecipients,parentFolderId&$top=50"
 
        response = requests.get(url, headers=headers)
 
        if response.status_code == 200:
            folder_map[folder_name] = response.json().get("value", [])
        else:
            folder_map[folder_name] = []
 
 
    return folder_map
def get_user_timezone(email):
 
    token = get_access_token()
 
    headers = {
        "Authorization": f"Bearer {token}"
    }
 
    response = requests.get(
        f"https://graph.microsoft.com/v1.0/users/{email}/mailboxSettings",
        headers=headers
    )
 
    print("MAILBOX SETTINGS:", response.status_code)
 
    if response.status_code == 200:
        data = response.json()
        return data.get("timeZone", "UTC")
 
    return "UTC"
 

def get_user_availability(email):
 
    token = get_access_token()
 
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
 
    now = datetime.now()
 
    end = now + timedelta(days=5)
    #time_zone=get_user_timezone(email)
    #print("USER TIMEZONE:",time_zone)
    payload = {
        "schedules": [email],
        "startTime": {
            "dateTime": now.isoformat(),
            "timeZone": "India Standard Time"
        },
        "endTime": {
            "dateTime": end.isoformat(),
            "timeZone": "India Standard Time"
        },
        "availabilityViewInterval": 30
    }
 
    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/calendar/getSchedule",
        headers=headers,
        json=payload
    )
 
    print("SCHEDULE_STATUS:", response.status_code)
    
 
    return response.json()
 
 