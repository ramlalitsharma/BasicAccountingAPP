def validate_required(value, field_name):
    if not value or not str(value).strip():
        raise ValueError(f"{field_name} is required")


def validate_positive_int(value, field_name):
    try:
        v = int(value)
        if v < 0:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a positive number")


def validate_positive_float(value, field_name):
    try:
        v = float(value)
        if v < 0:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a valid positive number")


def validate_sale(stock_id, quantity_sold, price):
    validate_required(stock_id, "Stock item")
    validate_positive_int(quantity_sold, "Quantity sold")
    validate_positive_float(price, "Price")
