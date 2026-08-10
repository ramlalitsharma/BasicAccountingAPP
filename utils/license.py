"""License system: RSA-signed tokens, machine binding, heartbeat, offline grace.

Architecture
------------
1. Admin generates a license token via ``tools/gen_license.py``. The token is a
   JSON blob signed with the admin's RSA private key (kept off-machine).
2. The user pastes the token into Accounting Pro. The desktop app verifies the
   RSA signature with the embedded public key. On success the license is stored
   in DPAPI-encrypted storage. The token itself is never transmitted anywhere.
3. The app sends a heartbeat to the license server every
   ``HEARTBEAT_INTERVAL_DAYS`` days with ``{machine_id, key_hash, tier, app_version}``.
   The server checks the license has not been revoked and the active machine
   count is below ``max_machines``.
4. If the app is offline for more than ``HEARTBEAT_GRACE × HEARTBEAT_INTERVAL_DAYS``
   it shows a nag banner but keeps working (graceful degradation).

Token JSON schema
-----------------
    {
        "version":       2,
        "tier":          "pro",
        "licensee":      "Coffee House Pvt Ltd",
        "issued":        "2026-08-01T00:00:00Z",
        "expires":       "2027-08-01T00:00:00Z",
        "key_hash":      "<sha256 hex of license key>",
        "max_machines":  2,
        "features":      {"whatsapp_invoice": true, ...},
        "sig":           "<base64 RSA-PSS-SHA256 signature over all fields except sig>"
    }
"""
from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from config import CONFIG_DIR, VERSION
from utils.fingerprint import get_machine_id, get_machine_label
from utils.secrets_store import SecretsStore

logger = logging.getLogger(__name__)

# ── paths & server config ─────────────────────────────────────────────────
LICENSE_FILE = os.path.join(str(CONFIG_DIR), "license.enc")
# Production: Cloudflare Workers at accountingpro-license-server.ramlalitsharma01.workers.dev
# Override locally via the ACCOUNTINGPRO_LICENSE_SERVER environment variable.
LICENSE_SERVER_URL = os.environ.get(
    "ACCOUNTINGPRO_LICENSE_SERVER",
    "https://accountingpro-license-server.ramlalitsharma01.workers.dev/api",
)

HEARTBEAT_INTERVAL_DAYS = 7
HEARTBEAT_GRACE = 2  # offline tolerance = HEARTBEAT_GRACE × HEARTBEAT_INTERVAL_DAYS
HEARTBEAT_TIMEOUT_SEC = 15

# ── tiers ──────────────────────────────────────────────────────────────────
FREE_TIER_EXPIRY_DAYS = 14
FREE_MAX_STOCK = 100
BASIC_MAX_STOCK = 500
PRO_MAX_STOCK = 99_999
ENTERPRISE_MAX_STOCK = 999_999

_MAX_STOCK_MAP: Dict[str, int] = {
    "free": FREE_MAX_STOCK,
    "basic": BASIC_MAX_STOCK,
    "pro": PRO_MAX_STOCK,
    "enterprise": ENTERPRISE_MAX_STOCK,
}

_TIER_LABELS: Dict[str, str] = {
    "free": "Free Trial",
    "basic": "Basic",
    "pro": "Professional",
    "enterprise": "Enterprise",
}

_VALID_TIERS = tuple(_MAX_STOCK_MAP.keys())

# ── embedded public key (RSA-2048, PSS-SHA256) ─────────────────────────────
PUBLIC_KEY_PEM = """\
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAlSJsi1FpOjC58DxEB+1m
WPwzmQ/6xpsMk68kMsLiaWV8RpR3Wh+QsmZwAnfLhlG1bpaEwxqlUHWKGm4Jd16V
hpW9rBDixHYAH8YlXQxz5ANCtb/X2t2IRW4fKKTtdZXyitFYjDmts6svVVMc0Nlf
8iXfzAyC/r6QCRZ2fchitgqR5gLat1FwW3cGK9YEW8vNbKRfPNRcnPP3BWxImCpJ
qHWwJgy8rVT+MfPT+fxc3hSR1Z1E1KZy5gLbNHP1YzhXtojdXg83Z7Izd/hoZeCt
iFvm0LfDzfQ/wiXXkdThGzLTkgrYZxiS5hovFBUmGaCv6cyoyTg5cO+J7K8AB+An
ZwIDAQAB
-----END PUBLIC KEY-----"""


