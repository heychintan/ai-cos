def assemble_context(luma: str, spotify: str, webflow: str, template: str) -> str:
    return f"""=== DATA CONTEXT ===
{luma}
{spotify}
{webflow}

=== TEMPLATE & INSTRUCTIONS ===
{template}

=== YOUR TASK ===
Using the data above and following the template exactly, generate the newsletter draft.
"""
