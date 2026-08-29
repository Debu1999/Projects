import os
 
def generate_hostname_attachment(item):
 
    hostname = item["hostname"]
 
    filtered_df = item["_filtered_critical"]
 
    # ==========================
    # Skip empty vulnerabilities
    # ==========================
 
    if filtered_df.empty:
 
        print(f"No critical vulnerabilities for {hostname}")
 
        return None
 
    # ==========================
    # Ensure temp folder exists
    # ==========================
 
    output_folder = "temp_attachments"
 
    os.makedirs(output_folder, exist_ok=True)
 
    # ==========================
    # Build file path
    # ==========================
 
    safe_hostname = hostname.replace("/", "_")
 
    file_path = os.path.join(
        output_folder,
        f"{safe_hostname}.xlsx"
    )
 
    # ==========================
    # Export Excel
    # ==========================
 
    filtered_df.to_excel(
        file_path,
        index=False
    )
 
    print(f"Generated attachment: {file_path}")
 
    return file_path