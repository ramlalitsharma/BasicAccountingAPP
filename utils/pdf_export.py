import logging
from datetime import datetime
from config import APP_NAME

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    HAVE_REPORTLAB = True
except ImportError:
    HAVE_REPORTLAB = False


def export_sales_report(data, filepath, title="Sales Report"):
    if not HAVE_REPORTLAB:
        return False, "ReportLab is not installed. Run: pip install reportlab"
    
    try:
        doc = SimpleDocTemplate(filepath, pagesize=A4,
                               rightMargins=30, leftMargins=30,
                               topMargins=30, bottomMargins=30)
        styles = getSampleStyleSheet()
        elements = []
        
        # Title
        elements.append(Paragraph(f"{APP_NAME}", styles["Title"]))
        elements.append(Paragraph(f"{title}", styles["Heading1"]))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                                 styles["Normal"]))
        elements.append(Spacer(1, 12))
        
        if data:
            # Table
            headers = list(data[0].keys()) if data else []
            table_data = [headers]
            for row in data:
                table_data.append([str(row.get(h, "")) for h in headers])
            
            t = Table(table_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B2A4A')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("No data available.", styles["Normal"]))
        
        doc.build(elements)
        return True, "PDF report generated successfully"
    except (ImportError, OSError, Exception) as e:
        # broad catch - reportlab can raise many different exceptions
        logger.exception("PDF export failed")
        return False, f"PDF export failed: {e}"
