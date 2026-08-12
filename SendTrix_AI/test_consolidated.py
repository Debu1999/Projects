from template_engine import render_consolidated_template
from dr
applications = [
    {
        "asn": "ASN001",
        "name": "Application A",
        "owner": "John",
        "tech_owner": "Alice",
        "version": "1.2",
        "status": "Installed",
        "vendor": "Vendor A"
    },
    {
        "asn": "ASN002",
        "name": "Application B",
        "owner": "John",
        "tech_owner": "Bob",
        "version": "4.5",
        "status": "Installed",
        "vendor": "Vendor B"
    },
    {
        "asn": "ASN003",
        "name": "Application C",
        "owner": "John",
        "tech_owner": "Charlie",
        "version": "3.1",
        "status": "Installed",
        "vendor": "Vendor C"
    }
]
 
bulk_data = {
    "owner": "John",
    "application_count": 3,
    "selected_asns": "ASN001, ASN002, ASN003"
}
 
subject_template = "Compliance Review - {{selected_asns}}"
 
body_template = """
Hello {{owner}},
 
You have {{application_count}} applications requiring compliance review.
 
{{#applications}}
 
ASN: {{asn}}
Application: {{name}}
Technical Owner: {{tech_owner}}
Version: {{version}}
Status: {{status}}
Vendor: {{vendor}}
 
{{/applications}}
 
Regards,
Trackora
"""
 
print(
    render_consolidated_template(
        subject_template,
        bulk_data,
        applications
    )
)
 
print(
    render_consolidated_template(
        body_template,
        bulk_data,
        applications
    )
)
 