import os
import sys
import json
from pathlib import Path

VERSION = "1.0.0"
APP_NAME = "Accounting Pro"
APP_GEOMETRY = "1200x750"
APP_MIN_SIZE = "900x600"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(os.path.dirname(sys.executable))
    RESOURCE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent
    RESOURCE_DIR = BASE_DIR

ICON_DIR = RESOURCE_DIR / "icon"
ICON_PATH = str(ICON_DIR / "accounting_pro.ico")
ICON_PNG_PATH = str(ICON_DIR / "accounting_pro.png")

CONFIG_DIR = BASE_DIR / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

os.makedirs(CONFIG_DIR, exist_ok=True)

_DEFAULT_SETTINGS = {
    "data_dir": str(BASE_DIR),
    "theme": "Light",
    "currency_symbol": "\u20B9",
    "last_file": "",
}


def _load_settings():
    if not SETTINGS_FILE.exists():
        return dict(_DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        for k, v in _DEFAULT_SETTINGS.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(_DEFAULT_SETTINGS)


def _save_settings(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


_settings = _load_settings()

USER_DATA_DIR = Path(_settings.get("data_dir", str(BASE_DIR)))
DATA_DIR = USER_DATA_DIR / "data"
BACKUP_DIR = USER_DATA_DIR / "backups"
LOG_DIR = USER_DATA_DIR / "logs"


def update_data_dir(new_path):
    global USER_DATA_DIR, DATA_DIR, BACKUP_DIR, LOG_DIR, _settings
    _settings["data_dir"] = new_path
    _save_settings(_settings)
    USER_DATA_DIR = Path(new_path)
    DATA_DIR = USER_DATA_DIR / "data"
    BACKUP_DIR = USER_DATA_DIR / "backups"
    LOG_DIR = USER_DATA_DIR / "logs"
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def get_setting(key, default=None):
    return _settings.get(key, default)


def set_setting(key, value):
    _settings[key] = value
    _save_settings(_settings)


os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

UPDATE_CHECK_URL = "https://raw.githubusercontent.com/ramlalitsharma/BasicAccountingAPP/main/version.json"
UPDATE_GRACE_DAYS = 15

THEME = "clam"
PRIMARY_COLOR = "#1a1a2e"
PRIMARY_LIGHT = "#16213e"
ACCENT_COLOR = "#0f3460"
ACCENT_LIGHT = "#1a5276"
SUCCESS_COLOR = "#27ae60"
WARNING_COLOR = "#f39c12"
DANGER_COLOR = "#e74c3c"
INFO_COLOR = "#3498db"
BG_COLOR = "#f0f2f5"
CARD_BG = "#ffffff"
SIDEBAR_BG = "#1a1a2e"
SIDEBAR_FG = "#c8d6e5"
SIDEBAR_ACTIVE = "#0f3460"
SIDEBAR_HOVER = "#16213e"
FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"
