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
                    if sys.platform == "win32":
                        import ctypes
                        PROCESS_QUERY_INFORMATION = 0x0400
                        handle = ctypes.windll.kernel32.OpenProcess(
                            PROCESS_QUERY_INFORMATION, False, pid
                        )
                        if handle:
                            ctypes.windll.kernel32.CloseHandle(handle)
                            return True
                    else:
                        os.kill(pid, 0)
                        return True
                except (OSError, ValueError):
                    pass
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        return False
    except Exception as e:
        logger.warning(f"Single instance check failed: {e}")
        return False


def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        logger.warning(f"Failed to release lock: {e}")
