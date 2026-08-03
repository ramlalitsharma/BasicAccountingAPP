"""Vertical / industry registry. Each vertical has metadata + default feature flags."""
from typing import Dict, List, Optional

VERTICALS: Dict[str, Dict] = {
    "general": {
        "name": "General / Wholesale",
        "description": "Standard trading / wholesale business — items, suppliers, sales, GST/VAT invoices.",
        "icon": "📊",
        "default_features": {
            "tax_system": True,
            "barcode_scanner": False,
            "weight_pricing": False,
            "batch_tracking": False,
            "expiry_tracking": False,
            "schedule_tracking": False,
            "measurements": False,
            "supplier_returns": True,
            "whatsapp_invoice": False,
            "payment_gateway": False,
        },
        "extra_stock_fields": [],
        "extra_customer_fields": [],
        "primary_features": ["tax_system", "supplier_returns"],
    },
    "kirana": {
        "name": "Grocery / Kirana / Retail",
        "description": "Retail grocery/grocery-store billing with weight-based pricing and barcode scanning.",
        "icon": "🛒",
        "default_features": {
            "tax_system": True,
            "barcode_scanner": True,
            "weight_pricing": True,
            "batch_tracking": False,
            "expiry_tracking": True,
            "schedule_tracking": False,
            "measurements": False,
            "supplier_returns": True,
            "whatsapp_invoice": True,
            "payment_gateway": False,
        },
        "extra_stock_fields": ["barcode", "weight_grams"],
        "extra_customer_fields": [],
        "primary_features": ["barcode_scanner", "weight_pricing", "expiry_tracking", "whatsapp_invoice"],
    },
    "pharmacy": {
        "name": "Pharmacy / Medical",
        "description": "Pharmacy with batch tracking, expiry monitoring, and Schedule H/H1 drug tracking. FSSAI-related fields available.",
        "icon": "💊",
        "default_features": {
            "tax_system": True,
            "barcode_scanner": True,
            "weight_pricing": False,
            "batch_tracking": True,
            "expiry_tracking": True,
            "schedule_tracking": True,
            "measurements": False,
            "supplier_returns": True,
            "whatsapp_invoice": False,
            "payment_gateway": False,
        },
        "extra_stock_fields": ["barcode", "batch_no", "expiry_date", "drug_schedule", "fssai_no"],
        "extra_customer_fields": ["doctor_name", "prescription_no"],
        "primary_features": ["batch_tracking", "expiry_tracking", "schedule_tracking"],
    },
    "tailoring": {
        "name": "Tailoring / Boutique",
        "description": "Clothing tailoring / boutique workflow with customer measurements, order-delivery tracking.",
        "icon": "🧵",
        "default_features": {
            "tax_system": True,
            "barcode_scanner": False,
            "weight_pricing": False,
            "batch_tracking": False,
            "expiry_tracking": False,
            "schedule_tracking": False,
            "measurements": True,
            "supplier_returns": True,
            "whatsapp_invoice": True,
            "payment_gateway": False,
        },
        "extra_stock_fields": ["fabric", "color", "size"],
        "extra_customer_fields": ["measurements"],
        "primary_features": ["measurements", "whatsapp_invoice"],
    },
    "restaurant": {
        "name": "Restaurant / Cafe",
        "description": "Restaurant/cafe quick billing, table-based orders, KOT.",
        "icon": "🍽️",
        "default_features": {
            "tax_system": True,
            "barcode_scanner": False,
            "weight_pricing": False,
            "batch_tracking": False,
            "expiry_tracking": False,
            "schedule_tracking": False,
            "measurements": False,
            "supplier_returns": True,
            "whatsapp_invoice": True,
            "payment_gateway": False,
            "table_orders": True,
            "kot": True,
            "combo_items": False,
            "quick_billing": True,
            "recipe_tracking": False,
        },
        "extra_stock_fields": ["prep_time"],
        "extra_customer_fields": ["table_no"],
        "primary_features": ["whatsapp_invoice", "table_orders", "kot", "quick_billing"],
    },
    "coffee_shop": {
        "name": "Coffee Shop / Cafe",
        "description": "Coffee shop billing with table orders, KOT, combos (e.g. coffee+cookie), recipe/ingredient tracking, and quick checkout.",
        "icon": "☕",
        "default_features": {
            "tax_system": True,
            "barcode_scanner": False,
            "weight_pricing": False,
            "batch_tracking": False,
            "expiry_tracking": True,
            "schedule_tracking": False,
            "measurements": False,
            "supplier_returns": True,
            "whatsapp_invoice": True,
            "payment_gateway": False,
            "table_orders": True,
            "kot": True,
            "combo_items": True,
            "quick_billing": True,
            "recipe_tracking": True,
        },
        "extra_stock_fields": ["recipe_ingredients", "prep_time", "sizes"],
        "extra_customer_fields": ["table_no"],
        "primary_features": ["whatsapp_invoice", "table_orders", "kot", "combo_items",
                             "quick_billing", "recipe_tracking", "expiry_tracking"],
    },
}

