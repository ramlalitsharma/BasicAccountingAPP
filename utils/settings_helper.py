"""Convenience helpers that wrap config.get_setting with defaults for nested keys."""
import os
import json
from pathlib import Path
from config import (
    CONFIG_DIR, SETTINGS_FILE, _settings, _save_settings,
    get_setting, set_setting,
)
from utils.verticals import VERTICALS, ALL_FEATURES


_DEFAULTS = {
    "country": "India",
    "vertical": "general",
    "feature_flags": {fid: False for fid, _, _ in ALL_FEATURES},
    "tax": {
        "default_rate_percent": 0,
        "have_gstin": True,
        "have_pan": False,
        "india": {
            "rates": [0, 5, 12, 18, 28],
            "default_rate": 18,
            "include_cess": False,
            "show_gstin_on_invoice": True,
            "cess_percent": 0,
        },
        "nepal": {
            "rates": [0, 13],
            "default_rate": 13,
            "show_pan_on_invoice": True,
        },
    },
    "business": {
        "invoice_no_prefix": "INV",
        "low_stock_threshold_default": 5,
        "auto_print_receipt": False,
        "show_tax_breakdown_on_receipt": True,
        "decimal_places": 2,
    },
    "data_dir": str(CONFIG_DIR.parent),
    "theme": "Light",
    "currency_symbol": "\u20B9",
    "last_file": "",
    "log_level": "INFO",
    "first_run": True,
}


def get_default(key, default=None):
    keys = key.split(".")
    cur = dict(_DEFAULTS)
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def get_effective(key, default=None):
    """Return the setting value if set, otherwise the precomputed default."""
    val = get_setting(key, None)
    if val is not None:
        return val
    return get_default(key, default)


def is_feature_enabled(feature_id: str) -> bool:
    """Check if a feature flag is enabled in current vertical setup."""
    return bool(get_effective(f"feature_flags.{feature_id}", False))


def _current_username():
    try:
        from utils.auth import auth_manager
        return auth_manager.get_current_user() or ""
    except Exception:
        return ""


def get_user_setting(key, default=None):
    """Per-user preference (``user_prefs.<username>.<key>``); falls back to the
    global setting key, then ``default``. Lets every login have its own
    start page / dashboard layout / theme."""
    user = _current_username()
    if user:
        val = get_setting(f"user_prefs.{user}.{key}", None)
        if val is not None:
            return val
    return get_setting(key, default)


def set_user_setting(key, value):
    """Store a preference for the currently logged-in user (or globally when
    no user session exists)."""
    user = _current_username()
    if user:
        set_setting(f"user_prefs.{user}.{key}", value)
    else:
        set_setting(key, value)


def get_current_vertical() -> str:
    return get_effective("vertical", "general")


def get_current_country() -> str:
    return get_effective("country", "India")


def get_default_feature_flags():
    """Pre-fill flags based on the configured vertical."""
    from utils.verticals import get_default_feature_flags
    v = get_current_vertical()
    return get_default_feature_flags(v)


def update_features_from_vertical(vertical_key: str):
    """Reset feature flags to defaults matching a vertical (call after vertical change)."""
    from utils.verticals import get_default_feature_flags
    defaults = get_default_feature_flags(vertical_key)
    fs = _settings.get("feature_flags", {}) or {}
    for k, v in defaults.items():
        fs[k] = v
    _settings["feature_flags"] = fs
    _settings["vertical"] = vertical_key
    _save_settings(_settings)


def ensure_settings_initialized():
    """Make sure settings.json has all required sections, defaulting as needed."""
    from utils.verticals import get_default_feature_flags
    changed = False
    if "feature_flags" not in _settings or not isinstance(_settings.get("feature_flags"), dict):
        _settings["feature_flags"] = get_default_feature_flags(
            _settings.get("vertical", "general"))
        changed = True
    if "country" not in _settings:
        _settings["country"] = "India"
        changed = True
    if "vertical" not in _settings:
        _settings["vertical"] = "general"
        changed = True
    if "tax" not in _settings or not isinstance(_settings.get("tax"), dict):
        _settings["tax"] = dict(_DEFAULTS["tax"])
        changed = True
    if "business" not in _settings or not isinstance(_settings.get("business"), dict):
        _settings["business"] = dict(_DEFAULTS["business"])
        changed = True
    if "first_run" not in _settings:
        _settings["first_run"] = True
        changed = True

    # Ensure every feature flag in current vertical set is present
    fs = _settings.get("feature_flags", {})
    v = _settings.get("vertical", "general")
    for fid, _, _ in ALL_FEATURES:
        fs.setdefault(fid, False)
    _settings["feature_flags"] = fs

    if changed:
        _save_settings(_settings)


