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


def _fmt_money(value):
    try:
        from utils.formatters import format_currency
        return format_currency(value)
    except Exception:
        return f"{value}"


def export_sale_invoice(sale_data, filepath):
    """Render a single-sale invoice as a professional A4 PDF.

    ``sale_data`` follows the shape used by ``utils.billing._render_html``.
    Returns ``(success, message)``. Requires reportlab (already an app dep).
    """
    if not HAVE_REPORTLAB:
        return False, "ReportLab is not installed. Run: pip install reportlab"

    try:
        from utils.company import load_company
        from utils.tax import get_tax_engine, is_tax_enabled, get_default_rate
        company = load_company()

        cname = company.get("name") or "Your Business Name"
        caddr = ", ".join(filter(None, [company.get("address", ""), company.get("city", ""),
                                        company.get("state", ""), company.get("pincode", "")]))
        cphone = company.get("phone", "")
        cemail = company.get("email", "")
        cgst = company.get("gstin", "")
        note = company.get("invoice_note") or "Thank you for your business!"

        invoice_id = sale_data.get("invoice_id", f"#{sale_data.get('id', 'N/A')}")
        receipt_no = sale_data.get("receipt_no", "")
        sale_date = sale_data.get("sale_date", "")
        if sale_date and len(sale_date) >= 10:
            try:
                dt = datetime.strptime(sale_date[:10], "%Y-%m-%d")
                sale_date = dt.strftime("%d-%b-%Y")
            except ValueError:
                pass

        item = sale_data.get("item_name", "N/A")
        category = sale_data.get("category", "")
        qty = sale_data.get("quantity_sold", 0)
        price = sale_data.get("price", 0)
        total = sale_data.get("total", 0)
        customer = sale_data.get("customer_name", "Walk-in Customer")
        payment_status = str(sale_data.get("payment_status", "paid")).capitalize()
        paid_amt = sale_data.get("paid_amount", total) or 0
        unpaid_amt = sale_data.get("unpaid_amount", 0) or 0

        tax_rate = float(sale_data.get("tax_rate_percent", get_default_rate()))
        is_interstate = bool(sale_data.get("is_interstate", False))
        tax_lines = []
        grand_total = total
        if tax_rate > 0 and is_tax_enabled():
            engine = get_tax_engine()
            breakdown = engine.compute_tax_breakdown(
                subtotal=total, rate_percent=tax_rate, is_interstate=is_interstate,
                qty=qty, unit_price=price,
            )
            taxable = round(total - breakdown["tax_amount"], 2)
            grand_total = round(total + breakdown["tax_amount"], 2)
            tax_lines.append(("Taxable Amount", _fmt_money(taxable)))
            for comp in breakdown["components"]:
                tax_lines.append((comp["label"], _fmt_money(comp["amount"])))

        doc = SimpleDocTemplate(filepath, pagesize=A4,
                                rightMargins=40, leftMargins=40,
                                topMargins=36, bottomMargins=36)
        styles = getSampleStyleSheet()
        brand = ParagraphStyle("brand", parent=styles["Title"], fontSize=20,
                               textColor=colors.HexColor("#1B2A4A"), alignment=1)
        muted = ParagraphStyle("muted", parent=styles["Normal"], fontSize=9,
                               textColor=colors.HexColor("#64748B"), alignment=1)
        heading = ParagraphStyle("heading", parent=styles["Heading2"],
                                 textColor=colors.HexColor("#2563EB"), alignment=1,
                                 spaceBefore=6, spaceAfter=10)

        elements = []
        elements.append(Paragraph(str(cname), brand))
        if caddr:
            elements.append(Paragraph(caddr, muted))
        contact = " &nbsp;|&nbsp; ".join(filter(None, [
            f"Phone: {cphone}" if cphone else "",
            f"Email: {cemail}" if cemail else "",
        ]))
        if contact:
            elements.append(Paragraph(contact, muted))
        if cgst:
            elements.append(Paragraph(f"GSTIN: {cgst}", muted))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Tax Invoice", heading))

        info = Table([
            ["Invoice #", invoice_id, "Date", sale_date],
            ["Receipt #", receipt_no, "Customer", customer],
            ["Status", payment_status, "", ""],
        ], colWidths=[70, 155, 70, 155])
        info.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#64748B")),
            ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#64748B")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(info)
        elements.append(Spacer(1, 14))

        item_label = str(item)
        if category:
            item_label += f"  ({category})"
        lines = [["Item", "Qty", "Rate", "Amount"],
                 [item_label, str(qty), _fmt_money(price), _fmt_money(grand_total)]]
        t = Table(lines, colWidths=[260, 50, 85, 85])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#2563EB")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)

        totals_rows = [["Subtotal", _fmt_money(total)]]
        totals_rows.extend(tax_lines)
        if payment_status.lower() != "paid":
            totals_rows.append(["Paid", _fmt_money(paid_amt)])
            totals_rows.append(["Balance Due", _fmt_money(unpaid_amt)])
        totals_rows.append(["Total", _fmt_money(total)])

        tot = Table(totals_rows, colWidths=[395, 85])
        tot.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 12),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#2563EB")),
            ("LINEABOVE", (0, -1), (-1, -1), 1.2, colors.HexColor("#2563EB")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(Spacer(1, 4))
        elements.append(tot)

        elements.append(Spacer(1, 22))
        foot = ParagraphStyle("foot", parent=styles["Normal"], fontSize=10,
                              alignment=1, textColor=colors.HexColor("#1E293B"))
        cupi = company.get("upi_id") or ""
        if cupi:
            elements.append(Paragraph(
                f"Pay via UPI: <b>{cupi}</b> — Amount: {_fmt_money(grand_total)}", foot))
        cpay_note = company.get("payment_instructions") or ""
        if cpay_note:
            elements.append(Paragraph(f"Payment: <b>{cpay_note}</b>", foot))
        elements.append(Paragraph(str(note), foot))
        elements.append(Paragraph("This is a computer-generated invoice", muted))

        doc.build(elements)
        return True, filepath
    except Exception as e:  # broad — reportlab raises many exception types
        logger.exception("Invoice PDF export failed")
        return False, f"Invoice PDF failed: {e}"
