import sys, os, tempfile
from datetime import datetime
os.environ["DISPLAY"] = ""

sys.path.insert(0, os.path.dirname(__file__))

from database import models
from config import get_color, set_setting, get_color, _LIGHT_COLORS, _DARK_COLORS


def safe_float_c(v):
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0

errors = []

def check(cond, msg):
    if not cond:
        errors.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  OK: {msg}")

# 1. Theme system
print("1. Testing get_color()...")
set_setting("theme", "Light")
check(get_color("BG_COLOR") == "#F1F5F9", "Light BG")
set_setting("theme", "Dark")
check(get_color("BG_COLOR") == "#0F172A", "Dark BG")
all_light = {k for k in _LIGHT_COLORS}
all_dark = {k for k in _DARK_COLORS}
check(all_light == all_dark, "Palette keys match")
set_setting("theme", "Light")

# 2. Workbook + CRUD
print("\n2. Testing full workflow...")
tmpdir = tempfile.mkdtemp()
os.environ["ACCOUNTING_DATA_DIR"] = tmpdir
wb_path = models.create_new_workbook()
check(os.path.exists(wb_path), "Workbook created")
check(models.get_active_file() is not None, "Active file set")

sid = models.add_stock_item("TestItem", "Category1", 100, 10, 50.0, 75.0, None)
check(sid is not None and sid > 0, f"Stock item created (ID={sid})")

cid = models.add_customer("TestCustomer", "1234567890", "Addr1")
check(cid is not None and cid > 0, f"Customer created (ID={cid})")

sale_id, receipt = models.record_sale(sid, 5, 75.0, customer_id=cid, payment_status="paid")
check(sale_id > 0 and receipt.startswith("RCP-"), f"Sale recorded (ID={sale_id})")

eid = models.add_extra_income("Freelance", "Web dev", 5000, "Services", "Bank", "REF001")
check(eid > 0, f"Extra income created (ID={eid})")
incomes = models.get_extra_income()
check(len(incomes) >= 1, "get_extra_income returns data")

# 3. Preorder with advance
print("\n3. Testing preorder advance fields...")
poid = models.add_preorder(cid, sid, 3, 80.0, "2026-08-01",
    notes="Test", delivery_address="123 Main St",
    advance_amount=120.0, advance_type="partial")
check(poid > 0, f"Preorder created (ID={poid})")
po = models.get_preorder(poid)
check(po is not None, "get_preorder returns data")
check(po.get("Advance_Amount") == 120.0, f"Advance amount = {po.get('Advance_Amount')}")
check(po.get("Advance_Payment_Type") == "partial", f"Advance type = {po.get('Advance_Payment_Type')}")
check(po.get("Delivery_Address") == "123 Main St", f"Address = {po.get('Delivery_Address')}")

# 4. Complete preorder -> sale
print("\n4. Testing complete_preorder advance transfer...")
sale2_id, receipt2 = models.complete_preorder(poid)
check(sale2_id > 0, f"Completed sale created (ID={sale2_id})")
completed = models.get_preorder(poid)
check(completed is None, "Completed preorder removed from list (by design)")
all_sales = models.get_sales()
cs = [s for s in all_sales if s["ID"] == sale2_id]
check(len(cs) == 1, "Sale found in get_sales")
s = cs[0]
check(s["Payment_Status"] == "partial", f"Payment status = {s['Payment_Status']}")
check(s["Paid_Amount"] == 120.0, f"Paid amount = {s['Paid_Amount']}")
check(s["Unpaid_Amount"] == 120.0, f"Unpaid amount = {s['Unpaid_Amount']}")

# 5. Full advance preorder
print("\n5. Testing full advance...")
poid2 = models.add_preorder(cid, sid, 2, 100.0, "2026-09-01",
    advance_amount=200.0, advance_type="full")
sale3_id, _ = models.complete_preorder(poid2)
s3 = [s for s in models.get_sales() if s["ID"] == sale3_id][0]
check(s3["Payment_Status"] == "paid", f"Full advance status = {s3['Payment_Status']}")
check(s3["Paid_Amount"] == 200.0, f"Full advance paid = {s3['Paid_Amount']}")

# 6. Search sales
print("\n6. Testing sales search...")
found = models.get_sales(search="TestItem")
check(len(found) > 0, "Search by item name")
found = models.get_sales(search="TestCustomer")
check(len(found) > 0, "Search by customer name")

