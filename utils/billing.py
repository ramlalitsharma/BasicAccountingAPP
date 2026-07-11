import os
import tempfile
import webbrowser
import html
from datetime import datetime
from utils.company import load_company
from utils.formatters import format_currency


def _h(value):
    return html.escape(str(value or ""), quote=True)


def _render_html(sale_data):
    company = load_company()
    has_gst = bool(company.get("gstin"))

    cname = company.get("name") or "Your Business Name"
    caddr = company.get("address") or ""
    ccity = company.get("city") or ""
    cstate = company.get("state") or ""
    cpincode = company.get("pincode") or ""
    cphone = company.get("phone") or ""
    cemail = company.get("email") or ""
    cgst = company.get("gstin") or ""
    cpan = company.get("pan") or ""
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
    payment_status = sale_data.get("payment_status", "paid").capitalize()
    paid_amt = sale_data.get("paid_amount", total) or 0
    unpaid_amt = sale_data.get("unpaid_amount", 0) or 0

    tax_rows = ""
    if has_gst:
        total_val = sale_data.get("total", 0)
        taxable = round(total_val / 1.18, 2) if total_val else 0
        cgst_amt = round(taxable * 0.09, 2)
        sgst_amt = round(taxable * 0.09, 2)
        tax_rows = f"""
        <tr><td>Taxable Amount</td><td class="amt">{format_currency(taxable)}</td></tr>
        <tr><td>CGST @ 9%</td><td class="amt">{format_currency(cgst_amt)}</td></tr>
        <tr><td>SGST @ 9%</td><td class="amt">{format_currency(sgst_amt)}</td></tr>"""

    payment_rows = ""
    if payment_status.lower() != "paid":
        payment_rows = f"""
        <tr><td>Paid</td><td class="amt">{format_currency(paid_amt)}</td></tr>
        <tr><td>Balance</td><td class="amt">{format_currency(unpaid_amt)}</td></tr>"""

    eh = _h
    addr_parts = [eh(caddr)]
    city_line = ", ".join(filter(None, [eh(ccity), eh(cstate), eh(cpincode)]))
    if city_line:
        addr_parts.append(city_line)
    addr_html = "<br>".join(addr_parts) if any(addr_parts) else ""

    contact_parts = []
    if cphone:
        contact_parts.append(f"Phone: {eh(cphone)}")
    if cemail:
        contact_parts.append(f"Email: {eh(cemail)}")
    contact_html = "<br>".join(contact_parts)

    gst_pan_html = ""
    if cgst:
        gst_pan_html += f"GSTIN: {eh(cgst)}<br>"
    if cpan:
        gst_pan_html += f"PAN: {eh(cpan)}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Invoice {eh(invoice_id)}</title>
<style>
  @page {{ margin: 12mm; size: auto; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', 'DejaVu Sans', Arial, sans-serif;
    color: #1e293b;
    line-height: 1.5;
    max-width: 750px;
    margin: 0 auto;
    padding: 28px 24px;
    background: #fff;
  }}
  .header {{ text-align: center; margin-bottom: 22px; border-bottom: 3px solid #2563eb; padding-bottom: 18px; }}
  .header h1 {{ font-size: 22px; color: #1e293b; letter-spacing: 0.5px; margin-bottom: 4px; }}
  .header .addr {{ font-size: 13px; color: #64748b; }}
  .header .contact {{ font-size: 13px; color: #64748b; }}
  .header .gst-pan {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
  .title-row {{ text-align: center; margin-bottom: 18px; }}
  .title-row h2 {{ font-size: 18px; color: #2563eb; letter-spacing: 2px; text-transform: uppercase; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 18px; background: #f8fafc; border-radius: 6px; padding: 14px 16px; }}
  .info-grid .left {{ text-align: left; }}
  .info-grid .right {{ text-align: right; }}
  .info-grid .label {{ font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
  .info-grid .value {{ font-size: 14px; color: #1e293b; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
  th {{ background: #2563eb; color: #fff; font-size: 13px; text-align: left; padding: 10px 12px; }}
  th.amt {{ text-align: right; }}
  td {{ padding: 10px 12px; font-size: 14px; border-bottom: 1px solid #e2e8f0; }}
  td.amt {{ text-align: right; font-weight: 600; }}
  .totals {{ margin-left: auto; width: 320px; }}
  .totals table {{ margin-bottom: 0; }}
  .totals td {{ border-bottom: none; padding: 5px 12px; font-size: 14px; }}
  .totals .grand-total td {{ font-size: 17px; font-weight: 700; border-top: 2px solid #2563eb; padding-top: 8px; color: #2563eb; }}
  .footer {{ text-align: center; margin-top: 24px; padding-top: 16px; border-top: 2px solid #e2e8f0; font-size: 13px; color: #64748b; }}
  .footer .note {{ font-size: 14px; color: #1e293b; font-weight: 600; margin-bottom: 4px; }}
  .print-btn {{ display: block; width: 200px; margin: 24px auto 0; padding: 10px 0; background: #2563eb; color: #fff; border: none; border-radius: 6px; font-size: 15px; cursor: pointer; text-align: center; }}
  .print-btn:hover {{ background: #1d4ed8; }}
  @media print {{
    body {{ padding: 0; }}
    .print-btn {{ display: none; }}
    .info-grid {{ background: #f8fafc !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    th {{ background: #2563eb !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>{eh(cname)}</h1>
    {f'<div class="addr">{addr_html}</div>' if addr_html else ''}
    {f'<div class="contact">{contact_html}</div>' if contact_html else ''}
    {f'<div class="gst-pan">{gst_pan_html}</div>' if gst_pan_html else ''}
  </div>

  <div class="title-row"><h2>Tax Invoice</h2></div>

  <div class="info-grid">
    <div class="left">
      <div class="label">Invoice #</div>
      <div class="value">{eh(invoice_id)}</div>
    </div>
    <div class="right">
      <div class="label">Date</div>
      <div class="value">{eh(sale_date)}</div>
    </div>
    <div class="left">
      <div class="label">Receipt #</div>
      <div class="value">{eh(receipt_no)}</div>
    </div>
    <div class="right">
      <div class="label">Customer</div>
      <div class="value">{eh(customer)}</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width:45%">Item</th>
        <th style="width:15%" class="amt">Qty</th>
        <th style="width:20%" class="amt">Rate</th>
        <th style="width:20%" class="amt">Amount</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>{eh(item)}{f' <br><span style="font-size:12px;color:#94a3b8;">{eh(category)}</span>' if category else ''}</td>
        <td class="amt">{qty}</td>
        <td class="amt">{format_currency(price)}</td>
        <td class="amt">{format_currency(total)}</td>
      </tr>
    </tbody>
  </table>

  <div class="totals">
    <table>
      <tr><td>Subtotal</td><td class="amt">{format_currency(total)}</td></tr>
      {tax_rows}
      {payment_rows}
      <tr class="grand-total"><td>Total</td><td class="amt">{format_currency(total)}</td></tr>
    </table>
  </div>

  <div class="footer">
    <div class="note">{eh(note)}</div>
    <div style="font-size:11px;color:#94a3b8;margin-top:6px;">This is a computer-generated invoice</div>
  </div>

  <button class="print-btn" onclick="window.print()">\U0001f5a8\ufe0f  Print / Save PDF</button>
</body>
</html>"""


def print_bill(sale_data):
    html = _render_html(sale_data)
    tmp = os.path.join(tempfile.gettempdir(),
                       f"invoice_{sale_data.get('id', 0)}.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(tmp)
