from db import (
    get_due_followups,
    update_after_send,
    pause_tracking,
    get_settings,
    init_db,
    get_template_for_attempt,
    save_client_reply,
    get_reply_flags,
    resume_tracking,
    get_status,
    get_last_client_reply_time,
    get_client_reply_followups,
    get_active_followups,
    get_workspace_followup_conversation_ids,
    get_workspace_conversation_ids
)
from agent_service import clean_email_body, analyze_reply
from db import save_ai_draft
 
from graph_client import (
    send_followup_reply_manual,
    send_followup_reply_template,
    get_latest_message_in_conversation,
    get_messages_in_conversation
)
 
from auth import get_access_token
import requests
from datetime import datetime, timezone
from agent_service import get_agent_followup_decision
 
 
# Ensure DB initialized
init_db()
 
_my_email_cache = None
 
 
def get_my_email():
    global _my_email_cache
    if _my_email_cache:
        return _my_email_cache
 
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
 
    response = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers=headers,
    )
 
    if response.status_code != 200:
        raise Exception("Failed to fetch user profile")
 
    profile = response.json()
    email = profile.get("mail") or profile.get("userPrincipalName")
 
    if not email:
        raise Exception("Unable to determine logged-in user email")
 
    _my_email_cache = email.lower().strip()
    return _my_email_cache
 
 
def is_from_me(sender_address: str, my_email: str) -> bool:
    if not sender_address:
        return False
    return sender_address.lower().strip() == my_email.lower().strip()
 
 
def parse_graph_datetime(dt_string: str):
    if not dt_string:
        return None
 
    try:
        return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
    except Exception:
        return None

def is_auto_reply(subject: str):
    if not subject:
        return False
 
    subject = subject.lower()
 
    keywords = [
        "out of office",
        "automatic reply",
        "auto reply",
        "autoreply",
        "out of the office"
    ]
 
    return any(k in subject for k in keywords)

def did_user_reply_after_client(conversation_id, last_client_reply_time):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
 
    url = (
        f"https://graph.microsoft.com/v1.0/me/messages"
        f"?$filter=conversationId eq '{conversation_id}'"
        f"&$top=15"
    )
 
    response = requests.get(url, headers=headers)
 
    if response.status_code != 200:
        print("Error fetching messages:", response.text)
        return False
 
    #messages = response.json().get("value", [])
    messages=get_messages_in_conversation(conversation_id)
 
    my_email = get_my_email()
 
    for msg in messages:
        sender = (
            msg.get("from", {})
            .get("emailAddress", {})
            .get("address", "")
        ).lower().strip()
 
        msg_time = parse_graph_datetime(msg.get("sentDateTime") or msg.get("receivedDateTime"))

        print("MESSAGE:",sender,"| Time:",msg_time,"| Last Client:",last_client_reply_time)
        if sender == my_email and msg_time and last_client_reply_time:
            if msg_time > last_client_reply_time:
                print("RETURNING TRUE BECAUSE:", msg_time, ">", last_client_reply_time)
                return True
 
    return False
 

