import json
import os
import hashlib
import hmac
import logging
from datetime import datetime

from config import CONFIG_DIR

logger = logging.getLogger(__name__)

LICENSE_FILE = os.path.join(CONFIG_DIR, "license.json")

_ENCODED_KEY_HEX = "e4c6c6cad0cbd1cccbc2f5d7ca88f5d7cac1d0c6d1cccacb88ede8e4e6889795979388d397"

TIERS = {
    "free": {
        "name": "Basic",
        "max_stock_items": 100,
        "max_customers": 50,
        "max_suppliers": 30,
        "has_export": True,
        "has_charts": True,
        "has_reports": True,
        "has_preorders": True,
        "has_extra_income": True,
        "has_invoice_customization": False,
        "has_cloud_backup": False,
        "has_email_invoicing": False,
        "has_advanced_reports": False,
        "has_multi_company": False,
    },
    "pro": {
        "name": "Professional",
        "max_stock_items": 99999,
        "max_customers": 99999,
        "max_suppliers": 99999,
        "has_export": True,
        "has_charts": True,
        "has_reports": True,
        "has_preorders": True,
        "has_extra_income": True,
        "has_invoice_customization": True,
        "has_cloud_backup": True,
        "has_email_invoicing": True,
        "has_advanced_reports": True,
        "has_multi_company": False,
    },
    "enterprise": {
        "name": "Enterprise",
        "max_stock_items": 999999,
        "max_customers": 999999,
        "max_suppliers": 999999,
        "has_export": True,
        "has_charts": True,
        "has_reports": True,
        "has_preorders": True,
        "has_extra_income": True,
        "has_invoice_customization": True,
        "has_cloud_backup": True,
        "has_email_invoicing": True,
        "has_advanced_reports": True,
        "has_multi_company": True,
    }
}

_TRIAL_DAYS = 30


class LicenseManager:
    def __init__(self):
        self._key = bytes(b ^ 0xA5 for b in bytes.fromhex(_ENCODED_KEY_HEX))
        self._license = self._load()
        if self._license.get("tier") == "free" and self._license.get("first_run") is None:
            self._license["first_run"] = datetime.now().strftime("%Y-%m-%d")
            self._save()

    def _sign(self, data_dict):
        payload = json.dumps(data_dict, sort_keys=True, separators=(',', ':'))
        return hmac.new(self._key, payload.encode(), hashlib.sha256).hexdigest()

    def _verify(self, data_dict, signature):
        return hmac.compare_digest(self._sign(data_dict), signature)

    def _load(self):
        defaults = {"tier": "free", "licensed_to": "", "key": "", "expires": "", "first_run": None}
        try:
            if os.path.exists(LICENSE_FILE):
                with open(LICENSE_FILE, "r") as f:
                    data = json.load(f)
                signature = data.pop("signature", None)
                if signature is None or not self._verify(data, signature):
                    logger.warning("License tampered or invalid, resetting to free")
                    return dict(defaults)
                for k, v in defaults.items():
                    data.setdefault(k, v)
                return data
        except (OSError, json.JSONDecodeError, ValueError):
            logger.exception("Failed to load license")
        return dict(defaults)

    def _save(self):
        data = {k: v for k, v in self._license.items() if k != "signature"}
        data["signature"] = self._sign(data)
        try:
            os.makedirs(os.path.dirname(LICENSE_FILE), exist_ok=True)
            with open(LICENSE_FILE, "w") as f:
                json.dump(data, f, indent=2)
            self._license = data
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to save license")

    def get_tier(self):
        return self._license.get("tier", "free")

    def get_tier_name(self):
        return TIERS[self.get_tier()]["name"]

    def is_pro(self):
        return self.get_tier() in ("pro", "enterprise")

    def is_enterprise(self):
        return self.get_tier() == "enterprise"

    def has_feature(self, feature):
        return TIERS[self.get_tier()].get(feature, False)

    def check_feature(self, feature_name):
        return TIERS[self.get_tier()].get(feature_name, False)

    def check_limit(self, resource_name, current_count):
        limit = TIERS[self.get_tier()].get(resource_name)
        if limit is None:
            return True
        return current_count < limit

    def get_licensed_to(self):
        return self._license.get("licensed_to", "")

    def is_expired(self):
        expires = self._license.get("expires", "")
        if not expires:
            return False
        try:
            return datetime.now() > datetime.strptime(expires, "%Y-%m-%d")
        except ValueError:
            return True

    def get_trial_days_remaining(self):
        if self.get_tier() != "free":
            return 0
        first_run = self._license.get("first_run")
        if not first_run:
            return _TRIAL_DAYS
        try:
            start = datetime.strptime(first_run, "%Y-%m-%d").date()
            remaining = _TRIAL_DAYS - (datetime.now().date() - start).days
            return max(0, remaining)
        except ValueError:
            return 0

    def is_trial_expired(self):
        if self.get_tier() != "free":
            return False
        return self.get_trial_days_remaining() <= 0

    def activate(self, license_key, licensed_to, tier="pro"):
        try:
            parts = license_key.strip().split("-")
            if len(parts) != 5:
                return False, "Invalid license key format (XXXXX-XXXXX-XXXXX-XXXXX-XXXXX)"

            data = f"{licensed_to}|{tier}|2027-12-31"
            expected = hmac.new(self._key, data.encode(), hashlib.sha256).hexdigest()[:25]
            expected_key = "-".join([expected[i:i+5] for i in range(0, 25, 5)])

            if license_key.strip() != expected_key:
                return False, "Invalid license key. Please verify and try again."

            self._license["tier"] = tier
            self._license["licensed_to"] = licensed_to
            self._license["key"] = license_key
            self._license["expires"] = "2027-12-31"
            self._license["first_run"] = None
            self._save()
            return True, "License activated successfully!"
        except (ValueError, KeyError, OSError):
            logger.exception("License activation failed")
            return False, "Activation error: unexpected failure"

    def deactivate(self):
        self._license = {"tier": "free", "licensed_to": "", "key": "", "expires": "", "first_run": None}
        self._save()

    def get_limits(self):
        tier = self.get_tier()
        info = TIERS[tier]
        return {k: v for k, v in info.items() if k.startswith("max_")}

    def get_license_info(self):
        tier = self.get_tier()
        info = TIERS[tier]
        return {
            "tier": tier,
            "tier_name": info["name"],
            "licensed_to": self.get_licensed_to(),
            "expires": self._license.get("expires", "N/A"),
            "has_cloud_backup": info["has_cloud_backup"],
            "has_email_invoicing": info["has_email_invoicing"],
            "has_advanced_reports": info["has_advanced_reports"],
            "has_multi_company": info["has_multi_company"],
            "max_stock_items": info["max_stock_items"],
        }


license_manager = LicenseManager()