# 7. Update preorder
print("\n7. Testing update_preorder with new fields...")
poid3 = models.add_preorder(cid, sid, 1, 50.0, "2026-10-01")
models.update_preorder(poid3, cid, sid, 2, 60.0, "2026-11-01",
    notes="Updated", delivery_address="456 Oak St",
    advance_amount=50.0, advance_type="partial")
po3 = models.get_preorder(poid3)
check(po3["Quantity"] == 2, "Updated quantity")
check(po3.get("Delivery_Address") == "456 Oak St", "Updated address")
check(po3.get("Advance_Amount") == 50.0, "Updated advance")

# 8. Notifications (offline smoke test — no network)
print("\n8. Testing notifications plumbing...")
from utils import notifier

cid2 = models.add_customer("NotifyCust", "", "", email="cust@example.com",
                           phone="+919999999999", notify_email=True, notify_whatsapp=True)
cust2 = models.get_customer(cid2)
check(cust2.get("Email") == "cust@example.com", "Customer email persisted")
check(cust2.get("Notify_Email") == "Yes", "Customer email opt-in persisted")
check(cust2.get("Notify_WhatsApp") == "Yes", "Customer WhatsApp opt-in persisted")

receipt = notifier.build_sale_receipt_text({
    "receipt_no": "RCP-000099", "item_name": "TestItem",
    "quantity_sold": 2, "price": 50.0, "total": 100.0,
    "payment_status": "partial", "paid_amount": 40.0, "unpaid_amount": 60.0,
    "sale_date": "2026-09-23 10:00:00"}, customer_name="NotifyCust")
check("RCP-000099" in receipt and "NotifyCust" in receipt, "Receipt text renders")
check("Balance" in receipt, "Receipt shows balance for partial payment")

results = notifier.notify_after_sale(cust2, {
    "receipt_no": "RCP-000098", "item_name": "TestItem",
    "quantity_sold": 1, "price": 10.0, "total": 10.0,
    "payment_status": "paid", "paid_amount": 10.0, "unpaid_amount": 0.0,
    "sale_date": "2026-09-23 10:00:00"})
check(isinstance(results, list), "notify_after_sale returns list")
not_opted = models.get_customer(cid)  # TestCustomer — no opt-in
results2 = notifier.notify_after_sale(not_opted, {"receipt_no": "RCP-000097"})
check(results2 == [], "No notifications when customer has not opted in")

notifier.save_smtp_password("test-secret-123")
check(notifier.load_smtp_password() == "test-secret-123", "SMTP password DPAPI roundtrip")
notifier.save_smtp_password("")
check(notifier.load_smtp_password() == "", "SMTP password cleared")

# 9. Payment reminders (offline smoke test)
print("\n9. Testing payment reminders...")
reminder_text = notifier.build_payment_reminder_text(
    "NotifyCust", 60.0,
    [{"Receipt_No": "RCP-000098", "Sale_Date": "2026-09-23 10:00:00", "Unpaid_Amount": 60.0}])
check("NotifyCust" in reminder_text and "RCP-000098" in reminder_text, "Reminder text renders with bill list")
check("60" in reminder_text, "Reminder includes due amount")
rem_res = notifier.send_payment_reminder(cust2, 60.0, [])
check(isinstance(rem_res, list) and all(len(r) == 3 for r in rem_res), "send_payment_reminder returns channel results")
not_opted2 = models.get_customer(cid)
rem_res2 = notifier.send_payment_reminder(not_opted2, 10.0, [])
check(rem_res2 and rem_res2[-1][0] == "reminder" and rem_res2[-1][1] is False,
      "Reminder refuses non-opted-in customer")

# 10. PDF invoice export
print("\n10. Testing PDF invoice export...")
from utils.pdf_export import export_sale_invoice, HAVE_REPORTLAB
if HAVE_REPORTLAB:
    pdf_path = os.path.join(tmpdir, "test_invoice.pdf")
    ok, msg = export_sale_invoice({
        "id": 99, "invoice_id": "#99", "receipt_no": "RCP-000099",
        "item_name": "TestItem", "category": "Category1",
        "quantity_sold": 2, "price": 50.0, "total": 100.0,
        "payment_status": "partial", "paid_amount": 40.0, "unpaid_amount": 60.0,
        "customer_name": "NotifyCust", "sale_date": "2026-09-23 10:00:00",
    }, pdf_path)
    check(ok and os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000,
          f"PDF invoice generated ({msg})")
    with open(pdf_path, "rb") as f:
        check(f.read(4) == b"%PDF", "PDF file has valid header")
