import markdown
from xhtml2pdf import pisa
import os

# Define paths
input_filename = r"C:\Users\Goutham Srinath\.gemini\antigravity\brain\c60eecd9-528a-4287-8020-08635a89ead3\project_documentation.md"
output_filename = r"C:\Users\Goutham Srinath\.gemini\antigravity\brain\c60eecd9-528a-4287-8020-08635a89ead3\project_documentation.pdf"

# Read Markdown
with open(input_filename, "r", encoding="utf-8") as f:
    text = f.read()

# Convert to HTML
# We add some CSS to make it look decent
html_text = markdown.markdown(text, extensions=['tables', 'fenced_code'])

full_html = f"""
<html>
<head>
<style>
    body {{ font-family: Helvetica, sans-serif; font-size: 12px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
    code {{ background-color: #f4f4f4; padding: 2px 5px; font-family: monospace; }}
    pre {{ background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd; white-space: pre-wrap; }}
    h1 {{ color: #333; }}
    h2 {{ color: #555; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
</style>
</head>
<body>
{html_text}
</body>
</html>
"""

# Convert to PDF
with open(output_filename, "wb") as result_file:
    pisa_status = pisa.CreatePDF(full_html, dest=result_file)

if pisa_status.err:
    print("Error during PDF generation")
else:
    print(f"Successfully created PDF at: {output_filename}")
