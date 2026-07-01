import json
import os
import logging
import threading
import hashlib
import subprocess
import sys
import urllib.error
from datetime import datetime
from config import VERSION, CONFIG_DIR, APP_NAME, UPDATE_CHECK_URL

logger = logging.getLogger(__name__)

UPDATE_FILE = os.path.join(CONFIG_DIR, "update.json")
AUTO_CHECK_INTERVAL_HOURS = 24
RETRY_INTERVAL_HOURS = 1

DEFAULT_STATE = {
    "latest_version": "",
    "min_version": "",
    "download_url": "",
    "changelog": "",
    "release_date": "",
    "file_size_mb": 0,
    "sha256_hash": "",
    "force_update": False,
    "last_check": "",
    "last_online_check": "",
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
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(DEFAULT_STATE)


def _save(data):
    try:
        with open(UPDATE_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to save update state: {e}")


def _parse_version(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except (ValueError, TypeError):
        return (0, 0, 0)


def _is_online():
    try:
        import urllib.request
        urllib.request.urlopen("https://raw.githubusercontent.com", timeout=5)
        return True
    except (urllib.error.URLError, OSError):
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
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state["last_check"] = now_str
        state["last_online_check"] = now_str
        state["latest_version"] = data.get("latest_version", "")
        state["min_version"] = data.get("min_version", "")
        state["force_update"] = data.get("force_update", False)
        state["download_url"] = data.get("download_url", "")
        state["changelog"] = data.get("changelog", "")
        state["release_date"] = data.get("release_date", "")
        state["file_size_mb"] = data.get("file_size_mb", 0)
        state["sha256_hash"] = data.get("sha256_hash", "")
        _save(state)
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.debug(f"Update check failed: {e}")
        return None


def get_latest_version():
    return LATEST_KNOWN or _load().get("latest_version", "")


def is_update_available():
    latest = get_latest_version()
    if not latest:
        return False
    try:
        current = _parse_version(VERSION)
        remote = _parse_version(latest)
        return remote > current
    except (OSError, PermissionError):
        return False


def is_mandatory_update():
    state = _load()
    min_ver = state.get("min_version", "")
    if not min_ver:
        return False
    try:
        return _parse_version(VERSION) < _parse_version(min_ver)
    except (ValueError, TypeError):
        return False


def is_server_force_update():
    return _load().get("force_update", False)


def must_update_now():
    if not is_update_available():
        return False
    if is_mandatory_update():
        return True
    if is_server_force_update():
        return True
    return False


def get_update_status():
    state = _load()
    latest = get_latest_version()
    available = is_update_available()
    mandatory = must_update_now()

    last_check_str = state.get("last_check", "")
    last_online = state.get("last_online_check", "")
    is_online = _is_online()

    history = state.get("update_history", [])
    if isinstance(history, list) and len(history) > 20:
        history = history[-20:]

    return {
        "available": available,
        "mandatory": mandatory,
        "latest_version": latest,
        "current_version": VERSION,
        "min_version": state.get("min_version", ""),
        "download_url": state.get("download_url", ""),
        "changelog": state.get("changelog", ""),
        "release_date": state.get("release_date", ""),
        "file_size_mb": state.get("file_size_mb", 0),
        "sha256_hash": state.get("sha256_hash", ""),
        "server_force_update": state.get("force_update", False),
        "last_check": last_check_str,
        "last_online_check": last_online,
        "is_online_now": is_online,
        "downloaded_path": state.get("downloaded_path", ""),
    }


def mark_update_downloaded(filepath):
    state = _load()
    state["downloaded_path"] = filepath
    _save(state)


def update_available_info(latest_version, download_url="", changelog="",
                          release_date="", file_size_mb=0, sha256_hash=""):
    state = _load()
    state["latest_version"] = latest_version
    state["download_url"] = download_url
    state["changelog"] = changelog
    state["release_date"] = release_date
    state["file_size_mb"] = file_size_mb
    state["sha256_hash"] = sha256_hash
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
    except (json.JSONDecodeError, OSError):
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
        except (FileNotFoundError, OSError) as e:
            logger.exception("Download failed")
            if callback:
                callback({"success": False, "error": str(e)})

    thread = threading.Thread(target=_download, daemon=True)
    thread.start()


def verify_download(filepath, expected_hash):
    if not expected_hash:
        return True
    try:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        result = h.hexdigest()
        if result != expected_hash:
            logger.error(f"Hash mismatch: expected={expected_hash} got={result}")
            return False
        return True
    except (FileNotFoundError, OSError) as e:
        logger.error(f"Hash verification failed: {e}")
        return False


def install_update(filepath):
    logger.info(f"Launching update installer: {filepath}")
    try:
        old_exe = sys.executable if getattr(sys, "frozen", False) else None
        if old_exe:
            bat_path = os.path.join(CONFIG_DIR, "_update_launcher.bat")
            with open(bat_path, "w") as bat:
                bat.write('@echo off\n')
                bat.write('echo Updating Accounting Pro...\n')
                bat.write('timeout /t 3 /nobreak >nul\n')
                bat.write(f'taskkill /f /im "{os.path.basename(old_exe)}" 2>nul\n')
                bat.write('timeout /t 2 /nobreak >nul\n')
                bat.write(f'start "" "{filepath}"\n')
                bat.write(f'del "%~f0"\n')
            subprocess.Popen(
                f'cmd /c "{bat_path}"',
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                close_fds=True,
            )
        else:
            os.startfile(filepath)
    except OSError as e:
        logger.error(f"Failed to launch update: {e}")


def auto_update_on_launch():
    state = _load()
    downloaded = state.get("downloaded_path", "")
    if not downloaded or not os.path.exists(downloaded):
        return False

    latest = state.get("latest_version", "")
    if not is_update_available():
        return False

    expected_hash = state.get("sha256_hash", "")
    if not verify_download(downloaded, expected_hash):
        logger.warning("Downloaded update failed hash verification, re-downloading")
        try:
            os.remove(downloaded)
        except OSError:
            pass
        state["downloaded_path"] = ""
        _save(state)
        return False

    logger.info(f"Auto-installing cached update: {downloaded}")
    install_update(downloaded)
    return True
