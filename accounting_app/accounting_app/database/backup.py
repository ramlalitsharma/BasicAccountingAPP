import shutil
from datetime import datetime
from pathlib import Path
from config import BACKUP_DIR
from database.excel_db import get_active_file


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