else:
    check(True, "ReportLab not installed — skipped (runtime guard active)")

# 11. Vertical extra fields (pharmacy: batch + expiry)
print("\n11. Testing vertical extra fields + expiry tracking...")
from utils.verticals import get_stock_field_defs, get_customer_field_defs
p_stock = get_stock_field_defs("pharmacy")
check(any(d["column"] == "Expiry_Date" for _, d in p_stock), "Pharmacy stock extras include Expiry_Date")
check(any(d["column"] == "Batch_No" for _, d in p_stock), "Pharmacy stock extras include Batch_No")
check(any(d["column"] == "Doctor_Name" for _, d in get_customer_field_defs("pharmacy")),
      "Pharmacy customer extras include Doctor_Name")
check(get_stock_field_defs("general") == [], "General vertical has no extra stock fields")

sid2 = models.add_stock_item("ExpiryItem", "Medicines", 20, 10, 30.0, 5, None,
                             extras={"Batch_No": "B-001", "Expiry_Date": "2026-10-15",
                                     "Drug_Schedule": "H1"})
item2 = models.get_stock_item(sid2)
check(item2.get("Batch_No") == "B-001", "Stock extra Batch_No persisted")
check(item2.get("Expiry_Date") == "2026-10-15", "Stock extra Expiry_Date persisted")

models.update_stock_item(sid2, "ExpiryItem", "Medicines", 18, 5, 10, 30.0, None,
                         extras={"Batch_No": "B-002"})
check(models.get_stock_item(sid2).get("Batch_No") == "B-002", "Stock extras updated")
check(models.get_stock_item(sid2).get("Expiry_Date") == "2026-10-15",
      "Expiry kept when not overwritten")

expiring = models.get_expiring_items(400)
check(any(it.get("ID") == sid2 for it in expiring), "get_expiring_items finds item")
expiring_none = models.get_expiring_items(0)
check(not any(it.get("ID") == sid2 for it in expiring_none),
      "get_expiring_items excludes far-future expiry")

models.add_customer("PharmaCust", "999", "", extras={"Doctor_Name": "Dr. Rao", "Prescription_No": "RX-1"})
pc = models.get_customers()[-1]
check(pc.get("Doctor_Name") == "Dr. Rao", "Customer extras persisted")

# 12. Report data helpers (P&L / tax / top items math)
print("\n12. Testing report data helpers...")
from utils.tax import get_tax_engine, is_tax_enabled, get_default_rate
yr = datetime.now().year
sales_now = models.get_sales()
check(len(sales_now) >= 1, "Sales exist for report math")
monthly = models.get_yearly_report(yr)
check(any(m.get("sale_count", 0) > 0 for m in monthly), "Yearly report aggregates sales")
engine = get_tax_engine()
bd = engine.compute_tax_breakdown(subtotal=1000.0, rate_percent=18.0)
comp_sum = round(sum(c["amount"] for c in bd["components"]), 2)
check(round(bd["tax_amount"], 2) == comp_sum, "Tax breakdown components sum to total tax")
check(bd["tax_amount"] > 0, "Tax amount positive at 18%")

# 13. Per-user preference plumbing
print("\n13. Testing per-user preferences...")
from utils.settings_helper import get_user_setting, set_user_setting
set_setting("nav.start_page", "dashboard")
set_user_setting("dashboard.hidden_cards", ["low_stock"])  # no session -> global key
check(get_user_setting("nav.start_page") == "dashboard", "Global start page read")
check(get_user_setting("dashboard.hidden_cards") == ["low_stock"], "Hidden cards roundtrip")
set_user_setting("dashboard.hidden_cards", [])

# 14. CRM: credit limit + customer statement
print("\n14. Testing CRM (credit limit + statement)...")
cid3 = models.add_customer("CreditCust", "888", "", extras={"Credit_Limit": 150.0})
c3 = models.get_customer(cid3)
check(safe_float_c(c3.get("Credit_Limit")) == 150.0, "Credit_Limit persisted")
models.record_sale(sid, 1, 100.0, customer_id=cid3, payment_status="unpaid")
models.record_sale(sid, 1, 100.0, customer_id=cid3, payment_status="partial",
                   paid_amount=60.0, unpaid_amount=40.0)
