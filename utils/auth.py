"""User authentication system with PBKDF2 password hashing, role-based access
control, brute-force lockout, password policy and login auditing.

Hash formats
------------
- Legacy: ``salt:hex``                      — PBKDF2-HMAC-SHA256 @ 100k iters
- Current: ``pbkdf2:iters:salt:hex``        — iteration count carried in the
  record, so new passwords can use a higher work factor without breaking
  existing accounts (verified transparently, upgraded on next password set).
"""
import json
import os
import hashlib
import hmac
import secrets
import logging
import time
from datetime import datetime
from config import CONFIG_DIR

logger = logging.getLogger(__name__)

AUTH_FILE = os.path.join(CONFIG_DIR, "auth.json")

_PBKDF2_LEGACY_ITERATIONS = 100_000
_PBKDF2_ITERATIONS = 310_000  # OWASP 2023+ guidance for HMAC-SHA256

# ── brute-force lockout ────────────────────────────────────────────────────
_MAX_FAILURES = 5          # attempts allowed before lockout kicks in
_LOCKOUT_BASE_SEC = 60     # 5 failures -> 60s, then doubles per extra failure
_LOCKOUT_MAX_SEC = 30 * 60

# ── password policy ─────────────────────────────────────────────────────────
_MIN_PASSWORD_LEN = 8
_COMMON_PASSWORDS = {
    "password", "password1", "123456", "12345678", "123456789", "admin123",
    "admin", "qwerty", "letmein", "welcome", "iloveyou", "abc123",
}

ROLES = {
    "admin": {"name": "Administrator", "priority": 0, "can_manage_users": True, "can_manage_license": True,
              "can_delete": True, "can_export": True, "can_print": True, "can_edit_prices": True},
    "manager": {"name": "Manager", "priority": 1, "can_manage_users": False, "can_manage_license": False,
                "can_delete": True, "can_export": True, "can_print": True, "can_edit_prices": True},
    "cashier": {"name": "Cashier", "priority": 2, "can_manage_users": False, "can_manage_license": False,
                "can_delete": False, "can_export": False, "can_print": True, "can_edit_prices": False},
}


def _hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'),
                            _PBKDF2_ITERATIONS)
    return f"pbkdf2:{_PBKDF2_ITERATIONS}:{salt}:{h.hex()}"


def _verify_password(password, stored):
    """Verify against both the current and the legacy hash format."""
    if not stored or ":" not in stored:
        return False
    if stored.startswith("pbkdf2:"):
        try:
            _, iters, salt, hash_hex = stored.split(":", 3)
            iters = int(iters)
        except (ValueError, TypeError):
            return False
        calc = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                   salt.encode('utf-8'), iters)
        return hmac.compare_digest(calc.hex(), hash_hex)
    # Legacy: salt:hex @ fixed 100k iterations
    salt, hash_hex = stored.split(":", 1)
    calc = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                               salt.encode('utf-8'), _PBKDF2_LEGACY_ITERATIONS)
    return hmac.compare_digest(f"{salt}:{calc.hex()}", stored)


def validate_password_strength(password):
    """Return ``(ok, message)`` for a candidate password."""
    pw = password or ""
    if len(pw) < _MIN_PASSWORD_LEN:
        return False, f"Password must be at least {_MIN_PASSWORD_LEN} characters"
    if pw.lower() in _COMMON_PASSWORDS:
        return False, "Password is too common — choose something stronger"
    if not any(c.isalpha() for c in pw) or not any(c.isdigit() for c in pw):
        return False, "Password must contain letters and digits"
    return True, "OK"


def _audit_login(username, success, note=""):
    """Best-effort login auditing: app log + workbook audit trail when open."""
    if success:
        logger.info("Login OK: %s", username)
    else:
        logger.warning("Login FAILED: %s (%s)", username, note or "invalid credentials")
    try:
        from database.audit import log
        log("LOGIN" if success else "LOGIN_FAILED", "User", str(username or "?"), note)
    except Exception:
        pass


