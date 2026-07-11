import os
import sys
import json
from pathlib import Path

VERSION = "2.8.0"
APP_NAME = "Accounting Pro"
APP_GEOMETRY = "1280x780"
APP_MIN_SIZE = "960x640"

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
    "log_level": "INFO",
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
    except (FileNotFoundError, json.JSONDecodeError, OSError):
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
RELEASE_BASE_URL = "https://github.com/ramlalitsharma/BasicAccountingAPP/releases"

FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"
FONT_SIZE_SM = 9
FONT_SIZE_MD = 10
FONT_SIZE_LG = 11
FONT_SIZE_XL = 13
FONT_SIZE_XXL = 20
PADDING_SM = 6
PADDING_MD = 12
PADDING_LG = 20
RADIUS = 8
THEME = "clam"

_LIGHT_COLORS = {
    "PRIMARY_COLOR": "#1B2A4A",
    "PRIMARY_LIGHT": "#2C3E6B",
    "ACCENT_COLOR": "#2563EB",
    "ACCENT_LIGHT": "#3B82F6",
    "ACCENT_DARK": "#1D4ED8",
    "SUCCESS_COLOR": "#059669",
    "SUCCESS_LIGHT": "#10B981",
    "WARNING_COLOR": "#D97706",
    "WARNING_LIGHT": "#F59E0B",
    "DANGER_COLOR": "#DC2626",
    "DANGER_LIGHT": "#EF4444",
    "INFO_COLOR": "#0284C7",
    "INFO_LIGHT": "#0EA5E9",
    "BG_COLOR": "#F1F5F9",
    "BG_DARK": "#E2E8F0",
    "CARD_BG": "#FFFFFF",
    "CARD_BORDER": "#E2E8F0",
    "HEADER_BG": "#F8FAFC",
    "SIDEBAR_BG": "#0F172A",
    "SIDEBAR_FG": "#94A3B8",
    "SIDEBAR_ACTIVE_BG": "#1E293B",
    "SIDEBAR_ACTIVE_FG": "#FFFFFF",
    "SIDEBAR_HOVER_BG": "#1E293B",
    "SIDEBAR_ACCENT": "#3B82F6",
    "MODAL_OVERLAY": "#000000",
    "TEXT_PRIMARY": "#1E293B",
    "TEXT_SECONDARY": "#64748B",
    "TEXT_MUTED": "#94A3B8",
    "BORDER_COLOR": "#CBD5E1",
}

_DARK_COLORS = {
    "PRIMARY_COLOR": "#0F172A",
    "PRIMARY_LIGHT": "#1E293B",
    "ACCENT_COLOR": "#3B82F6",
    "ACCENT_LIGHT": "#60A5FA",
    "ACCENT_DARK": "#2563EB",
    "SUCCESS_COLOR": "#10B981",
    "SUCCESS_LIGHT": "#34D399",
    "WARNING_COLOR": "#F59E0B",
    "WARNING_LIGHT": "#FBBF24",
    "DANGER_COLOR": "#EF4444",
    "DANGER_LIGHT": "#F87171",
    "INFO_COLOR": "#0EA5E9",
    "INFO_LIGHT": "#38BDF8",
    "BG_COLOR": "#0F172A",
    "BG_DARK": "#1E293B",
    "CARD_BG": "#1E293B",
    "CARD_BORDER": "#334155",
    "HEADER_BG": "#1E293B",
    "SIDEBAR_BG": "#020617",
    "SIDEBAR_FG": "#64748B",
    "SIDEBAR_ACTIVE_BG": "#1E293B",
    "SIDEBAR_ACTIVE_FG": "#F1F5F9",
    "SIDEBAR_HOVER_BG": "#1E293B",
    "SIDEBAR_ACCENT": "#3B82F6",
    "MODAL_OVERLAY": "#000000",
    "TEXT_PRIMARY": "#F1F5F9",
    "TEXT_SECONDARY": "#94A3B8",
    "TEXT_MUTED": "#64748B",
    "BORDER_COLOR": "#475569",
}

def _get_current_theme():
    return get_setting("theme", "Light")

def get_color(name):
    theme = _get_current_theme()
    palette = _DARK_COLORS if theme == "Dark" else _LIGHT_COLORS
    return palette.get(name, _LIGHT_COLORS.get(name, "#000000"))

PRIMARY_COLOR = _LIGHT_COLORS["PRIMARY_COLOR"]
PRIMARY_LIGHT = _LIGHT_COLORS["PRIMARY_LIGHT"]
ACCENT_COLOR = _LIGHT_COLORS["ACCENT_COLOR"]
ACCENT_LIGHT = _LIGHT_COLORS["ACCENT_LIGHT"]
ACCENT_DARK = _LIGHT_COLORS["ACCENT_DARK"]
SUCCESS_COLOR = _LIGHT_COLORS["SUCCESS_COLOR"]
SUCCESS_LIGHT = _LIGHT_COLORS["SUCCESS_LIGHT"]
WARNING_COLOR = _LIGHT_COLORS["WARNING_COLOR"]
WARNING_LIGHT = _LIGHT_COLORS["WARNING_LIGHT"]
DANGER_COLOR = _LIGHT_COLORS["DANGER_COLOR"]
DANGER_LIGHT = _LIGHT_COLORS["DANGER_LIGHT"]
INFO_COLOR = _LIGHT_COLORS["INFO_COLOR"]
INFO_LIGHT = _LIGHT_COLORS["INFO_LIGHT"]
BG_COLOR = _LIGHT_COLORS["BG_COLOR"]
BG_DARK = _LIGHT_COLORS["BG_DARK"]
CARD_BG = _LIGHT_COLORS["CARD_BG"]
CARD_BORDER = _LIGHT_COLORS["CARD_BORDER"]
HEADER_BG = _LIGHT_COLORS["HEADER_BG"]
SIDEBAR_BG = _LIGHT_COLORS["SIDEBAR_BG"]
SIDEBAR_FG = _LIGHT_COLORS["SIDEBAR_FG"]
SIDEBAR_ACTIVE_BG = _LIGHT_COLORS["SIDEBAR_ACTIVE_BG"]
SIDEBAR_ACTIVE_FG = _LIGHT_COLORS["SIDEBAR_ACTIVE_FG"]
SIDEBAR_HOVER_BG = _LIGHT_COLORS["SIDEBAR_HOVER_BG"]
SIDEBAR_ACCENT = _LIGHT_COLORS["SIDEBAR_ACCENT"]
MODAL_OVERLAY = _LIGHT_COLORS["MODAL_OVERLAY"]
TEXT_PRIMARY = _LIGHT_COLORS["TEXT_PRIMARY"]
TEXT_SECONDARY = _LIGHT_COLORS["TEXT_SECONDARY"]
TEXT_MUTED = _LIGHT_COLORS["TEXT_MUTED"]
BORDER_COLOR = _LIGHT_COLORS["BORDER_COLOR"]
