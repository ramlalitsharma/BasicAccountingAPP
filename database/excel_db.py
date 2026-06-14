import openpyxl
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import os
import shutil
from datetime import datetime
from config import DATA_DIR, BACKUP_DIR, set_setting
from utils.update_checker import get_update_status


_active_file = None
SHEET_VERSION = "2.0"


def _check_write_lock():
    status = get_update_status()
    if status.get("force_update", False):
        raise PermissionError(
            f"Update Required: v{status['latest_version']} available.\n"
            "Please update to the latest version to continue editing."
        )

SHEETS = {
    "Suppliers": ["ID", "Name", "Contact", "Address", "Created_At"],
    "Stock": ["ID", "Item_Name", "Category", "Quantity", "Min_Quantity",
              "Purchase_Price", "Selling_Price", "Supplier_ID", "Created_At"],
    "Sales": ["ID", "Stock_ID", "Quantity_Sold", "Price", "Total", "Sale_Date"],
    "StockLog": ["ID", "Stock_ID", "Change_Type", "Qty_Change", "Old_Qty",
                 "New_Qty", "Note", "Created_At"],
    "Customers": ["ID", "Name", "Contact", "Address", "Created_At"],
    "Purchases": ["ID", "Stock_ID", "Supplier_ID", "Quantity", "Cost_Price",
                  "Total_Cost", "Purchase_Date"],
}

INVOICE_PREFIX = "INV"


def set_active_file(filepath):
    global _active_file
    _active_file = filepath
    try:
        set_setting("last_file", filepath)
    except Exception:
        pass


def get_active_file():
    return _active_file


def _backup_file(filepath):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.basename(filepath)
    backup_path = os.path.join(BACKUP_DIR, f"pre_{ts}_{base}")
    try:
        shutil.copy2(filepath, backup_path)
    except Exception:
        pass


def _ensure_sheets(wb):
    changed = False
    for name, headers in SHEETS.items():
        if name not in wb.sheetnames:
            ws = wb.create_sheet(name)
            ws.append(headers)
            changed = True
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]
        changed = True
    return changed


def _validate_sheets(wb):
    issues = []
    for name, headers in SHEETS.items():
        if name in wb.sheetnames:
            ws = wb[name]
            actual = [cell.value for cell in ws[1]] if ws.max_row > 0 else []
            if not actual:
                ws.append(headers)
                issues.append(f"Added missing headers to {name}")
            else:
                for expected in headers:
                    if expected not in actual:
                        missing_idx = headers.index(expected)
                        col_letter = get_column_letter(missing_idx + 1)
                        ws[f"{col_letter}1"] = expected
                        issues.append(f"Fixed missing column '{expected}' in {name}")
    return issues


