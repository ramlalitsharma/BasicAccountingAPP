import sys, os, tempfile
os.environ["DISPLAY"] = ""

sys.path.insert(0, os.path.dirname(__file__))

from database import models
from config import get_color, set_setting, get_color, _LIGHT_COLORS, _DARK_COLORS

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
check(completed["Status"] == "completed", "Preorder marked completed")
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