stmt = models.get_customer_statement(cid3)
check(len(stmt) == 2, "Statement lists customer sales")
check(stmt[-1]["running_balance"] == 140.0, f"Running balance = {stmt[-1]['running_balance']}")
check(models.get_customer_due(cid3) == 140.0, "get_customer_due sums unpaid")
stmt2 = models.get_customer_statement(cid)
check(all(r.get("Customer_ID") == cid for r in stmt2), "Statement isolated per customer")

# 15. Cloud backup plumbing (offline — no real upload)
print("\n15. Testing cloud backup plumbing...")
from utils import cloud_backup
set_setting("cloud_backup.enabled", False)
ok, msg = cloud_backup.upload_backup_file("nonexistent.xlsx")
check(not ok and "disabled" in msg.lower(), "Upload refuses when disabled")
set_setting("cloud_backup.enabled", True)
set_setting("cloud_backup.endpoint", "http://example.com/insecure")
ok, msg = cloud_backup.upload_backup_file(os.path.join(tmpdir, "test_invoice.pdf"))
check(not ok and "https" in msg.lower(), "Upload enforces HTTPS endpoint")
check(cloud_backup._allowed_url("https://x.workers.dev/api/backup"), "HTTPS endpoint allowed")
check(not cloud_backup._allowed_url("http://example.com"), "http endpoint rejected")
body, boundary = cloud_backup._multipart_body({"machine_id": "abc"}, "file", os.path.join(tmpdir, "test_invoice.pdf"))
check(boundary.encode() in body and b"machine_id" in body and b"%PDF" in body,
      "Multipart body contains fields + file bytes")
cloud_backup.save_token("tok-123")
check(cloud_backup.load_token() == "tok-123", "Backup API token DPAPI roundtrip")
cloud_backup.save_token("")
set_setting("cloud_backup.enabled", False)
set_setting("cloud_backup.endpoint", "")

# 16. Auth hardening (lockout, policy, hash upgrade) — isolated auth file
print("\n16. Testing auth hardening...")
import utils.auth as auth
auth.AUTH_FILE = os.path.join(tmpdir, "auth_test.json")  # isolate from real users
mgr = auth.AuthManager()
check("admin" in mgr._users, "Default admin created")
check(mgr.needs_password_reset("admin"), "Default admin flagged must_change_password")
ok, _ = auth.validate_password_strength("weak")
check(not ok, "Weak password rejected")
ok, _ = auth.validate_password_strength("StrongPass99")
check(ok, "Strong password accepted")
ok, msg = mgr.login("admin", "wrongpass")
check(not ok, "Bad password rejected")
for _ in range(4):
    mgr.login("admin", "wrongpass")
ok, msg = mgr.login("admin", "admin123")
check(not ok and "locked" in msg.lower(), f"Account locked after 5 failures ({msg})")
mgr._failures.clear()  # simulate lockout expiry
ok, msg = mgr.login("admin", "admin123")
check(ok, "Correct password logs in after lockout cleared")
check(mgr._users["admin"]["password_hash"].startswith("pbkdf2:310000:"),
      "Password stored in current pbkdf2 format")
# legacy format still verifies
import hashlib as _hl
_salt = "abc123"
_legacy = _salt + ":" + _hl.pbkdf2_hmac("sha256", b"LegacyPass9", _salt.encode(), 100000).hex()
mgr._users["legacy"] = {"password_hash": _legacy, "role": "cashier", "display_name": "Legacy"}
ok, _ = mgr.login("legacy", "LegacyPass9")
check(ok, "Legacy hash format still verifies")
check(mgr._users["legacy"]["password_hash"].startswith("pbkdf2:310000:"),
      "Legacy hash auto-upgraded on login")
ok, msg = mgr.change_password("legacy", "LegacyPass9", "NewPass1234")
check(ok, "Password change clears flags" )
check(not mgr.needs_password_reset("legacy"), "must_change cleared after change")

# 17. Billing UPI + invoice HTML rendering
print("\n17. Testing billing UPI rendering...")
from utils.billing import _render_html
from utils.company import save_company, load_company
comp = load_company()
comp["upi_id"] = "shop@upi"
save_company(comp)
html_out = _render_html({
    "id": 5, "invoice_id": "#5", "receipt_no": "RCP-000005", "item_name": "TestItem",
    "quantity_sold": 1, "price": 100.0, "total": 100.0, "payment_status": "paid",
    "paid_amount": 100.0, "unpaid_amount": 0.0, "customer_name": "TestCustomer",
    "sale_date": "2026-09-24 10:00:00"})
