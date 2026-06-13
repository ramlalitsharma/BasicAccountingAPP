import json
import os
from config import CONFIG_DIR

COMPANY_FILE = os.path.join(CONFIG_DIR, "company.json")

DEFAULT_COMPANY = {
    "name": "",
    "address": "",
    "city": "",
    "state": "",
    "pincode": "",
    "phone": "",
    "email": "",
    "gstin": "",
    "pan": "",
    "invoice_prefix": "INV",
    "invoice_note": "Thank you for your business!",
}


def load_company():
    if not os.path.exists(COMPANY_FILE):
        save_company(DEFAULT_COMPANY)
        return dict(DEFAULT_COMPANY)
    try:
        with open(COMPANY_FILE, "r") as f:
            data = json.load(f)
        for k, v in DEFAULT_COMPANY.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(DEFAULT_COMPANY)


def save_company(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(COMPANY_FILE, "w") as f:
        json.dump(data, f, indent=2)
