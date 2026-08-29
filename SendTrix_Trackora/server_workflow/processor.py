def build_server_inventory(workbook_data):
 
    vm_df = workbook_data["vm list"]
    critical_df = workbook_data["critical"]
 
    results = []
 
    print("\nProcessing hostnames...\n")
 
    for _, row in vm_df.iterrows():
 
        hostname = str(
            row["hostname"]
        ).strip()
 
        if not hostname or hostname == "nan":
            continue
 
        assigned_to = str(
            row.get("assigned_to", "")
        ).strip()
 
        assigned_email = str(
            row.get("assigned_to_email", "")
        ).strip()
 
        # ==========================
        # Filter Critical Sheet
        # ==========================
 
        filtered_critical = critical_df[
            critical_df["hostname"].astype(str).str.strip() == hostname
        ]
 
        new_item = row.to_dict()
        new_item["hostname"] = hostname
        new_item["assigned_to"] = assigned_to
        new_item["assigned_email"] = assigned_email
        new_item["_filtered_critical"] = filtered_critical
        results.append(new_item)
 
    print(f"Processed {len(results)} hostnames.")
 
    return results