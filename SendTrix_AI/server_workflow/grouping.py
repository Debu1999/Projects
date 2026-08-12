def group_per_hostname(inventory):
 
    grouped = []
 
    for item in inventory:
 
        new_item = dict(item)
        new_item.pop("_filtered_critical",None)
        new_item["assigned_to_email"] = item["assigned_email"]
        new_item["attachments"] = [
            item["attachment_path"]
        ]
        grouped.append(new_item)
 
    return grouped
def group_by_owner(inventory):
 
    grouped = {}
 
    for item in inventory:
 
        email = item["assigned_email"]
 
        if not email or email == "nan":
            continue
 
        # ==========================
        # Create owner bucket
        # ==========================
 
        if email not in grouped:
            grouped[email] = dict(item)
            grouped[email].pop("_filtered_critical",None)
            grouped[email]["assigned_to_email"] = email
            grouped[email]["hostnames"] = []
            grouped[email]["attachments"] = []
 
        # ==========================
        # Append hostname
        # ==========================
 
        grouped[email]["hostnames"].append(
            item["hostname"]
        )
 
        # ==========================
        # Append attachment
        # ==========================
 
        attachment = item.get("attachment_path")
 
        if attachment:
            grouped[email]["attachments"].append(
                attachment
            )

    for email, data in grouped.items():
        data["hostnames"]=", ".join(data["hostnames"])
 
    return list(grouped.values())
