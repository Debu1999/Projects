from graph_client import get_sent_with_category
from db import insert_or_resume_followup, get_connection
 
 
def get_all_categories():
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("SELECT DISTINCT category_name FROM settings")
    rows = cursor.fetchall()
 
    conn.close()
 
    return [row[0] for row in rows]
 
 
def sync():
 
    categories = get_all_categories()
 
    if not categories:
        print("No categories configured. Please create a category first.")
        return
 
    total_new = 0
    total_skipped = 0
 
    for category_name in categories:
 
        print(f"Syncing category: {category_name}")
 
        messages = get_sent_with_category(category_name)
 
        for msg in messages:
 
            if not msg.get("conversationId"):
                continue
            to_list = msg.get("toRecipients", [])
            cc_list = msg.get("ccRecipients", [])
            all_recipients = []
            for r in to_list + cc_list:
                address = (
                    r.get("emailAddress", {})
                    .get("address", "")
                    .strip()
                    .lower()
                )
                if address:
                    all_recipients.append(address)

            recipients_str = ",".join(all_recipients)
            result = insert_or_resume_followup(msg, category_name,recipients_str)
 
            if result == "inserted":
                print("Inserted:", msg["id"])
                total_new += 1
 
            elif result == "skipped existing":
                #print("Resumed tracking:", msg["id"])
                total_skipped += 1
 
    print(f"[+] {total_new} new followups detected")
    print(f"[+] {total_skipped} already tracked")
 