# ── vertical/flag-driven extra form fields ────────────────────────────────
# An extra field shows up when the active vertical lists it OR its mapped
# feature flag is enabled manually — both routes now configure the forms.
_FIELD_FEATURE = {
    "barcode": "barcode_scanner",
    "weight_grams": "weight_pricing",
    "batch_no": "batch_tracking",
    "expiry_date": "expiry_tracking",
    "drug_schedule": "schedule_tracking",
    "fabric": "measurements",
    "color": "measurements",
    "size": "measurements",
    "prep_time": "recipe_tracking",
    "recipe_ingredients": "recipe_tracking",
    "sizes": "recipe_tracking",
    "measurements": "measurements",
    "doctor_name": "schedule_tracking",
    "prescription_no": "schedule_tracking",
    "table_no": "table_orders",
}
_STOCK_EXTRA_KEYS = {"barcode", "weight_grams", "batch_no", "expiry_date",
                     "drug_schedule", "fssai_no", "fabric", "color", "size",
                     "prep_time", "recipe_ingredients", "sizes"}
_CUSTOMER_EXTRA_KEYS = {"doctor_name", "prescription_no", "measurements", "table_no"}


def get_active_stock_field_defs(vertical: str = None):
    """Ordered ``(field_key, def)`` for the stock form, honoring both the
    vertical's extras and individually-enabled feature flags."""
    from utils.verticals import EXTRA_FIELD_DEFS, get_extra_stock_fields
    keys = list(get_extra_stock_fields(vertical or get_current_vertical()))
    for fkey, flag in _FIELD_FEATURE.items():
        if fkey in _STOCK_EXTRA_KEYS and flag and is_feature_enabled(flag) and fkey not in keys:
            keys.append(fkey)
    return [(k, EXTRA_FIELD_DEFS[k]) for k in keys if k in EXTRA_FIELD_DEFS]


def get_active_customer_field_defs(vertical: str = None):
    """Same idea for the customer form."""
    from utils.verticals import EXTRA_FIELD_DEFS, get_extra_customer_fields
    keys = list(get_extra_customer_fields(vertical or get_current_vertical()))
    for fkey, flag in _FIELD_FEATURE.items():
        if fkey in _CUSTOMER_EXTRA_KEYS and flag and is_feature_enabled(flag) and fkey not in keys:
            keys.append(fkey)
    return [(k, EXTRA_FIELD_DEFS[k]) for k in keys if k in EXTRA_FIELD_DEFS]


def apply_first_run_defaults():
    """For the very first run, set sensible defaults based on country/vertical."""
    from utils.verticals import get_default_feature_flags, DEFAULT_COUNTRY_FOR_VERTICAL, VERTICALS
    country = _settings.get("country", "India")
    vertical = _settings.get("vertical", "general")
    if vertical not in VERTICALS:
        vertical = "general"
        _settings["vertical"] = vertical
    if country not in ("India", "Nepal", "None"):
        country = "India"
        _settings["country"] = country
    if "currency_symbol" not in _settings or not _settings.get("currency_symbol"):
        if country == "India":
            _settings["currency_symbol"] = "\u20B9"
        elif country == "Nepal":
            _settings["currency_symbol"] = "Rs."
        else:
            _settings["currency_symbol"] = "$"

    defaults = get_default_feature_flags(vertical)
    if not _settings.get("feature_flags") or not any(_settings.get("feature_flags", {}).values()):
        _settings["feature_flags"] = defaults
    _settings["first_run"] = False
    _save_settings(_settings)