def create_new_workbook(filepath=None):
    if filepath is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(DATA_DIR, f"accounts_{timestamp}.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = "Suppliers"
    ws.append(SHEETS["Suppliers"])
    ws = wb.create_sheet("Stock")
    ws.append(SHEETS["Stock"])
    ws = wb.create_sheet("Sales")
    ws.append(SHEETS["Sales"])
    ws = wb.create_sheet("StockLog")
    ws.append(SHEETS["StockLog"])
    ws = wb.create_sheet("Customers")
    ws.append(SHEETS["Customers"])
    ws = wb.create_sheet("Purchases")
    ws.append(SHEETS["Purchases"])
    wb.save(filepath)
    set_active_file(filepath)
    return filepath


def open_workbook(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found:\n{filepath}")
    if not filepath.endswith(".xlsx"):
        raise ValueError("Please select a valid .xlsx file")
    _backup_file(filepath)
    wb = openpyxl.load_workbook(filepath)
    changed = _ensure_sheets(wb)
    issues = _validate_sheets(wb)
    if changed or issues:
        wb.save(filepath)
    set_active_file(filepath)
    return filepath


def _get_wb():
    if not _active_file or not os.path.exists(_active_file):
        raise FileNotFoundError("No active workbook. Create or open one first.")
    return openpyxl.load_workbook(_active_file)


def _save_and_close(wb):
    wb.save(_active_file)
    wb.close()


def _sheet_to_dicts(ws):
    headers = [cell.value for cell in ws[1]]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if any(v is not None for v in row):
            rows.append(dict(zip(headers, row)))
    return rows


def _dicts_to_sheet(ws, dicts, headers):
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.value = None
    ws.delete_rows(2, ws.max_row - 1)
    for d in dicts:
        ws.append([d.get(h, "") for h in headers])


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")



def _next_id(ws):
    max_id = 0
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
        if row[0] is not None:
            try:
                max_id = max(max_id, int(row[0]))
            except (ValueError, TypeError):
                pass
    return max_id + 1


# ---- SUPPLIERS ----

def add_supplier(name, contact="", address=""):
    _check_write_lock()
    wb = _get_wb()
    ws = wb["Suppliers"]
    sid = _next_id(ws)
    ws.append([sid, name, contact, address, _now()])
    _save_and_close(wb)
    return sid


def get_suppliers(search=""):
    wb = _get_wb()
    data = _sheet_to_dicts(wb["Suppliers"])
    wb.close()
    if search:
        search = search.lower()
        data = [r for r in data if search in str(r.get("Name", "")).lower()]
    return data


def get_supplier(supplier_id):
    wb = _get_wb()
    for r in _sheet_to_dicts(wb["Suppliers"]):
        if r.get("ID") == supplier_id:
            wb.close()
            return r
    wb.close()
    return None


def update_supplier(supplier_id, name, contact, address):
    _check_write_lock()
    wb = _get_wb()
    ws = wb["Suppliers"]
    data = _sheet_to_dicts(ws)
    for r in data:
        if r.get("ID") == supplier_id:
            r["Name"] = name
            r["Contact"] = contact
            r["Address"] = address
            break
    _dicts_to_sheet(ws, data, SHEETS["Suppliers"])
    _save_and_close(wb)


def delete_supplier(supplier_id):
    _check_write_lock()
    wb = _get_wb()
    ws = wb["Suppliers"]
    data = _sheet_to_dicts(ws)
    data = [r for r in data if r.get("ID") != supplier_id]
    _dicts_to_sheet(ws, data, SHEETS["Suppliers"])
    _save_and_close(wb)


# ---- STOCK ----

def add_stock_item(item_name, category, quantity, purchase_price, selling_price,
                   min_quantity=5, supplier_id=None):
    _check_write_lock()
    wb = _get_wb()
    ws = wb["Stock"]
    sid = _next_id(ws)
    ws.append([sid, item_name, category, quantity, min_quantity,
               purchase_price, selling_price, supplier_id, _now()])
    _save_and_close(wb)
    return sid


def get_stock_items(search="", category=""):
    wb = _get_wb()
    data = _sheet_to_dicts(wb["Stock"])
    wb.close()
    # Join supplier name
    suppliers = {s["ID"]: s["Name"] for s in get_suppliers()}
    for r in data:
        r["supplier_name"] = suppliers.get(r.get("Supplier_ID"), "")
    if search:
        search = search.lower()
        data = [r for r in data if search in str(r.get("Item_Name", "")).lower()]
    if category and category != "All":
        data = [r for r in data if r.get("Category") == category]
    return data


def get_stock_item(stock_id):
    wb = _get_wb()
    for r in _sheet_to_dicts(wb["Stock"]):
        if r.get("ID") == stock_id:
            suppliers = {s["ID"]: s["Name"] for s in get_suppliers()}
            r["supplier_name"] = suppliers.get(r.get("Supplier_ID"), "")
            wb.close()
            return r
    wb.close()
    return None


def update_stock_item(stock_id, item_name, category, quantity, min_quantity,
                      purchase_price, selling_price, supplier_id=None):
    _check_write_lock()
    wb = _get_wb()
    ws = wb["Stock"]
    data = _sheet_to_dicts(ws)
    for r in data:
        if r.get("ID") == stock_id:
            old_qty = r.get("Quantity", 0)
            r["Item_Name"] = item_name
            r["Category"] = category
            r["Quantity"] = quantity
            r["Min_Quantity"] = min_quantity
            r["Purchase_Price"] = purchase_price
            r["Selling_Price"] = selling_price
            r["Supplier_ID"] = supplier_id
            if old_qty != quantity:
                diff = quantity - old_qty
                _log_stock_change_internal(wb, stock_id, "adjustment", diff,
                                           old_qty, f"Manual: {old_qty} -> {quantity}")
            break
    _dicts_to_sheet(ws, data, SHEETS["Stock"])
    _save_and_close(wb)


def delete_stock_item(stock_id):
    _check_write_lock()
    wb = _get_wb()
    ws = wb["Stock"]
    data = _sheet_to_dicts(ws)
    data = [r for r in data if r.get("ID") != stock_id]
    _dicts_to_sheet(ws, data, SHEETS["Stock"])
    _save_and_close(wb)


def get_low_stock_items():
    wb = _get_wb()
    data = _sheet_to_dicts(wb["Stock"])
    wb.close()
    return [r for r in data if r.get("Quantity", 0) <= r.get("Min_Quantity", 0)]


def get_categories():
    wb = _get_wb()
    data = _sheet_to_dicts(wb["Stock"])
    wb.close()
    cats = set()
    for r in data:
        c = r.get("Category", "")
        if c:
            cats.add(c)
    return sorted(cats)


# ---- SALES ----

def record_sale(stock_id, quantity_sold, price):
    _check_write_lock()
    wb = _get_wb()
    stock_ws = wb["Stock"]
    stock_data = _sheet_to_dicts(stock_ws)
    item = None
    for r in stock_data:
        if r.get("ID") == stock_id:
            item = r
            break
    if not item:
        wb.close()
        raise ValueError("Stock item not found")
    if item["Quantity"] < quantity_sold:
        wb.close()
        raise ValueError(f'Not enough stock. Available: {item["Quantity"]}')
    total = round(quantity_sold * price, 2)
    sales_ws = wb["Sales"]
    sid = _next_id(sales_ws)
    sales_ws.append([sid, stock_id, quantity_sold, price, total, _now()])
    old_qty = item["Quantity"]
    item["Quantity"] = old_qty - quantity_sold
    _dicts_to_sheet(stock_ws, stock_data, SHEETS["Stock"])
    _log_stock_change_internal(wb, stock_id, "sale", -quantity_sold,
                               old_qty, f"Sold {quantity_sold} units")
    _save_and_close(wb)


def return_sale(sale_id):
    _check_write_lock()
    wb = _get_wb()
    sales_ws = wb["Sales"]
    sales_data = _sheet_to_dicts(sales_ws)
    sale = None
    for r in sales_data:
        if r.get("ID") == sale_id:
            sale = r
            break
    if not sale:
        wb.close()
        raise ValueError("Sale not found")
    stock_ws = wb["Stock"]
    stock_data = _sheet_to_dicts(stock_ws)
    for r in stock_data:
        if r.get("ID") == sale["Stock_ID"]:
            old_qty = r["Quantity"]
            r["Quantity"] = old_qty + sale["Quantity_Sold"]
            _log_stock_change_internal(wb, sale["Stock_ID"], "return",
                                       sale["Quantity_Sold"], old_qty,
                                       f"Return of sale #{sale_id}")
            break
    sales_data = [r for r in sales_data if r.get("ID") != sale_id]
    _dicts_to_sheet(sales_ws, sales_data, SHEETS["Sales"])
    _dicts_to_sheet(stock_ws, stock_data, SHEETS["Stock"])
    _save_and_close(wb)


def delete_sale(sale_id):
    _check_write_lock()
    wb = _get_wb()
    ws = wb["Sales"]
    data = _sheet_to_dicts(ws)
    data = [r for r in data if r.get("ID") != sale_id]
    _dicts_to_sheet(ws, data, SHEETS["Sales"])
    _save_and_close(wb)


def get_sales(search="", from_date="", to_date=""):
    wb = _get_wb()
    data = _sheet_to_dicts(wb["Sales"])
    wb.close()
    stock = {r["ID"]: r for r in get_stock_items()}
    result = []
    for r in data:
        item = stock.get(r.get("Stock_ID"), {})
        r["item_name"] = item.get("Item_Name", "")
        r["category"] = item.get("Category", "")
        if search and search.lower() not in r["item_name"].lower():
            continue
        sd = r.get("Sale_Date", "")
        if from_date and sd and sd[:10] < from_date:
            continue
        if to_date and sd and sd[:10] > to_date:
            continue
        result.append(r)
    result.sort(key=lambda x: x.get("Sale_Date", ""), reverse=True)
    return result


def get_daily_sales(date=None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    sales = get_sales()
    day_sales = [s for s in sales if s.get("Sale_Date", "")[:10] == date]
    return {
        "count": len(day_sales),
        "total": sum(s.get("Total", 0) or 0 for s in day_sales),
    }


def get_monthly_report(year, month):
    wb = _get_wb()
    sales = _sheet_to_dicts(wb["Sales"])
    stock = {r["ID"]: r for r in _sheet_to_dicts(wb["Stock"])}
    wb.close()
    ym = f"{year}-{month:02d}"
    grouped = {}
    for s in sales:
        sd = str(s.get("Sale_Date", ""))
        if not sd.startswith(ym):
            continue
        item = stock.get(s.get("Stock_ID"), {})
        name = item.get("Item_Name", "Unknown")
        if name not in grouped:
            grouped[name] = {
                "item_name": name,
                "category": item.get("Category", ""),
                "qty_sold": 0,
                "price": s.get("Price", 0),
                "total_revenue": 0,
                "purchase_price": item.get("Purchase_Price", 0),
                "profit": 0,
            }
        qty = s.get("Quantity_Sold", 0) or 0
        price = s.get("Price", 0) or 0
        grouped[name]["qty_sold"] += qty
        grouped[name]["total_revenue"] += s.get("Total", 0) or 0
        grouped[name]["price"] = price
    result = []
    for name, g in grouped.items():
        cost = g["qty_sold"] * g["purchase_price"]
        g["profit"] = g["total_revenue"] - cost
        result.append(g)
    result.sort(key=lambda x: x["profit"], reverse=True)
    return result


def get_yearly_report(year):
    sales = get_sales()
    monthly = {}
    for s in sales:
        sd = str(s.get("Sale_Date", ""))
        if not sd.startswith(str(year)):
            continue
        m = sd[5:7]
        if m not in monthly:
            monthly[m] = {"month": m, "sale_count": 0, "total_qty": 0,
                          "total_revenue": 0, "total_profit": 0}
        monthly[m]["sale_count"] += 1
        monthly[m]["total_qty"] += s.get("Quantity_Sold", 0) or 0
        monthly[m]["total_revenue"] += s.get("Total", 0) or 0
    # Get profit from stock costs
    stock = {r["ID"]: r for r in get_stock_items()}
    for s in sales:
        sd = str(s.get("Sale_Date", ""))
        if not sd.startswith(str(year)):
            continue
        m = sd[5:7]
        item = stock.get(s.get("Stock_ID"), {})
        cost = (s.get("Quantity_Sold", 0) or 0) * (item.get("Purchase_Price", 0) or 0)
        monthly[m]["total_profit"] = (monthly[m].get("total_profit", 0) or 0) + \
                                     (s.get("Total", 0) or 0) - cost
    result = [monthly[m] for m in sorted(monthly.keys())]
    return result


def get_dashboard_stats():
    stock = get_stock_items()
    total_items = len(stock)
    low_stock = len([s for s in stock if s.get("Quantity", 0) <= s.get("Min_Quantity", 0)])
    stock_value = sum((s.get("Quantity", 0) or 0) * (s.get("Purchase_Price", 0) or 0) for s in stock)
    ds = get_daily_sales()
    return {
        "total_items": total_items,
        "low_stock": low_stock,
        "stock_value": round(stock_value, 2),
        "sales_today": round(ds.get("total", 0), 2),
    }


# ---- STOCK LOG ----

def _log_stock_change_internal(wb, stock_id, change_type, qty_change, old_qty, note=""):
    ws = wb["StockLog"]
    lid = _next_id(ws)
    new_qty = old_qty + qty_change
    ws.append([lid, stock_id, change_type, qty_change, old_qty, new_qty, note, _now()])


def get_stock_log(stock_id=None, limit=100):
    wb = _get_wb()
    data = _sheet_to_dicts(wb["StockLog"])
    wb.close()
    if stock_id:
        data = [r for r in data if r.get("Stock_ID") == stock_id]
    data.sort(key=lambda x: x.get("Created_At", ""), reverse=True)
    return data[:limit]


def get_year_months():
    sales = get_sales()
    pairs = set()
    for s in sales:
        sd = str(s.get("Sale_Date", ""))
        if len(sd) >= 7:
            pairs.add((sd[:4], sd[5:7]))
    return sorted(pairs, reverse=True)


# ---- CUSTOMERS ----

def add_customer(name, contact="", address=""):
    _check_write_lock()
    wb = _get_wb()
    ws = wb["Customers"]
    cid = _next_id(ws)
    ws.append([cid, name, contact, address, _now()])
    _save_and_close(wb)
    return cid


def get_customers(search=""):
    wb = _get_wb()
    data = _sheet_to_dicts(wb["Customers"])
    wb.close()
    if search:
        search = search.lower()
        data = [r for r in data if search in str(r.get("Name", "")).lower()]
    return data


def get_customer(customer_id):
    wb = _get_wb()
    for r in _sheet_to_dicts(wb["Customers"]):
        if r.get("ID") == customer_id:
            wb.close()
            return r
    wb.close()
    return None


def update_customer(customer_id, name, contact, address):
    _check_write_lock()
    wb = _get_wb()
    ws = wb["Customers"]
    data = _sheet_to_dicts(ws)
    for r in data:
        if r.get("ID") == customer_id:
            r["Name"] = name
            r["Contact"] = contact
            r["Address"] = address
            break
    _dicts_to_sheet(ws, data, SHEETS["Customers"])
    _save_and_close(wb)


def delete_customer(customer_id):
    _check_write_lock()
    wb = _get_wb()
    ws = wb["Customers"]
    data = _sheet_to_dicts(ws)
    data = [r for r in data if r.get("ID") != customer_id]
    _dicts_to_sheet(ws, data, SHEETS["Customers"])
    _save_and_close(wb)


# ---- PURCHASES (from suppliers) ----

def record_purchase(stock_id, supplier_id, quantity, cost_price):
    _check_write_lock()
    wb = _get_wb()
    stock_ws = wb["Stock"]
    stock_data = _sheet_to_dicts(stock_ws)
    item = None
    for r in stock_data:
        if r.get("ID") == stock_id:
            item = r
            break
    if not item:
        wb.close()
        raise ValueError("Stock item not found")
    total_cost = round(quantity * cost_price, 2)
    old_qty = item["Quantity"]
    item["Quantity"] = old_qty + quantity
    item["Purchase_Price"] = cost_price  # update avg cost
    _dicts_to_sheet(stock_ws, stock_data, SHEETS["Stock"])
    pur_ws = wb["Purchases"]
    pid = _next_id(pur_ws)
    pur_ws.append([pid, stock_id, supplier_id, quantity, cost_price, total_cost, _now()])
    _log_stock_change_internal(wb, stock_id, "purchase", quantity,
                               old_qty, f"Purchased {quantity} units at ₹{cost_price}")
    _save_and_close(wb)
    return pid


def get_purchases(search=""):
    wb = _get_wb()
    data = _sheet_to_dicts(wb["Purchases"])
    wb.close()
    stock = {r["ID"]: r for r in get_stock_items()}
    suppliers = {s["ID"]: s["Name"] for s in get_suppliers()}
    result = []
    for r in data:
        r["item_name"] = stock.get(r.get("Stock_ID"), {}).get("Item_Name", "")
        r["supplier_name"] = suppliers.get(r.get("Supplier_ID"), "")
        if search and search.lower() not in r["item_name"].lower():
            continue
        result.append(r)
    return result


# ---- INVOICE FORMAT ----

def format_invoice_id(sale_id):
    try:
        from utils.company import load_company
        prefix = load_company().get("invoice_prefix", "INV")
    except Exception:
        prefix = "INV"
    return f"{prefix}-{sale_id:05d}"
