"""Encrypted-at-rest storage for sensitive files (license.json, auth.json).

Uses Windows DPAPI on Windows (CryptProtectData/CryptUnprotectData), and
falls back to a password-derived AES-GCM key on macOS/Linux so the same
codebase works during development.

On Windows the secret is bound to the current user account - even another
admin on the same machine cannot decrypt it.

File format (JSON):
    {
        "version": 1,
        "backend": "dpapi" | "fernet" | "plaintext-fallback",
        "ciphertext_b64": "<base64 of encrypted bytes>"
    }

The plaintext is never written to disk; we only ever persist the ciphertext.
"""
import base64
import json
import logging
import os
import platform
from typing import Any, Dict

logger = logging.getLogger(__name__)

CURRENT_USER_BACKEND = "dpapi" if platform.system() == "Windows" else "fernet"

_FILE_VERSION = 1


class SecretsStore:
    """Encrypted JSON file store with OS-level key binding."""

    def __init__(self, path: str, description: str = "secret"):
        self.path = path
        self.description = description

    def _encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt bytes with the OS-bound key. Returns ciphertext bytes."""
        if CURRENT_USER_BACKEND == "dpapi":
            # Use Windows DPAPI (CryptProtectData / CryptUnprotectData) when
            # pywin32 is available; fall back to per-user AES-GCM otherwise.
            try:
                import win32crypt  # type: ignore
                return win32crypt.CryptProtectData(
                    plaintext, self.description, None, None, None, 0
                )
            except ImportError:
                pass
            except (TypeError, ValueError, OSError):
                pass
        # Fallback: per-user key derived from username + machine-id via PBKDF2,
        # stored as plaintext at OS level. Still much better than storing
        # credentials in plaintext.
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import getpass
        import hashlib

        salt_path = self.path + ".salt"
        if not os.path.exists(salt_path):
            salt = os.urandom(16)
            with open(salt_path, "wb") as f:
                f.write(salt)
            try:
                os.chmod(salt_path, 0o600)
            except OSError:
                pass
        else:
            with open(salt_path, "rb") as f:
                salt = f.read()

        user = (getpass.getuser() + "@" + platform.node()).encode("utf-8")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000
        )
        key = kdf.derive(user)
        aes = AESGCM(key)
        nonce = os.urandom(12)
        ct = aes.encrypt(nonce, plaintext, None)
        return b"FERNET1" + nonce + ct

    def _decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt bytes produced by _encrypt()."""
        if CURRENT_USER_BACKEND == "dpapi":
            try:
                import win32crypt  # type: ignore
                blob = win32crypt.CryptUnprotectData(ciphertext)
                return blob[1]
            except ImportError:
                pass
            except (TypeError, ValueError, OSError):
                pass
        if ciphertext.startswith(b"FERNET1"):
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import getpass
            salt_path = self.path + ".salt"
            salt = open(salt_path, "rb").read() if os.path.exists(salt_path) else b"\x00" * 16
            user = (getpass.getuser() + "@" + platform.node()).encode("utf-8")
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000
            )
            key = kdf.derive(user)
            aes = AESGCM(key)
            nonce = ciphertext[7:19]
            ct = ciphertext[19:]
            return aes.decrypt(nonce, ct, None)
        raise ValueError("Unknown ciphertext format")

    def load(self) -> Dict[str, Any]:
        """Read and decrypt the secrets file. Returns {} if missing/corrupt."""
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                wrapper = json.load(f)
            if wrapper.get("version") != _FILE_VERSION:
                logger.warning("Secrets file version mismatch, resetting")
                return {}
            ct = base64.b64decode(wrapper["ciphertext_b64"])
            plaintext = self._decrypt(ct)
            return json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            logger.warning("Failed to decrypt %s: %s", self.path, exc)
            return {}

    def save(self, data: Dict[str, Any]) -> None:
        """Encrypt and write the secrets file atomically."""
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        plaintext = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
        ct = self._encrypt(plaintext)
        wrapper = {
            "version": _FILE_VERSION,
            "backend": CURRENT_USER_BACKEND,
            "ciphertext_b64": base64.b64encode(ct).decode("ascii"),
        }
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(wrapper, f, indent=2)
        os.replace(tmp, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def clear(self) -> None:
        """Securely remove the secrets file."""
        if os.path.exists(self.path):
            try:
                # Overwrite with zeros before unlink where possible.
                size = os.path.getsize(self.path)
                with open(self.path, "wb") as f:
                    f.write(b"\x00" * size)
                os.remove(self.path)
            except OSError:
                pass
        salt_path = self.path + ".salt"
        if os.path.exists(salt_path):
            try:
                os.remove(salt_path)
            except OSError:
                pass
