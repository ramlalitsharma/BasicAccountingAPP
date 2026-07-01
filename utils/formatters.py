def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_currency(amount):
    try:
        return f"₹{float(amount):,.2f}"
    except (ValueError, TypeError):
        return f"₹0.00"


def format_date(date_str):
    if not date_str:
        return ""
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y")
    except ValueError:
        return date_str


def format_datetime(date_str):
    if not date_str:
        return ""
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y %I:%M %p")
    except ValueError:
        return date_str
