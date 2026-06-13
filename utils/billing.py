import os
import tempfile
from datetime import datetime
from utils.company import load_company


def generate_invoice_text(sale_data):
    company = load_company()
    has_gst = bool(company.get("gstin"))

    cname = company.get("name") or "Your Business Name"
    caddr = company.get("address") or ""
    ccity = company.get("city") or ""
    cstate = company.get("state") or ""
    cphone = company.get("phone") or ""
    cgst = company.get("gstin") or ""
    cpan = company.get("pan") or ""
    note = company.get("invoice_note") or "Thank you for your business!"

    invoice_id = sale_data.get("invoice_id", f"#{sale_data.get('id', 'N/A')}")
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

    w = 56
    lines = []
    lines.append("=" * w)
    lines.append(f"{cname:^{w}}")
    lines.append("=" * w)
    if caddr:
        lines.append(f"{caddr:^{w}}")
    if ccity and cstate:
        lines.append(f"{ccity}, {cstate:^{w - len(ccity) - 2}}")
    if cphone:
        lines.append(f"Phone: {cphone:>{w - 7}}")
    if cgst:
        lines.append(f"GSTIN: {cgst:>{w - 6}}")
    if cpan:
        lines.append(f"PAN: {cpan:>{w - 4}}")
    lines.append("-" * w)
    lines.append(" " * 18 + "TAX INVOICE")
    lines.append("-" * w)
    lines.append(f"  Invoice #:    {invoice_id}")
    lines.append(f"  Date:         {sale_date}")
    if has_gst:
        total = sale_data.get("total", 0)
        taxable = round(total / 1.18, 2) if total else 0
        cgst_amt = round(taxable * 0.09, 2)
        sgst_amt = round(taxable * 0.09, 2)
        lines.append(f"  Taxable Amt:  \u20B9{taxable:>8,.2f}")
        lines.append(f"  CGST @9%:     \u20B9{cgst_amt:>8,.2f}")
        lines.append(f"  SGST @9%:     \u20B9{sgst_amt:>8,.2f}")
    lines.append("-" * w)
    lines.append(f"  {'Item:':11}{item}")
    if category:
        lines.append(f"  {'Category:':11}{category}")
    lines.append(f"  {'Quantity:':11}{qty}")
    lines.append(f"  {'Unit Price:':11}\u20B9{price:>8,.2f}")
    lines.append("-" * w)
    lines.append(f"  {'TOTAL AMOUNT:':25}\u20B9{total:>8,.2f}")
    lines.append("=" * w)
    lines.append(f"{note:^{w}}")
    lines.append("=" * w)
    return "\n".join(lines)


def print_bill(sale_data):
    text = generate_invoice_text(sale_data)
    tmp = os.path.join(tempfile.gettempdir(),
                       f"invoice_{sale_data.get('id', 0)}.txt")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.startfile(tmp)