ALL_FEATURES = [
    ("tax_system", "Tax System", "Apply and track GST (India) / VAT (Nepal) / None on sales and purchases"),
    ("barcode_scanner", "Barcode Scanner", "Add barcode field to stock items and scan during billing"),
    ("weight_pricing", "Weight-Based Pricing", "Sell items by grams/kilograms with weight-based calculation"),
    ("batch_tracking", "Batch Tracking", "Track batch/lot numbers per stock item"),
    ("expiry_tracking", "Expiry Tracking", "Track expiry dates per stock item; alerts for soon-to-expire"),
    ("schedule_tracking", "Drug Schedule Tracking", "Tag pharmacy items as Schedule H, H1, X — strict dispensing checks"),
    ("measurements", "Customer Measurements", "Capture & store tailoring measurements per customer"),
    ("supplier_returns", "Supplier Returns", "Track returns to suppliers (quantity + reason + amount)"),
    ("whatsapp_invoice", "WhatsApp Invoice", "Send invoice PDF/image directly to customers via WhatsApp"),
    ("payment_gateway", "Payment Gateway", "Online payment links via Razorpay/Stripe/etc."),
    ("audit_trail", "Audit Trail", "Detailed edit log per record: who/when changed what"),
    ("bank_recon", "Bank Reconciliation", "Match bank transactions with sales/purchase records"),
    ("table_orders", "Table Orders", "Assign and manage orders by table number"),
    ("kot", "Kitchen Order Ticket (KOT)", "Print/send separate KOTs to the kitchen for each order"),
    ("combo_items", "Combo / Meal Deals", "Bundle items as combos (e.g. coffee + cookie) with combo-level pricing"),
    ("quick_billing", "Quick Billing Mode", "Compact fast-checkout UI suited for cafes and counters"),
    ("recipe_tracking", "Recipe / Ingredient Tracking", "Track recipe ingredients and auto-deduct stock per item sold"),
]

COUNTRIES = ["India", "Nepal", "None"]

DEFAULT_COUNTRY_FOR_VERTICAL = {
    "general": "India",
    "kirana": "India",
    "pharmacy": "India",
    "tailoring": "India",
    "restaurant": "India",
    "coffee_shop": "India",
}


def get_vertical(key: str) -> Optional[Dict]:
    return VERTICALS.get(key)


def list_verticals() -> List[tuple]:
    return [(k, v["name"], v["icon"], v["description"]) for k, v in VERTICALS.items()]


def get_default_feature_flags(vertical_key: str) -> Dict[str, bool]:
    """Return feature flags default for a vertical (enabled for primary, disabled otherwise)."""
    v = VERTICALS.get(vertical_key)
    if not v:
        return {k: True for k, _ in ALL_FEATURES}
    primary = set(v.get("primary_features", []))
    defaults = {k: (k in primary) for k, _, _ in ALL_FEATURES}
    for k, val in v.get("default_features", {}).items():
        defaults[k] = val
    return defaults


def get_extra_stock_fields(vertical_key: str) -> List[str]:
    v = VERTICALS.get(vertical_key)
    return v.get("extra_stock_fields", []) if v else []


def get_extra_customer_fields(vertical_key: str) -> List[str]:
    v = VERTICALS.get(vertical_key)
    return v.get("extra_customer_fields", []) if v else []
