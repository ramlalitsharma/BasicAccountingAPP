import shutil
import os
import logging
import threading
from datetime import datetime
from pathlib import Path
from config import BACKUP_DIR, DATA_DIR
from database.excel_db import get_active_file

logger = logging.getLogger(__name__)


def backup_database():
    src = get_active_file()
    if not src or not Path(src).exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = Path(src).stem
    backup_name = f"{name}_backup_{timestamp}.xlsx"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(str(src), str(backup_path))
    _cleanup_old_backups()
    return str(backup_path)


def _cleanup_old_backups(keep=20):
    backups = sorted(BACKUP_DIR.glob("*_backup_*.xlsx"), reverse=True)
    for old in backups[keep:]:
        old.unlink()


def create_backup():
    """Create a timestamped backup of all data files."""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        for f in os.listdir(DATA_DIR):
            if f.endswith('.xlsx'):
                src = os.path.join(DATA_DIR, f)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                dst = os.path.join(BACKUP_DIR, f"backup_{ts}_{f}")
                shutil.copy2(src, dst)
        logger.info(f"Backup created at {BACKUP_DIR}")
        return True
    except (OSError, PermissionError, shutil.Error) as e:
        logger.exception("Backup failed")
        return False


_auto_backup_timer = None


def start_auto_backup(interval_minutes=30):
    """Start periodic auto-backup."""
    global _auto_backup_timer
    stop_auto_backup()

    def _run():
        create_backup()
        global _auto_backup_timer
        _auto_backup_timer = threading.Timer(interval_minutes * 60, _run)
        _auto_backup_timer.daemon = True
        _auto_backup_timer.start()

    _run()
    logger.info(f"Auto-backup started every {interval_minutes} minutes")


def stop_auto_backup():
    """Stop auto-backup timer."""
    global _auto_backup_timer
    if _auto_backup_timer:
        _auto_backup_timer.cancel()
        _auto_backup_timer = None
