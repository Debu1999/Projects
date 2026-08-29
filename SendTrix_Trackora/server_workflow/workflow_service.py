from server_workflow.parser import load_server_workbook
from server_workflow.processor import build_server_inventory
from server_workflow.attachment_builder import generate_hostname_attachment
from server_workflow.grouping import (
    group_per_hostname,
    group_by_owner
)
 
 
def prepare_server_workflow(
    file_path,
    mode="hostname"
):
 
    print("\nStarting server workflow...\n")
 
    # ==========================
    # Load workbook
    # ==========================
 
    workbook = load_server_workbook(
        file_path
    )
 
    # ==========================
    # Build inventory
    # ==========================
 
    inventory = build_server_inventory(
        workbook
    )
 
    # ==========================
    # Generate attachments
    # ==========================
 
    for item in inventory:
 
        attachment = generate_hostname_attachment(
            item
        )
 
        item["attachment_path"] = attachment
 
    # ==========================
    # Apply grouping mode
    # ==========================
 
    if mode == "hostname":
 
        grouped = group_per_hostname(
            inventory
        )
 
    elif mode == "owner":
 
        grouped = group_by_owner(
            inventory
        )
 
    else:
 
        raise Exception(
            f"Invalid workflow mode: {mode}"
        )
 
    print(
        f"\nWorkflow completed. "
        f"Generated {len(grouped)} mail groups."
    )
 
    return grouped