def refresh_conversations(workspace_id=None):
 
    print("Refreshing conversations")
 
    my_email = get_my_email()
 
    due_rows = get_due_followups()
    client_reply_rows = get_client_reply_followups()
    active_rows=get_active_followups()
    all_rows = {}
    
    for row in due_rows + client_reply_rows + active_rows:
        conversation_id = row[1]   # row[1] = conversation_id
        all_rows[conversation_id] = row
    
    rows = list(all_rows.values())
    # -----------------------------------------
    # WORKSPACE FILTER
    # -----------------------------------------
    if workspace_id is not None:
 
        workspace_conversation_ids = set(
            get_workspace_conversation_ids(workspace_id)
        )
 
        rows = [
            row for row in rows
            if row[1] in workspace_conversation_ids
        ]
 
        print(
            f"Workspace {workspace_id}: "
            f"{len(rows)} conversations selected for refresh"
        )
 
    print("Total conversations:", len(rows))
 
    #rows = rows + paused_rows
 
    #print("Total conversations:", len(rows))
 
    for (
        message_id,
        conversation_id,
        category_name,
        version,
        attempt_count,
        last_followup_sent_at,
        original_recipients
    ) in rows:
 
        latest_message = get_latest_message_in_conversation(
            conversation_id
        )
 
        if not latest_message:
            continue
 
        latest_sender = (
            latest_message.get("from", {})
            .get("emailAddress", {})
            .get("address", "")
        )
 
        print(
            "Conversation:",
            conversation_id,
            "Latest sender:",
            latest_sender
        )
        messages = get_messages_in_conversation(conversation_id)
        #print("MESSAGE_COUNT:", len(messages))
        for msg in messages:
            sender = (
                msg.get("from", {})
                .get("emailAddress", {})
                .get("address", "")
            )
            to_list = [
                r.get("emailAddress", {}).get("address", "")
                for r in msg.get("toRecipients", [])
            ]
            cc_list = [
                r.get("emailAddress", {}).get("address", "")
                for r in msg.get("ccRecipients", [])
            ]
            #print("-----")
            #print("FROM:", sender)
            #print("TO:", to_list)
            #print("CC:", cc_list)
 
        sender_clean = (latest_sender or "").lower().strip()
        #print("IS_FROM_ME",is_from_me(sender_clean,my_email))
        current_status = get_status(conversation_id)
        if (current_status == "CLIENT_REPLY"and is_from_me(sender_clean, my_email)):
            print("User replied after client")
            resume_tracking(conversation_id)
            print("Conversation resumed")
            continue
        if not is_from_me(sender_clean, my_email):
            print("Potential client reply detected")
            subject = latest_message.get("subject", "")
            body = latest_message.get("body", {}).get("content", "")
            latest_message_id = latest_message.get("id")
            
            latest_received_time = parse_graph_datetime(
                latest_message.get("receivedDateTime")
            )
            print("LATEST SUBJECT:",subject)
            print("LATEST BODY:",body[:1000])
            save_client_reply(
                conversation_id,
                sender_clean,
                latest_received_time,
                subject,
                body,
                latest_message_id
            )
            clean_body = clean_email_body(body)
            result = analyze_reply(subject, clean_body,sender_clean)
            if result:
                save_ai_draft(conversation_id, result["draft_body"], result["reasoning"],result["classification"])
            pause_tracking(conversation_id)
            print("Conversation paused")
 
# =========================================================
# 🚀 MAIN PROCESS (MULTI CATEGORY SAFE)
# =========================================================
 
