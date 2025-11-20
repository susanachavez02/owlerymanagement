import io
from io import BytesIO
from django.template.loader import render_to_string
from datetime import datetime

# Try to import weasyprint, handle error if not installed
try:
    from weasyprint import HTML
except ImportError:
    HTML = None

# UPDATE THIS LINE to include context_data=None
def generate_document_from_template(template_content, template_name, context_data=None):
    """
    Generates a PDF from HTML content using WeasyPrint.
    """
    # Default to empty dict if nothing passed
    if context_data is None:
        context_data = {}
        
    # 1. Render the HTML with context
    # If you don't have a wrapper template, just use the content directly
    try:
        html_string = render_to_string('document_processor_temp.html', {'template_content': template_content, **context_data})
    except Exception:
        # Fallback if the wrapper template doesn't exist or fails
        html_string = template_content

    # 2. Convert to PDF
    if HTML:
        pdf_bytes = HTML(string=html_string).write_pdf()
        buffer = BytesIO(pdf_bytes)
        ext = "pdf"
    else:
        # Fallback if WeasyPrint isn't installed: return text/html
        buffer = BytesIO(html_string.encode('utf-8'))
        ext = "html"

    # 3. Prepare filename
    output_filename = f"{template_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.{ext}"
    
    return buffer, output_filename