check("shop@upi" in html_out, "UPI ID rendered on HTML invoice")
check("Tax Invoice" in html_out, "Invoice layout renders")
comp["upi_id"] = ""
save_company(comp)
html_out2 = _render_html({"id": 6, "invoice_id": "#6", "receipt_no": "RCP-000006",
    "item_name": "TestItem", "quantity_sold": 1, "price": 10.0, "total": 10.0,
    "payment_status": "paid", "paid_amount": 10.0, "unpaid_amount": 0.0,
    "customer_name": "X", "sale_date": "2026-09-24 10:00:00"})
check("Pay via UPI" not in html_out2, "No UPI line when UPI ID not set")

# 18. Customer portal (offline plumbing)
print("\n18. Testing customer portal plumbing...")
from utils import portal
pin = portal.generate_pin()
check(len(pin) == 6 and pin.isdigit(), "Auto PIN is 6 digits")
check(portal.portal_url().endswith("/portal"), f"Portal URL resolves ({portal.portal_url()})")
share = portal.build_share_text({"Name": "NotifyCust", "Phone": "+9779812345678"}, "1234")
check("NotifyCust" in share and "1234" in share and portal.portal_url() in share,
      "Share text includes URL + phone + PIN")
set_setting("portal.enabled", False)
check(portal.sync_enabled_customers() == (0, 0), "Portal sync no-ops when disabled")
ok, msg, _pin = portal.invite_customer({"Name": "NoPhone", "Phone": "", "Contact": ""})
if portal.is_licensed_for_portal():
    check(not ok and "phone" in msg.lower(), "Invite refuses customers without phone")
else:
    check(not ok and "license" in msg.lower(), "Invite requires an activated license")
set_setting("portal.enabled", True)

# 19. Feature behaviors: flag→field mapping, recipe auto-deduct, bank recon
print("\n19. Testing feature behaviors...")
from utils.settings_helper import (get_active_stock_field_defs,
                                   get_active_customer_field_defs)
set_setting("feature_flags.batch_tracking", False)
set_setting("feature_flags.table_orders", False)
set_setting("vertical", "general")
check(not any(k == "batch_no" for k, _ in get_active_stock_field_defs()),
      "Batch field hidden when flag off on general")
set_setting("feature_flags.batch_tracking", True)
set_setting("feature_flags.table_orders", True)
check(any(k == "batch_no" for k, _ in get_active_stock_field_defs()),
      "Batch field appears when flag enabled")
check(any(k == "table_no" for k, _ in get_active_customer_field_defs()),
      "Table_No customer field appears when table_orders enabled")
from utils.verticals import get_default_feature_flags
check(get_default_feature_flags("general")["audit_trail"] is True,
      "Audit trail stays on by default")

# recipe deduction (coffee + cookie combo consuming beans/milk)
ing_id = models.add_stock_item("Coffee Beans", "Ingredients", 10, 5, 10.0, 0, None)
models.add_stock_item("Combo Coffee", "Drinks", 20, 10, 30.0, 0, None,
                      extras={"Recipe_Ingredients": "Coffee Beans:2"})
set_setting("feature_flags.recipe_tracking", True)
combo_id = [i for i in models.get_stock_items() if i["Item_Name"] == "Combo Coffee"][0]["ID"]
models.record_sale(combo_id, 3, 30.0, payment_status="paid")
ing = models.get_stock_item(ing_id)
check(ing["Quantity"] == 4, f"Recipe deducted 3x2 beans (left {ing['Quantity']})")
set_setting("feature_flags.recipe_tracking", False)
models.record_sale(combo_id, 1, 30.0, payment_status="paid")
check(models.get_stock_item(ing_id)["Quantity"] == 4, "No deduction when recipe flag off")

# bank recon CSV parsing
from ui.pages.bank_recon import _load_bank_csv, _parse_date
csv_path = os.path.join(tmpdir, "bank.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    f.write("Date,Description,Debit\n2026-09-20,SUPPLIER PAYMENT,-1960.00\n")
bank_rows = _load_bank_csv(csv_path)
check(len(bank_rows) == 1 and bank_rows[0]["amount"] == -1960.0, "Bank CSV parsed")
check(_parse_date("20/09/2026") == "2026-09-20", "Date format d/m/Y parsed")

# Cleanup
os.remove(wb_path)

print(f"\n{'='*40}")
if errors:
    print(f"FAILED: {len(errors)} errors")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