def _load_public_key():
    return serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode("ascii"))


PUBLIC_KEY = _load_public_key()


# ── helpers ────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _is_https(url: str) -> bool:
    if url.lower().startswith("https://"):
        return True
    # Allow http://127.0.0.1 / localhost for local tests & on-prem deployments.
    lowered = url.lower()
    if lowered.startswith("http://"):
        if lowered.startswith("http://127.0.0.1") or lowered.startswith("http://localhost"):
            return True
    return False


# ── canonical signing payload ──────────────────────────────────────────────
def _canonical_payload(token: Dict[str, Any]) -> bytes:
    """Return exact UTF-8 bytes that the signature covers (every field but 'sig')."""
    d = {k: v for k, v in token.items() if k != "sig"}
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


# =========================================================================
# LicenseManager
# =========================================================================
class LicenseManager:
    """Owns the local license state. Thread-safe for read properties; activates
    and heartbeat calls must be made from one thread at a time."""

    def __init__(self) -> None:
        self._store = SecretsStore(LICENSE_FILE, description="AccountingPro license")
        self._license: Dict[str, Any] = self._load()
        self._machine_id: str = get_machine_id()
        self._lock = threading.Lock()

    # ── persistence ────────────────────────────────────────────────────────
    def _load(self) -> Dict[str, Any]:
        data = self._store.load()
        if data:
            return data
        return {
            "version": 2,
            "tier": "free",
            "trial_start": None,
            "first_run": None,
            "last_heartbeat": None,
            "heartbeat_success": False,
        }

    def _save(self) -> None:
        self._store.save(self._license)

    # ── signature verification ─────────────────────────────────────────────
    def _verify_token(self, token: Dict[str, Any]) -> bool:
        sig_field = token.get("sig")
        if not sig_field or not isinstance(sig_field, str):
            return False
        payload = _canonical_payload(token)
        try:
            signature = base64.b64decode(sig_field, validate=True)
        except (ValueError, TypeError):
            return False
        try:
            PUBLIC_KEY.verify(
                signature,
                payload,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            logger.warning("License token signature verification FAILED")
            return False
        except Exception as exc:
            logger.warning("Signature verify error: %s", exc)
            return False

    # ── activation ─────────────────────────────────────────────────────────
    @staticmethod
    def _try_b64_json(raw: str) -> Optional[Dict[str, Any]]:
        """Try to decode a base64-encoded JSON object. Returns dict or None."""
        if "\n" in raw or " " in raw:
            # b64 from the admin dashboard could wrap; strip whitespace.
            raw = "".join(raw.split())
        if len(raw) < 16:
            return None
        try:
            decoded = base64.b64decode(raw, validate=True)
        except (ValueError, TypeError):
            return None
        if not decoded.lstrip().startswith(b"{"):
            return None
        try:
            obj = json.loads(decoded.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if isinstance(obj, dict):
            return obj
        return None

    def activate(self, token_json: str) -> Tuple[bool, str]:
        """Parse, verify, store a license token string.

        Accepts either a JSON blob or a base64-encoded JSON blob (as emitted
        by ``tools/gen_license.py``). Returns ``(success, message)``.
        """
        token = None
        raw = (token_json or "").strip()
        if not raw:
            return False, "Empty token — paste the token from the admin dashboard."
        decoded = self._try_b64_json(raw)
        if decoded is not None:
            token = decoded
        else:
            try:
                token = json.loads(raw)
                if not isinstance(token, dict):
                    raise ValueError("not a JSON object")
            except (ValueError, TypeError):
                return False, "Invalid token — paste the token from the admin dashboard."

        if token.get("version") != 2:
            return False, "Unsupported license token version."

        if not self._verify_token(token):
            return False, "License token signature is invalid. It may have been tampered with."

        tier = token.get("tier", "free")
        if tier not in _VALID_TIERS:
            return False, f"Unknown tier: {tier}"

        try:
            max_machines = int(token.get("max_machines", 2))
        except (ValueError, TypeError):
            max_machines = 2
        if max_machines < 1:
            max_machines = 1

        with self._lock:
            self._license.update({
                "version": 2,
                "tier": tier,
                "trial_start": None,
                "first_run": self._license.get("first_run") or token.get("issued"),
                "last_heartbeat": None,
                "heartbeat_success": False,
                "key_hash": token.get("key_hash", ""),
                "licensee": token.get("licensee", ""),
                "expires": token.get("expires", ""),
                "max_machines": max_machines,
                "features_override": token.get("features", {}) or {},
                "machine_id": self._machine_id,
                "machine_label": get_machine_label(),
            })
            self._save()
        # Best-effort first heartbeat; ignore failures (license still valid).
        self._send_heartbeat_sync()
        return True, f"License activated — {tier.upper()} tier. Thank you!"

    def deactivate(self) -> None:
        with self._lock:
            self._license = {
                "version": 2,
                "tier": "free",
                "trial_start": None,
                "first_run": None,
                "last_heartbeat": None,
                "heartbeat_success": False,
            }
            self._save()
        try:
            self._store.clear()
        except Exception:  # pragma: no cover
            pass

    # ── read-only properties ───────────────────────────────────────────────
    @property
    def tier(self) -> str:
        return self._license.get("tier", "free")

    @property
    def tier_name(self) -> str:
        return _TIER_LABELS.get(self.tier, "Free Trial")

    @property
    def is_free(self) -> bool:
        return self.tier == "free"

    @property
    def is_pro(self) -> bool:
        return self.tier in ("pro", "enterprise")

    @property
    def is_enterprise(self) -> bool:
        return self.tier == "enterprise"

    @property
    def max_stock_items(self) -> int:
        return _MAX_STOCK_MAP.get(self.tier, FREE_MAX_STOCK)

    @property
    def max_machines(self) -> int:
        try:
            return int(self._license.get("max_machines", 2))
        except (ValueError, TypeError):
            return 2

    @property
    def licensee(self) -> str:
        return self._license.get("licensee", "") or ""

    @property
    def machine_id(self) -> str:
        return self._machine_id

    @property
    def machine_label(self) -> str:
        return self._license.get("machine_label", get_machine_label())

    @property
    def expires_date(self) -> Optional[str]:
        if self.tier == "free":
            start = self._license.get("trial_start") or self._license.get("first_run")
            if not start:
                # Bootstrap trial lazily.
                start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                self._license["trial_start"] = start
                self._save()
            try:
                t0 = datetime.strptime(str(start)[:10], "%Y-%m-%d")
            except (ValueError, TypeError):
                t0 = datetime.now(timezone.utc)
            return (t0 + timedelta(days=FREE_TIER_EXPIRY_DAYS)).strftime("%Y-%m-%d")
        e = self._license.get("expires")
        if not e:
            return None
        return str(e)[:10]

    @property
    def days_left(self) -> int:
        d = self.expires_date
        if not d:
            return 99_999
        try:
            expiry = datetime.strptime(d, "%Y-%m-%d")
            now = datetime.now(timezone.utc)
            # tolerate expiry stored as UTC date
            delta = expiry.date() - now.date()
            return delta.days
        except (ValueError, TypeError):
            return 0

    @property
    def is_expired(self) -> bool:
        return self.days_left <= 0

    @property
    def last_heartbeat(self) -> Optional[str]:
        return self._license.get("last_heartbeat")

    @property
    def heartbeat_ok(self) -> bool:
        return bool(self._license.get("heartbeat_success"))

    @property
    def heartbeat_status(self) -> str:
        """One of: ok, overdue, never, offline."""
        if self.tier == "free":
            return "n/a"
        last = self._license.get("last_heartbeat")
        if not last:
            return "never"
        try:
            t = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - t).days
            if age_days <= HEARTBEAT_INTERVAL_DAYS:
                return "ok"
            if age_days <= HEARTBEAT_GRACE * HEARTBEAT_INTERVAL_DAYS:
                return "overdue"
            return "offline"
        except (ValueError, TypeError):
            return "unknown"

    def has_feature(self, feature_id: str) -> bool:
        overrides = self._license.get("features_override", {})
        if isinstance(overrides, dict) and feature_id in overrides:
            return bool(overrides[feature_id])
        return True

    # ── trial tracking ────────────────────────────────────────────────────
    def mark_first_run(self) -> None:
        if not self._license.get("first_run"):
            self._license["first_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self._license.setdefault("trial_start", self._license["first_run"])
            self._license["tier"] = "free"
            self._save()

    # ── heartbeat ─────────────────────────────────────────────────────────
    def _build_heartbeat_payload(self) -> Dict[str, Any]:
        return {
            "machine_id": self._machine_id,
            "machine_label": get_machine_label(),
            "key_hash": self._license.get("key_hash", ""),
            "tier": self.tier,
            "licensee": self.licensee,
            "app_version": VERSION,
            "sent_at": _now_iso(),
        }

    def _http_post(self, url: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """HTTPS-only POST that returns parsed JSON or None on failure."""
        if not _is_https(url):
            logger.warning("Refusing non-https heartbeat URL: %s", url)
            return None
        try:
            data = json.dumps(payload).encode("utf-8")
        except (ValueError, TypeError):
            return None
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "AccountingPro License/2",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=HEARTBEAT_TIMEOUT_SEC) as resp:
                if 200 <= getattr(resp, "status", 0) < 300:
                    return json.loads(resp.read().decode("utf-8"))
                logger.warning("Heartbeat non-2xx from %s: %s", url, resp.status)
                return None
        except Exception as exc:
            logger.debug("Heartbeat network error: %s", exc)
            return None

    def _send_heartbeat_sync(self) -> bool:
        if self.tier == "free":
            return True
        url = f"{LICENSE_SERVER_URL}/heartbeat"
        payload = self._build_heartbeat_payload()
        result = self._http_post(url, payload)
        if result and result.get("ok"):
            with self._lock:
                self._license["last_heartbeat"] = _now_iso()
                self._license["heartbeat_success"] = True
                self._save()
            return True
        return False

    def send_heartbeat_now(self) -> Tuple[bool, str]:
        """Manual/run-now heartbeat invoked from the UI. Returns (ok, message)."""
        ok = self._send_heartbeat_sync()
        if ok:
            return True, "Heartbeat OK — license verified with server."
        return False, "Heartbeat failed — will retry automatically. App keeps working."

    def schedule_heartbeat(self) -> None:
        t = threading.Thread(target=self._heartbeat_worker, daemon=True)
        t.start()

    def _heartbeat_worker(self) -> None:
        """Background loop: send a heartbeat once per interval; retry on failure."""
        # Send an initial one shortly after launch (network warm-up).
        time.sleep(60)
        while True:
            try:
                self._send_heartbeat_sync()
            except Exception as exc:  # pragma: no cover
                logger.debug("Heartbeat worker exception: %s", exc)
            # Sleep until next scheduled check.
            time.sleep(HEARTBEAT_INTERVAL_DAYS * 86_400)


# =========================================================================
# Module-level singleton
# =========================================================================
license_mgr = LicenseManager()


__all__ = [
    "LicenseManager",
    "license_mgr",
    "PUBLIC_KEY_PEM",
    "LICENSE_SERVER_URL",
    "HEARTBEAT_INTERVAL_DAYS",
    "HEARTBEAT_GRACE",
    "FREE_TIER_EXPIRY_DAYS",
    "_canonical_payload",
]
