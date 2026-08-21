import sqlite3
 
conn = sqlite3.connect("followups.db")  # <-- use your exact DB filename
cursor = conn.cursor()
 
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables:", cursor.fetchall())
 
cursor.execute("SELECT category_name, order_number, draft_id, draft_subject FROM category_templates;")
rows = cursor.fetchall()

#cursor.execute("SELECT primary_folder_id, secondary_folder_id FROM settings")
#print(cursor.fetchall())

cursor.execute("SELECT * FROM category_templates;")
print(cursor.fetchall())

cursor.execute("SELECT order_number, draft_id FROM category_templates WHERE category_name='bulk' ORDER BY order_number;")
print(cursor.fetchall())

cursor.execute("SELECT last_reply_subject, last_reply_body, is_unread_reply FROM followups;")
print(cursor.fetchall())

cursor.execute("UPDATE application_analysis SET next_due_date = '2000-01-01T00:00:00' WHERE appser_number IN ('ASN0000103', 'ASN0000126');")
print(cursor.fetchall())

cursor.execute("SELECT appser_number, frequency, internal_status, next_due_date FROM application_analysis WHERE upload_id = 1;")
print(cursor.fetchall())

cursor.execute("SELECT * FROM action_template_mapping;")
print(cursor.fetchall())

cursor.execute("SELECT * FROM master_control WHERE is_active = 1;")
print(cursor.fetchall())

cursor.execute("SELECT COUNT(*) FROM applications_snapshot;")
print(cursor.fetchall())

cursor.execute("SELECT * FROM action_template_mapping;")
print(cursor.fetchall())

cursor.execute("SELECT appser_number,send_status,last_sent_at,last_draft_id,last_category FROM application_analysis LIMIT 5;")
print(cursor.fetchall())

cursor.execute("SELECT appser_number,send_status,last_sent_at FROM application_analysis WHERE send_status='ACTIVE';")
print(cursor.fetchall())
 
print(cursor.fetchall())

cursor.execute("SELECT * FROM application_meetings;")
print(cursor.fetchall())

cursor.execute("SELECT appser_number,meeting_start FROM application_meetings WHERE appser_number='ASN0000103';")
print(cursor.fetchall())

cursor.execute("SELECT appser_number,conversation_id FROM application_analysis;")
print(cursor.fetchall())

cursor.execute("SELECT conversation_id,original_recipients,last_client_email,last_client_reply_at FROM followups WHERE conversation_id='AAQkAGIwMjg4OGE5LTRiYmItNGIzNS1iYWUzLTVjNTkwN2NlMGQyMwAQAIpv6enu4WFDh_XTKKmlshw=';")
print(cursor.fetchall())

cursor.execute("SELECT appser_number,event_id FROM application_meetings;")
print(cursor.fetchall())

cursor.execute("SELECT comparison_id,appser_number,field_name,change_type FROM comparison_changes WHERE appser_number = 'ASN0001470';")
print(cursor.fetchall())

cursor.execute("SELECT COUNT(*) FROM comparison_logs;")
print(cursor.fetchall())

cursor.execute("SELECT appser_number,COUNT(*) FROM applications_raw_data WHERE upload_id = 2 GROUP BY appser_number HAVING COUNT(*) > 1;")
print(cursor.fetchall())

cursor.execute("SELECT upload_id,COUNT(*) FROM applications_raw_data GROUP BY upload_id ORDER bY upload_id;")
print(cursor.fetchall())

cursor.execute("SELECT COUNT(DISTINCT appser_number)FROM applications_raw_data WHERE upload_id = 2;")
print(cursor.fetchall())

cursor.execute("""
SELECT upload_id, COUNT(*)
FROM applications_raw_data
GROUP BY upload_id
""")
cursor.execute("""
SELECT
COUNT(*),
COUNT(DISTINCT appser_number)
FROM applications_raw_data
WHERE upload_id = 2
""")

 
print(cursor.fetchall())
 
print(cursor.fetchall())
cursor.execute("SELECT remediation_due_date,next_due_date FROM application_analysis WHERE appser_number='ASN0000200';")
print(cursor.fetchall())

cursor.execute("SELECT * FROM comparison_logs ORDER BY id DESC LIMIT 1;")
print(cursor.fetchall())

cursor.execute("SELECT id,field_name,approval_status FROM comparison_changes WHERE comparison_id =1 AND appser_number = 'ASN0000103';")
print(cursor.fetchall())

cursor.execute("SELECT appser_number,field_name,change_type,approval_status FROM comparison_changes WHERE comparison_id = 3 AND appser_number = 'ASN0000203';")
print(cursor.fetchall())

cursor.execute("""SELECT
    upload_id,
    appser_number,
    frequency,
    comments,
    compliance_mode,
    send_status
FROM application_analysis
WHERE appser_number IN ('ASN0000103','ASN0000126');
""")


cursor.execute("SELECT * FROM evidence_uploads;")
print(cursor.fetchall())


print("Settings:", rows)
 
conn.close()