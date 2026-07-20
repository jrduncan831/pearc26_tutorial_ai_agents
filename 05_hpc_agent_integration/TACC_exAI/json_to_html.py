import os
import json
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from pygments.formatters import HtmlFormatter
from .utils import display_in_panel

# Configuration
INPUT_FOLDER = "/Users/gjaffe/Documents/Code/TACC_exAI/knowledge_base"
OUTPUT_FOLDER = "/Users/gjaffe/Documents/Code/TACC_exAI/knowledge_base_html"

# Get Pygments Monokai CSS
pygments_css = HtmlFormatter(style='monokai').get_style_defs('.codehilite')

# CSS styles including Monokai syntax highlighting and page padding
CSS_STYLES = f"""
<style>
    body {{
        font-family: Arial, sans-serif;
        max-width: 800px;
        margin: 40px auto;
        line-height: 1.6;
        padding-left: 15px;
        padding-right: 15px;
    }}
    h1 {{ border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
    .description {{ color: #666; font-style: italic; margin-bottom: 20px; }}
    .content {{ margin-top: 20px; }}
    .content p {{ margin-bottom: 1em; }}
    .codehilite {{
        padding: 10px;
        overflow-x: auto;
        border-radius: 4px;
    }}
    .codehilite pre {{
        margin: 0;
        font-family: Consolas, monospace, monospace;
        font-size: 14px;
        line-height: 1.4;
    }}
    {pygments_css}
</style>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    {css}
</head>
<body>
    <h1>{title}</h1>
    <div class="description">{description}</div>
    <div class="content">{content}</div>
</body>
</html>
"""

def render_html_from_json_file(json_path: str, output_folder: str):
    """Renders HTML from a single JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    title = data.get('title', 'No Title')
    description = data.get('description', '')
    content_md = data.get('content', '')

    md = markdown.Markdown(extensions=['fenced_code', CodeHiliteExtension(linenums=False, guess_lang=False)])
    content_html = md.convert(content_md)

    html = HTML_TEMPLATE.format(title=title, description=description, content=content_html, css=CSS_STYLES)
    safe_title = "".join(c if c.isalnum() else "_" for c in title)
    output_file = os.path.join(output_folder, f"{safe_title}.html")
    with open(output_file, 'w', encoding='utf-8') as outf:
        outf.write(html)
    print(f"Rendered {output_file}")

def render_html_from_json_files(input_folder: str, output_folder: str, target_file: str = None):
    """Renders HTML from JSON files in the input folder or a targeted file."""
    os.makedirs(output_folder, exist_ok=True)

    if target_file:
        # Process a single targeted JSON file
        json_path = os.path.join(input_folder, target_file)
        if os.path.exists(json_path):
            render_html_from_json_file(json_path, output_folder)
        else:
            print(f"Target file {target_file} not found in {input_folder}.")
    else:
        # Process all JSON files in the input folder
        json_files = [f for f in os.listdir(input_folder) if f.endswith('.json')]
        md = markdown.Markdown(extensions=['fenced_code', CodeHiliteExtension(linenums=False, guess_lang=False)])
        for json_file in json_files:
            json_path = os.path.join(input_folder, json_file)
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            title = data.get('title', 'No Title')
            description = data.get('description', '')
            content_md = data.get('content', '')
            content_html = md.convert(content_md)
            md.reset()  # reset markdown instance for next file
            html = HTML_TEMPLATE.format(title=title, description=description, content=content_html, css=CSS_STYLES)
            safe_title = "".join(c if c.isalnum() else "_" for c in title)
            output_file = os.path.join(output_folder, f"{safe_title}.html")
            with open(output_file, 'w', encoding='utf-8') as outf:
                outf.write(html)
            display_in_panel(f"Rendered {output_file}", title="HTML Conversion Successful" )

if __name__ == "__main__":
    # To process all JSON files
    # render_html_from_json_files(INPUT_FOLDER, OUTPUT_FOLDER)
    
    # To process a targeted JSON file
    target_file = "String Panel Display Script.json"  # Replace with your target file name
    render_html_from_json_files(INPUT_FOLDER, OUTPUT_FOLDER, target_file)
