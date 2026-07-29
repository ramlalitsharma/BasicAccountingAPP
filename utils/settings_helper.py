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
