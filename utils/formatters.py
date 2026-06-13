def format_currency(amount):
    return f"₹{amount:,.2f}"


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
