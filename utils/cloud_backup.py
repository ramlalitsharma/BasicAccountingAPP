"""Cloud backup upload + scheduled sync.

Design
------
- The desktop app uploads its latest local ``.xlsx`` backup to the configured
  HTTPS endpoint (defaults to the AccountingPro license server's
  ``/api/backup`` route) using a simple multipart POST with the machine id and
  the license key hash for identity. An optional bearer token (stored
  DPAPI-encrypted) enables server-side ACLs.
- Everything degrades gracefully: no endpoint reachable -> error message, no
  crash; disabled -> no-op. Uploads run on daemon threads so the UI never
  blocks.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB hard cap
DEFAULT_TIMEOUT_SEC = 60


def _gs(key, default=None):
    from config import get_setting
    return get_setting(key, default)


def _ss(key, value) -> None:
    from config import set_setting
    set_setting(key, value)


# ── settings & secrets ─────────────────────────────────────────────────────
def is_enabled() -> bool:
    return bool(_gs("cloud_backup.enabled", False))


def get_endpoint() -> str:
    ep = (_gs("cloud_backup.endpoint", "") or "").strip()
    if ep:
        return ep
    from utils.license import LICENSE_SERVER_URL
    return f"{LICENSE_SERVER_URL}/backup"


def get_interval_hours() -> int:
    try:
        return max(1, int(_gs("cloud_backup.interval_hours", 24) or 24))
    except (ValueError, TypeError):
        return 24


def last_upload() -> str:
    return _gs("cloud_backup.last_upload", "") or ""


def _token_store():
    from config import CONFIG_DIR
    from utils.secrets_store import SecretsStore
    return SecretsStore(os.path.join(str(CONFIG_DIR), "cloud_backup.enc"),
                        description="AccountingPro cloud backup token")


def save_token(token: str) -> None:
    store = _token_store()
    if token:
        store.save({"api_token": token})
    else:
        store.clear()


def load_token() -> str:
    try:
        return str(_token_store().load().get("api_token", "") or "")
    except Exception:
        return ""


# ── upload ─────────────────────────────────────────────────────────────────
def _allowed_url(url: str) -> bool:
    u = url.lower()
    if u.startswith("https://"):
        return True
    return u.startswith(("http://127.0.0.1", "http://localhost"))  # local testing only


def _multipart_body(fields: dict, file_field: str, file_path: str) -> tuple:
    boundary = "----AccountingProBackup" + uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode("utf-8")
        )
    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        data = f.read()
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
        .encode("utf-8")
        + data + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), boundary


def upload_backup_file(path: str = None):
    """Create (if needed) and upload a backup file. Returns ``(ok, message)``."""
    from database.backup import backup_database

    if not is_enabled():
        return False, "Cloud backup is disabled — enable it in Settings → Backup."
    if path is None:
        path = backup_database()
    if not path or not os.path.isfile(path):
        return False, "No backup file available (open a workbook first)."
    size = os.path.getsize(path)
    if size <= 0:
        return False, "Backup file is empty."
    if size > MAX_UPLOAD_BYTES:
        return False, f"Backup too large ({size / 1048576:.1f} MB > 25 MB limit)."

    url = get_endpoint()
    if not _allowed_url(url):
        return False, "Backup endpoint must be https:// (Settings → Backup)."

    from utils.fingerprint import get_machine_id, get_machine_label
    from utils.license import license_mgr
    from config import VERSION
    fields = {
        "machine_id": get_machine_id(),
        "machine_label": get_machine_label(),
        "key_hash": getattr(license_mgr, "_license", {}).get("key_hash", "") or "",
        "app_version": VERSION,
    }
    body, boundary = _multipart_body(fields, "file", path)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}",
               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AccountingPro/2.11.1 Desktop"}
    token = load_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SEC) as resp:
            ok = 200 <= getattr(resp, "status", 0) < 300
            try:
                payload = json.loads(resp.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                payload = {}
        if ok and payload.get("ok", True):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _ss("cloud_backup.last_upload", ts)
            return True, f"Backup uploaded ({os.path.basename(path)})"
        return False, f"Server rejected backup ({payload.get('error') or getattr(resp, 'status', '?')})"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        logger.warning("Cloud backup failed: %s", exc)
        return False, f"Cloud backup failed: {exc}"
    except Exception as exc:  # pragma: no cover
        logger.exception("Cloud backup failed unexpectedly")
        return False, f"Cloud backup failed: {exc}"


def upload_backup_async(callback=None) -> None:
    """Run an upload on a daemon thread; ``callback(ok, message)`` runs on the
    worker thread — callers must marshal UI updates themselves."""

    def _run():
        result = upload_backup_file()
        if callback:
            try:
                callback(*result)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()


def maybe_auto_upload() -> None:
    """Called from the local auto-backup timer: uploads when cloud backup is
    enabled and the last successful upload is older than the interval."""
    if not is_enabled():
        return
    last = last_upload()
    if last:
        try:
            age_h = (datetime.now() - datetime.strptime(last, "%Y-%m-%d %H:%M:%S")).total_seconds() / 3600
            if age_h < get_interval_hours():
                return
        except (ValueError, TypeError):
            pass

    def _run():
        ok, msg = upload_backup_file()
        if ok:
            logger.info("Cloud backup: %s", msg)
        else:
            logger.debug("Cloud backup skipped/failed: %s", msg)

    threading.Thread(target=_run, daemon=True).start()
