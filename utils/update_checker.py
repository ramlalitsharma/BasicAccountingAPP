import json
import os
import logging
import threading
import time
from datetime import datetime, timedelta
from config import VERSION, CONFIG_DIR, APP_NAME, UPDATE_GRACE_DAYS

logger = logging.getLogger(__name__)

UPDATE_FILE = os.path.join(CONFIG_DIR, "update.json")

UPDATE_CHECK_URL = "https://raw.githubusercontent.com/ramlalitsharma/BasicAccountingAPP/main/version.json"

RELEASE_BASE_URL = "https://github.com/ramlalitsharma/BasicAccountingAPP/releases"

GRACE_DAYS = UPDATE_GRACE_DAYS
AUTO_CHECK_INTERVAL_HOURS = 24
RETRY_INTERVAL_HOURS = 1

DEFAULT_STATE = {
    "latest_version": "",
    "download_url": "",
    "changelog": "",
    "release_date": "",
    "file_size_mb": 0,
    "notified_at": "",
    "last_check": "",
    "last_online_check": "",
    "skipped_version": "",
    "update_history": [],
    "download_progress": 0,
    "downloaded_path": "",
}

LATEST_KNOWN = ""
_is_checking = False

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
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Failed to save update state: {e}")


def _parse_version(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except Exception:
        return (0, 0, 0)


def _is_online():
    try:
        import urllib.request
        urllib.request.urlopen("https://raw.githubusercontent.com", timeout=5)
        return True
    except Exception:
        return False


def check_for_update_async(callback=None, force=False):
    global _is_checking
    if _is_checking and not force:
        if callback:
            callback(None)
        return

    def _check():
        global LATEST_KNOWN, _is_checking
        _is_checking = True
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            state = _load()
            state["last_check"] = now_str
            _save(state)

            result = _fetch_version_info()
            if result:
                LATEST_KNOWN = result.get("latest_version", "")
                state = _load()
                state["last_online_check"] = now_str
                _save(state)
                if callback:
                    callback(result)
            else:
                if callback:
                    callback(None)
        finally:
            _is_checking = False

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
        state["last_online_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _save(state)
        return data
    except Exception as e:
        logger.debug(f"Update check failed: {e}")
        return None


def get_latest_version():
    return LATEST_KNOWN or _load().get("latest_version", "")


def is_update_available(skip_skipped=True):
    latest = get_latest_version()
    if not latest:
        return False
    try:
        current = _parse_version(VERSION)
        remote = _parse_version(latest)
        if remote <= current:
            return False
        if skip_skipped:
            skipped = _load().get("skipped_version", "")
            if skipped and _parse_version(skipped) >= remote:
                return False
        return True
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

    last_check_str = state.get("last_check", "")
    last_online = state.get("last_online_check", "")
    is_online = _is_online()

    history = state.get("update_history", [])
    if isinstance(history, list) and len(history) > 20:
        history = history[-20:]

    return {
        "available": available,
        "latest_version": latest,
        "current_version": VERSION,
        "download_url": state.get("download_url", ""),
        "changelog": state.get("changelog", ""),
        "release_date": state.get("release_date", ""),
        "file_size_mb": state.get("file_size_mb", 0),
        "days_remaining": days_remaining,
        "force_update": force_update,
        "notified_at": notified_at,
        "last_check": last_check_str,
        "last_online_check": last_online,
        "is_online_now": is_online,
        "skipped_version": state.get("skipped_version", ""),
        "downloaded_path": state.get("downloaded_path", ""),
    }


def mark_notified():
    state = _load()
    state["notified_at"] = datetime.now().strftime("%Y-%m-%d")
    _save(state)


def skip_version(version):
    state = _load()
    state["skipped_version"] = version
    _save(state)
    logger.info(f"Skipped update v{version}")


def mark_update_downloaded(filepath):
    state = _load()
    state["downloaded_path"] = filepath
    _save(state)


def update_available_info(latest_version, download_url="", changelog="", release_date="", file_size_mb=0):
    state = _load()
    state["latest_version"] = latest_version
    state["download_url"] = download_url
    state["changelog"] = changelog
    state["release_date"] = release_date
    state["file_size_mb"] = file_size_mb
    state["downloaded_path"] = ""
    _save(state)
    global LATEST_KNOWN
    LATEST_KNOWN = latest_version

    history = state.get("update_history", [])
    if not isinstance(history, list):
        history = []
    history.append({
        "version": latest_version,
        "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "changelog": changelog[:100] if changelog else "",
    })
    state["update_history"] = history
    _save(state)


def needs_auto_check():
    state = _load()
    last_check = state.get("last_check", "")
    if not last_check:
        return True
    try:
        last = datetime.strptime(last_check, "%Y-%m-%d %H:%M:%S")
        hours_since = (datetime.now() - last).total_seconds() / 3600
        if hours_since >= AUTO_CHECK_INTERVAL_HOURS:
            return True
        if is_update_available():
            return False
        return hours_since >= RETRY_INTERVAL_HOURS
    except Exception:
        return True


def download_update_async(download_url, callback=None):
    def _download():
        import urllib.request
        import tempfile
        try:
            temp_dir = CONFIG_DIR
            os.makedirs(temp_dir, exist_ok=True)
            file_ext = ".exe" if ".exe" in download_url else ".msi"
            temp_path = os.path.join(temp_dir, f"{APP_NAME}_update{file_ext}")

            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": f"{APP_NAME}/{VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                last_reported = -1
                chunk_size = 65536
                with open(temp_path, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int(downloaded / total_size * 100)
                        else:
                            progress = 0
                        if progress != last_reported:
                            last_reported = progress
                            state = _load()
                            state["download_progress"] = progress
                            _save(state)

            mark_update_downloaded(temp_path)
            if callback:
                callback({"success": True, "path": temp_path})
        except Exception as e:
            logger.error(f"Download failed: {e}")
            if callback:
                callback({"success": False, "error": str(e)})

    thread = threading.Thread(target=_download, daemon=True)
    thread.start()
