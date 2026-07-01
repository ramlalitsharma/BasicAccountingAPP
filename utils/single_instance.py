import os
import sys
import tempfile
import logging

logger = logging.getLogger(__name__)

LOCK_FILE = os.path.join(
    tempfile.gettempdir(), "accounting_pro.lock"
)


def is_already_running():
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, "r") as f:
                pid = f.read().strip()
            if pid:
                try:
                    pid = int(pid)
                    if _is_accounting_pro_running(pid):
                        return True
                    else:
                        logger.info(f"Stale lock file found (PID {pid} not running or not AccountingPro), removing")
                        try:
                            os.remove(LOCK_FILE)
                        except OSError:
                            pass
                except (OSError, ValueError):
                    try:
                        os.remove(LOCK_FILE)
                    except OSError:
                        pass
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        return False
    except (FileNotFoundError, PermissionError, OSError) as e:
        logger.warning(f"Single instance check failed: {e}")
        return False


def _is_accounting_pro_running(pid):
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return False

        try:
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(ctypes.c_uint(512)))
            exe_path = buf.value.lower()
            return exe_path.endswith("accountingpro.exe")
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        return False


def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except (FileNotFoundError, PermissionError, OSError) as e:
        logger.warning(f"Failed to release lock: {e}")