class AuthManager:
    def __init__(self):
        self._users = {}
        self._current_user = None
        self._current_role = None
        # {username: {"count": int, "locked_until": float epoch}}
        self._failures = {}
        self._load()
        self._ensure_admin_exists()

    def _load(self):
        try:
            if os.path.exists(AUTH_FILE):
                with open(AUTH_FILE, 'r') as f:
                    self._users = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._users = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
            with open(AUTH_FILE, 'w') as f:
                json.dump(self._users, f, indent=2)
            try:
                os.chmod(AUTH_FILE, 0o600)
            except OSError:
                pass
        except OSError as e:
            logger.error(f"Failed to save auth: {e}")

    def _ensure_admin_exists(self):
        if not self._users:
            default_pass = "admin123"
            self._users["admin"] = {
                "password_hash": _hash_password(default_pass),
                "role": "admin",
                "display_name": "Administrator",
                "must_change_password": True,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._save()
            logger.warning("Created default admin user — password change required on first login")

    # ── lockout helpers ────────────────────────────────────────────────────
    def _lockout_remaining(self, username):
        rec = self._failures.get(username)
        if not rec:
            return 0
        remaining = int(rec.get("locked_until", 0) - time.time())
        return max(0, remaining)

    def _record_failure(self, username):
        rec = self._failures.setdefault(username, {"count": 0, "locked_until": 0})
        rec["count"] += 1
        if rec["count"] >= _MAX_FAILURES:
            extra = rec["count"] - _MAX_FAILURES
            secs = min(_LOCKOUT_BASE_SEC * (2 ** extra), _LOCKOUT_MAX_SEC)
            rec["locked_until"] = time.time() + secs
            logger.warning("Account '%s' locked for %ds after %d failed logins",
                           username, secs, rec["count"])
            _audit_login(username, False, f"lockout {secs}s")

    def _record_success(self, username):
        self._failures.pop(username, None)

    def needs_password_reset(self, username=None):
        u = self._users.get((username or self._current_user or "").strip().lower())
        return bool(u and u.get("must_change_password"))

    def login(self, username, password):
        username = username.strip().lower()
        remaining = self._lockout_remaining(username)
        if remaining > 0:
            return False, (f"Account temporarily locked after too many failed attempts. "
                           f"Try again in {remaining // 60 + 1} min.")
        user = self._users.get(username)
        if not user:
            _audit_login(username, False, "unknown user")
            time.sleep(0.4)  # make unknown-user probing the same cost as a hash check
            return False, "Invalid username or password"
        if not _verify_password(password, user["password_hash"]):
            self._record_failure(username)
            _audit_login(username, False, "bad password")
            remaining = self._lockout_remaining(username)
            if remaining > 0:
                return False, (f"Too many failed attempts — account locked. "
                               f"Try again in {remaining // 60 + 1} min.")
            return False, "Invalid username or password"
        self._record_success(username)
        # Transparent work-factor upgrade for legacy hashes on successful login.
        if not str(user.get("password_hash", "")).startswith("pbkdf2:"):
            user["password_hash"] = _hash_password(password)
            self._save()
        self._current_user = username
        self._current_role = user.get("role", "cashier")
        _audit_login(username, True, "")
        return True, f"Welcome, {user.get('display_name', username)}!"

    def logout(self):
        self._current_user = None
        self._current_role = None

    def is_logged_in(self):
        return self._current_user is not None

    def get_current_user(self):
        return self._current_user

    def get_current_role(self):
        return self._current_role

    def get_role_permissions(self, role=None):
        return ROLES.get(role or self._current_role, ROLES["cashier"])

    def has_permission(self, permission):
        if not self._current_user:
            return False
        perms = self.get_role_permissions()
        return perms.get(permission, False)

    def add_user(self, username, password, role, display_name, by_user=None):
        if not self.has_permission("can_manage_users"):
            return False, "Permission denied"
        username = username.strip().lower()
        if username in self._users:
            return False, "Username already exists"
        if role not in ROLES:
            return False, "Invalid role"
        ok, msg = validate_password_strength(password)
        if not ok:
            return False, msg
        self._users[username] = {
            "password_hash": _hash_password(password),
            "role": role,
            "display_name": display_name,
            "created_by": by_user or self._current_user,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save()
        return True, f"User '{display_name}' created as {role}"

    def change_password(self, username, old_password, new_password):
        username = username.strip().lower()
        user = self._users.get(username)
        if not user:
            return False, "User not found"
        if not _verify_password(old_password, user["password_hash"]):
            return False, "Current password is incorrect"
        ok, msg = validate_password_strength(new_password)
        if not ok:
            return False, msg
        user["password_hash"] = _hash_password(new_password)
        user.pop("must_change_password", None)
        self._save()
        return True, "Password changed"

    def reset_user_password(self, username, new_password):
        """Admin resets another user's password (no old password needed)."""
        if not self.has_permission("can_manage_users"):
            return False, "Permission denied"
        username = username.strip().lower()
        user = self._users.get(username)
        if not user:
            return False, "User not found"
        ok, msg = validate_password_strength(new_password)
        if not ok:
            return False, msg
        user["password_hash"] = _hash_password(new_password)
        user["must_change_password"] = True
        self._save()
        return True, f"Password reset for '{username}' — they'll be asked to change it"

    def list_users(self):
        if not self.has_permission("can_manage_users"):
            return [{"username": self._current_user or "—",
                     "role": self._current_role or "viewer",
                     "display_name": (self._users.get(self._current_user, {}) or {}).get("display_name", ""),
                     "created_at": (self._users.get(self._current_user, {}) or {}).get("created_at", "")}]
        result = []
        for uname, info in self._users.items():
            role = info.get("role") or "cashier"
            if role not in ROLES:
                role = "cashier"
            result.append({
                "username": uname,
                "role": role,
                "display_name": info.get("display_name") or uname,
                "created_at": info.get("created_at") or "",
            })
        return sorted(result, key=lambda x: ROLES.get(x["role"], {}).get("priority", 99))

    def delete_user(self, username):
        if not self.has_permission("can_manage_users"):
            return False, "Permission denied"
        username = username.strip().lower()
        if username == "admin":
            return False, "Cannot delete admin user"
        if username not in self._users:
            return False, "User not found"
        del self._users[username]
        self._save()
        return True, f"User '{username}' deleted"


auth_manager = AuthManager()