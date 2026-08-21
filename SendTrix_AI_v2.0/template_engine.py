import re
import html
 
# ==========================
# Extract placeholders
# ==========================
def extract_placeholders(text):
    pattern = r"{{\s*([a-zA-Z0-9_]+)\s*}}"
    return set(re.findall(pattern, text))
 
 
# ==========================
# Render dynamically
# ==========================
def render_dynamic(text, data_dict, strict=False):
 
    lower_dict = {
        k.lower(): "" if v is None or str(v).lower() == "nan" else str(v)
        for k, v in data_dict.items()
    }
 
    def replace_match(match):
        key = match.group(1).strip().lower()
 
        if key not in lower_dict or (strict and lower_dict[key].strip() == ""):
            if strict:
                raise Exception(f"Missing value for placeholder: {key}")
            return ""
 
        return html.escape(lower_dict[key])
 
    pattern = r"{{\s*([a-zA-Z0-9_]+)\s*}}"
    return re.sub(pattern, replace_match, text)
def render_consolidated_template(text, bulk_data, applications):
    """
    Render a consolidated Trackora email template.
 
    Bulk placeholders:
        {{owner}}
        {{application_count}}
        {{selected_asns}}
 
    Application placeholders must be inside:
 
        {{#applications}}
        {{asn}}
        {{name}}
        {{tech_owner}}
        {{version}}
        {{status}}
        {{vendor}}
        {{/applications}}
    """
 
    # ---------------------------------
    # 1. Find application blocks FIRST
    # ---------------------------------
 
    pattern = r"{{\s*#applications\s*}}(.*?){{\s*/applications\s*}}"
 
    def render_application_block(match):
 
        block_template = match.group(1)
 
        rendered_applications = []
 
        for application in applications:
 
            rendered_block = render_dynamic(
                block_template,
                application,
                strict=True
            )
 
            rendered_applications.append(
                rendered_block
            )
 
        return "\n".join(rendered_applications)
 
    # ---------------------------------
    # 2. Expand application blocks
    # ---------------------------------
 
    rendered = re.sub(
        pattern,
        render_application_block,
        text,
        flags=re.DOTALL
    )
 
    # ---------------------------------
    # 3. Render bulk-level placeholders
    # ---------------------------------
 
    rendered = render_dynamic(
        rendered,
        bulk_data,
        strict=True
    )
 
    return rendered
 