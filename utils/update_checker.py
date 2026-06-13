import json
import os
import logging
import threading
from datetime import datetime, timedelta
from config import VERSION, CONFIG_DIR, APP_NAME, UPDATE_GRACE_DAYS

logger = logging.getLogger(__name__)

UPDATE_FILE = os.path.join(CONFIG_DIR, "update.json")

UPDATE_CHECK_URL = "https://raw.githubusercontent.com/ramlalitsharma/BasicAccountingAPP/main/version.json"

GRACE_DAYS = UPDATE_GRACE_DAYS

DEFAULT_STATE = {
    "latest_version": "",
    "download_url": "",
    "changelog": "",
    "notified_at": "",
    "last_check": "",
}

LATEST_KNOWN = ""

os.makedirs(CONFIG_DIR, exist_ok=True)


def _load():
    if not os.path.exists(UPDATE_FILE):
        return dict(DEFAULT_STATE)
    try:
        with open(UPDATE_FILE, "r") as f:
            data = json.load(f)
        for k, v in DEFAULT_STATE.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(DEFAULT_STATE)


def _save(data):
    try:
        with open(UPDATE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save update state: {e}")


def check_for_update_async(callback=None):
    def _check():
        global LATEST_KNOWN
        result = _fetch_version_info()
        if result:
            LATEST_KNOWN = result.get("latest_version", "")
        if callback:
            callback(result)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()


def _fetch_version_info():
    try:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(
            UPDATE_CHECK_URL,
            headers={"User-Agent": f"{APP_NAME}/{VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        state = _load()
        state["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _save(state)
        return data
    except Exception as e:
        logger.debug(f"Update check failed: {e}")
        return None


def get_latest_version():
    return LATEST_KNOWN or _load().get("latest_version", "")


def is_update_available():
    latest = get_latest_version()
    if not latest:
        return False
    try:
        current = tuple(int(x) for x in VERSION.split("."))
        remote = tuple(int(x) for x in latest.split("."))
        return remote > current
    except Exception:
        return False


def get_update_status():
    state = _load()
    latest = get_latest_version()
    available = is_update_available()

    notified_at = state.get("notified_at", "")
    days_remaining = GRACE_DAYS
    force_update = False

    if available and notified_at:
        try:
            notified = datetime.strptime(notified_at, "%Y-%m-%d")
            elapsed = (datetime.now() - notified).days
            days_remaining = max(0, GRACE_DAYS - elapsed)
            force_update = elapsed >= GRACE_DAYS
        except ValueError:
            pass

    return {
        "available": available,
        "latest_version": latest,
        "current_version": VERSION,
        "download_url": state.get("download_url", ""),
        "changelog": state.get("changelog", ""),
        "days_remaining": days_remaining,
        "force_update": force_update,
        "notified_at": notified_at,
    }


def mark_notified():
    state = _load()
    state["notified_at"] = datetime.now().strftime("%Y-%m-%d")
    _save(state)


def update_available_info(latest_version, download_url="", changelog=""):
    state = _load()
    state["latest_version"] = latest_version
    state["download_url"] = download_url
    state["changelog"] = changelog
    _save(state)
    global LATEST_KNOWN
    LATEST_KNOWN = latest_version
