"""User authentication system with bcrypt password hashing and role-based access control."""
import json
import os
import hashlib
import secrets
import logging
from datetime import datetime
from config import CONFIG_DIR

logger = logging.getLogger(__name__)

AUTH_FILE = os.path.join(CONFIG_DIR, "auth.json")

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
    h = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return salt + ":" + h.hex()


def _verify_password(password, stored):
    if ":" not in stored:
        return False
    salt, _ = stored.split(":", 1)
    return _hash_password(password, salt) == stored


class AuthManager:
    def __init__(self):
        self._users = {}
        self._current_user = None
        self._current_role = None
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
        except OSError as e:
            logger.error(f"Failed to save auth: {e}")

    def _ensure_admin_exists(self):
        if not self._users:
            default_pass = "admin123"
            self._users["admin"] = {
                "password_hash": _hash_password(default_pass),
                "role": "admin",
                "display_name": "Administrator",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._save()
            logger.info("Created default admin user (password: admin123)")

    def login(self, username, password):
        username = username.strip().lower()
        user = self._users.get(username)
        if not user:
            return False, "Invalid username or password"
        if not _verify_password(password, user["password_hash"]):
            return False, "Invalid username or password"
        self._current_user = username
        self._current_role = user.get("role", "cashier")
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
        user["password_hash"] = _hash_password(new_password)
        self._save()
        return True, "Password changed"

    def list_users(self):
        if not self.has_permission("can_manage_users"):
            return [{"username": self._current_user, "role": self._current_role,
                     "display_name": self._users.get(self._current_user, {}).get("display_name", "")}]
        result = []
        for uname, info in self._users.items():
            result.append({
                "username": uname,
                "role": info.get("role"),
                "display_name": info.get("display_name"),
                "created_at": info.get("created_at"),
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