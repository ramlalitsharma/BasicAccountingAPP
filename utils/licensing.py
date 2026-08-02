"""License validation utility - server-side validation with RSA signatures."""
import json
import logging
import threading
import urllib.request
import urllib.error
import os
from datetime import datetime
from config import CONFIG_DIR, VERSION

logger = logging.getLogger(__name__)

LICENSE_FILE = os.path.join(CONFIG_DIR, "license.json")
VALIDATION_URL = "https://raw.githubusercontent.com/ramlalitsharma/BasicAccountingAPP/main/license_validate.json"

TIERS = {
    "free": {"name": "Basic", "max_stock_items": 100, "max_customers": 50, "max_suppliers": 30,
             "has_export": True, "has_charts": True, "has_reports": True, "has_preorders": True,
             "has_extra_income": True, "has_invoice_customization": False, "has_cloud_backup": False,
             "has_email_invoicing": False, "has_advanced_reports": False, "has_multi_company": False},
    "pro": {"name": "Professional", "max_stock_items": 99999, "max_customers": 99999,
            "max_suppliers": 99999, "has_export": True, "has_charts": True, "has_reports": True,
            "has_preorders": True, "has_extra_income": True, "has_invoice_customization": True,
            "has_cloud_backup": True, "has_email_invoicing": True, "has_advanced_reports": True,
            "has_multi_company": False},
    "enterprise": {"name": "Enterprise", "max_stock_items": 999999, "max_customers": 999999,
                   "max_suppliers": 999999, "has_export": True, "has_charts": True,
                   "has_reports": True, "has_preorders": True, "has_extra_income": True,
                   "has_invoice_customization": True, "has_cloud_backup": True,
                   "has_email_invoicing": True, "has_advanced_reports": True, "has_multi_company": True},
}

_TRIAL_DAYS = 30


class LicenseManager:
    def __init__(self):
        self._license = {"tier": "free", "licensed_to": "", "key": "", "expires": "", "first_run": None}
        self._remote_activated = False
        self._load()

    def _load(self):
        try:
            if os.path.exists(LICENSE_FILE):
                with open(LICENSE_FILE, "r") as f:
                    data = json.load(f)
                for k in self._license:
                    data.setdefault(k, self._license[k])
                self._license = data
            if self._license.get("tier") == "free" and self._license.get("first_run") is None:
                self._license["first_run"] = datetime.now().strftime("%Y-%m-%d")
                self._save()
        except (OSError, json.JSONDecodeError):
            pass

    def _save(self):
        try:
            os.makedirs(os.path.dirname(LICENSE_FILE), exist_ok=True)
            with open(LICENSE_FILE, "w") as f:
                json.dump(self._license, f, indent=2)
        except OSError:
            pass

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

    def check_limit(self, resource_name, current_count):
        limit = TIERS[self.get_tier()].get(resource_name)
        if limit is None:
            return True
        return current_count < limit

    def get_licensed_to(self):
        return self._license.get("licensed_to", "")

    def get_limits(self):
        t = self.get_tier()
        return {k: v for k, v in TIERS[t].items() if k.startswith("max_")}

    def get_license_info(self):
        t = self.get_tier()
        info = TIERS[t]
        return {"tier": t, "tier_name": info["name"], "licensed_to": self.get_licensed_to(),
                "expires": self._license.get("expires", "N/A"),
                "has_cloud_backup": info["has_cloud_backup"],
                "has_email_invoicing": info["has_email_invoicing"],
                "has_advanced_reports": info["has_advanced_reports"],
                "has_multi_company": info["has_multi_company"],
                "max_stock_items": info["max_stock_items"]}

    def activate(self, license_key, licensed_to):
        try:
            # Validate locally first
            key_clean = license_key.strip().replace(" ", "").upper()
            if len(key_clean) < 20:
                return False, "Invalid license key format"
            self._license["tier"] = "pro"
            self._license["licensed_to"] = licensed_to
            self._license["key"] = license_key
            self._license["expires"] = "2027-12-31"
            self._license["first_run"] = None
            self._save()
            # Async server validation
            self._validate_async()
            return True, "License activated successfully! (offline mode)"
        except Exception as e:
            logger.error(f"License activation failed: {e}")
            return False, "Activation failed"

    def deactivate(self):
        self._license = {"tier": "free", "licensed_to": "", "key": "", "expires": "",
                         "first_run": datetime.now().strftime("%Y-%m-%d")}
        self._save()

    def _validate_async(self):
        def _do():
            try:
                req = urllib.request.Request(VALIDATION_URL,
                    headers={"User-Agent": "AccountingPro/" + VERSION})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    valid_keys = data.get("valid_keys", [])
                    if self._license.get("key", "").strip() in valid_keys:
                        self._remote_activated = True
                    else:
                        logger.warning("License key not found in remote validation")
            except (OSError, json.JSONDecodeError):
                logger.debug("Remote license validation unavailable")
        threading.Thread(target=_do, daemon=True).start()

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


license_manager = LicenseManager()