def process(workspace_id=None):
    print("Starting process")
    my_email=get_my_email()
    rows = get_due_followups()
    client_reply_rows=get_client_reply_followups()

    rows=rows+client_reply_rows
    # -----------------------------------------
    # WORKSPACE FILTER
    # -----------------------------------------
    if workspace_id is not None:
        print(f"Filtering for workspace {workspace_id}")
 
        workspace_conversation_ids = set(
            get_workspace_followup_conversation_ids(workspace_id)
        )
 
        rows = [
            row for row in rows
            if row[1] in workspace_conversation_ids
        ]
 
        print(
            f"Workspace {workspace_id}: "
            f"{len(rows)} conversations eligible for processing"
        )
    print("\n================ PROCESS START ================")
    print("Due rows:", len(rows))
    for row in rows:
        print(
        "Conversation:",
        row[1],
        "Status:",
        get_status(row[1]),
        "Attempt:",
        row[4]
        )
    print("==============================================")
 
    if not rows:
        print("No followups due.")
        return
 
    #my_email = get_my_email()
 
    print(f"Found {len(rows)} due followups")
 
    for message_id, conversation_id,category_name,version, attempt_count,last_followup_sent_at,original_recipients in rows:
 
 
        try:
 
            # Get category-specific settings
            settings = get_settings(category_name,version)
            if not settings:
                print(f"No settings found for category {category_name}")
                continue
            if last_followup_sent_at:
                last_followup_sent_at=parse_graph_datetime(last_followup_sent_at)
            
 
            followup_text, max_attempts, interval_minutes,followup_mode = settings
            #DEBUG
            print("Category:",category_name)
            print("Followup mode:",followup_mode)
            print("Max_attempts:",max_attempts)
            print("Interval:",interval_minutes)
 
            latest_message = get_latest_message_in_conversation(conversation_id)
            print("Latest message full:",latest_message)
            
 
            if not latest_message:
                print("No messages found in conversation. Skipping.")
                continue
            subject=latest_message.get("subject","")
            body=latest_message.get("body",{}).get("content","")
            latest_message_id=latest_message.get("id")    
 
            latest_sender = (
                latest_message.get("from", {})
                .get("emailAddress", {})
                .get("address", "")
            )
            latest_sender_name = (
                latest_message.get("from", {})
                .get("emailAddress", {})
                .get("name", "")
            )
            print("Sender object:",latest_message.get("from",{}))
            print("Sender name:",latest_sender_name)
 
            latest_received_time = parse_graph_datetime(
                latest_message.get("receivedDateTime")
            )
            print("Latest sender:",latest_sender)
            print("My email:",my_email)
            print("sender_clean:",(latest_sender or "").lower().strip())
 
            # Get DB updated time for race condition check
            # (Fetch updated_at dynamically)
            # We re-query because get_due_followups doesn't return updated_at now
            # Optional improvement later.
            sender_clean = (latest_sender or "").lower().strip()
            current_status=get_status(conversation_id)
            if current_status == "CLIENT_REPLY":
                print("Conversation is paused")
                last_client_reply_time = get_last_client_reply_time(conversation_id)
                if last_client_reply_time:
                    last_client_reply_time = parse_graph_datetime(last_client_reply_time)
                    result=did_user_reply_after_client(conversation_id,last_client_reply_time)
                    print("Did_user_reply_after_client:",result)
                    if result:
                        print("User replied after client → Auto resume")
                        resume_tracking(conversation_id)
                        continue
                    print("Still paused.Skipping")
                    continue
            

            recipient_list = []
            if original_recipients:
                recipient_list = [x.strip().lower() for x in original_recipients.split(",") if x.strip()] if original_recipients else []
                print("Recipient list:", recipient_list)  # debug
            if (not is_from_me(sender_clean, my_email) and latest_received_time):
                is_reply=False
                # CASE 1
                if last_followup_sent_at and latest_received_time>last_followup_sent_at:
                    is_reply=True
                # CASE 2
                if not last_followup_sent_at:
                    is_reply=True
                if is_reply:
                    if is_auto_reply(subject):
                        print("Auto-reply detected. Ignoring")
                        continue
                    
                    match_found = any(sender_clean == r or sender_clean.endswith("@" + r.split("@")[-1])
                    for r in recipient_list)
                    if not match_found:
                        print("Reply from Unknown Sender,Ignoring")
                        print("Sender:", sender_clean)
                        print("Recipients:", recipient_list)
                        continue
                    #print("Client replied. Pausing tracking.")
                    #save_client_reply(conversation_id,sender_clean,latest_received_time)
                    #save_client_reply(conversation_id,sender_clean,latest_received_time,subject,body)
                    #pause_tracking(conversation_id)
                    #continue
                    print("LATEST SUBJECT:",subject)
                    print("LATEST BODY:",body[:1000])
                    save_client_reply(conversation_id,f"{latest_sender_name}({sender_clean})",latest_received_time,subject,body,latest_message_id)
                    clean_body = clean_email_body(body)
                    result = analyze_reply(subject, clean_body,sender_clean)
                    if result:
                        save_ai_draft(conversation_id, result["draft_body"], result["reasoning"],result["classification"])
                    is_ignored=get_reply_flags(conversation_id)
                    if is_ignored==0:
                        print("Client Replied. Pausing tracking")
                        pause_tracking(conversation_id)
                    else:
                        print("Reply ignored previously. Not pausing again")
                    continue

 
            if attempt_count >= max_attempts:
                print("Max attempts reached. Skipping.")
                continue

            print("Attempt Count from DB:",attempt_count)
            attempt_number = attempt_count+1
            print("Attempt Count:",attempt_count)
            print("Category:",category_name)
            print("attempt number:",attempt_number)
            print(
                f"Sending followup for category '{category_name}' "
                f"attempt {attempt_number}/{max_attempts}")
            print(">>> ABOUT TO SEND FOLLOWUP <<<")
            print("Conversation ID:", conversation_id)
            print("Attempt Number:", attempt_number)
            if followup_mode == "template":
                template = get_template_for_attempt(category_name,version, attempt_number)
                print("Template lookup result:",template)

                if not template:
                    print("No template found for this attempt. Skipping.")
                    continue
                draft_id=template['draft_id']
                print("Using template draft id:",draft_id)
                send_followup_reply_template(latest_message_id, draft_id)
                update_after_send(conversation_id, category_name)
            else:
                send_followup_reply_manual(latest_message_id, followup_text)
                update_after_send(conversation_id, category_name)
                '''decision = get_agent_followup_decision(
                    category_name=category_name,
                    subject=subject,
                    body=body,
                    attempt_number=attempt_number,
                    max_attempts=max_attempts,
                    fallback_text=followup_text,
                )
                print("Agent decision:", decision["send_followup"])
                print("Agent reasoning:", decision["reasoning"])
                if decision["send_followup"]:
                    send_followup_reply_manual(latest_message_id, decision["draft_email"])
                    update_after_send(conversation_id, category_name)
                else:
                    print(f"Agent decided to skip this followup for conversation {conversation_id}")
                    continue  '''
                
 
        except Exception as e:
            print(f"Error processing conversation {conversation_id}: {e}")
 
    print("Process completed.")
 
 
if __name__ == "__main__":
    process()
 