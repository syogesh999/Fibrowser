import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from PyQt5.QtCore import QSize, QUrl
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStyle

# Application Metadata & Dimension Constants
DEFAULT_HOME_PAGE = "https://www.msn.com"
DEFAULT_SEARCH_ENGINE = "Google"
APP_NAME = "Fibrowser Pro"
APP_VERSION = "2.1.0"
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 700
MAX_TABS = 100
TAB_THROTTLE_SECONDS = 0.1
HISTORY_MAX_SIZE = 500
HISTORY_SAVE_DEBOUNCE_MS = 2000
PROGRESS_BAR_HEIGHT = 3
DEFAULT_ZOOM = 1.0
LOG_FILE_NAME = "debug.log"

# Patterns of sensitive system files to protect against unauthorized access
SENSITIVE_FILE_PATTERNS = [
    "config\\sam",
    "config/sam",
    "config\\system",
    "config/system",
    "config\\security",
    "config/security",
    "drivers\\etc\\hosts",
    "drivers/etc/hosts",
    "/etc/shadow",
    "/etc/passwd",
    "id_rsa",
    "id_ed25519",
    ".env",
    "ntds.dit"
]

SEARCH_ENGINES: Dict[str, str] = {
    "Google": "https://www.google.com/search?q={}",
    "Bing": "https://www.bing.com/search?q={}",
    "DuckDuckGo": "https://duckduckgo.com/?q={}",
    "YouTube": "https://www.youtube.com/results?search_query={}",
    "Wikipedia": "https://en.wikipedia.org/w/index.php?search={}"
}

@dataclass
class Theme:
    """Theme color configuration definition"""
    name: str
    bg: str
    fg: str
    tab_bg: str
    tab_active: str
    url_bg: str
    hover: str
    accent: str

THEMES: Dict[str, Theme] = {
    "Light": Theme(
        name="Light",
        bg="#ffffff",
        fg="#000000",
        tab_bg="#f1f1f1",
        tab_active="#ffffff",
        url_bg="#f1f3f4",
        hover="rgba(0, 0, 0, 0.05)",
        accent="#1a73e8"
    ),
    "Dark": Theme(
        name="Dark",
        bg="#202124",
        fg="#e8eaed",
        tab_bg="#3c4043",
        tab_active="#202124",
        url_bg="#525355",
        hover="rgba(255, 255, 255, 0.1)",
        accent="#8ab4f8"
    ),
    "Blue": Theme(
        name="Blue",
        bg="#e3f2fd",
        fg="#0d47a1",
        tab_bg="#bbdefb",
        tab_active="#e3f2fd",
        url_bg="#bbdefb",
        hover="rgba(13, 71, 161, 0.05)",
        accent="#1976d2"
    ),
    "Nord": Theme(
        name="Nord",
        bg="#2e3440",
        fg="#eceff4",
        tab_bg="#3b4252",
        tab_active="#2e3440",
        url_bg="#434c5e",
        hover="rgba(255, 255, 255, 0.08)",
        accent="#88c0d0"
    ),
    "Dracula": Theme(
        name="Dracula",
        bg="#282a36",
        fg="#f8f8f2",
        tab_bg="#44475a",
        tab_active="#282a36",
        url_bg="#383a47",
        hover="rgba(255, 255, 255, 0.1)",
        accent="#50fa7b"
    )
}

# Standard icon fallback dictionary mapping icon names to Qt StandardPixmaps
ICON_FALLBACK_MAP = {
    "fibrowser.ico": QStyle.SP_ComputerIcon,
    "fibrowser.png": QStyle.SP_ComputerIcon,
    "favicon.png": QStyle.SP_ComputerIcon,
    "back_icon.png": QStyle.SP_ArrowBack,
    "next_icon.png": QStyle.SP_ArrowForward,
    "refresh_icon.png": QStyle.SP_BrowserReload,
    "home_icon.png": QStyle.SP_DirHomeIcon,
    "bookmarks_icon.png": QStyle.SP_DirLinkIcon,
    "history_icon.png": QStyle.SP_FileDialogListView,
    "downloads_icon.png": QStyle.SP_DialogSaveButton,
    "private_icon.png": QStyle.SP_FileDialogEnd,
    "settings_icon.png": QStyle.SP_FileDialogDetailedView,
    "web_dark_icon.png": QStyle.SP_DesktopIcon,
}

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev mode and for PyInstaller bundled builds.
    
    Args:
        relative_path: Relative path to resource file
        
    Returns:
        Absolute filesystem path
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        # Resolved to parent of this file's directory if in config.py
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def get_icon(name: str, fallback_style: Optional[QStyle.StandardPixmap] = None) -> QIcon:
    """Load icon from assets directory or fallback to standard style icon.
    
    Args:
        name: Name of the icon file in assets/icons
        fallback_style: Optional fallback QStyle.StandardPixmap
        
    Returns:
        QIcon object
    """
    icon_path = get_resource_path(os.path.join("assets", "icons", name))
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    
    if fallback_style is None:
        fallback_style = ICON_FALLBACK_MAP.get(name, QStyle.SP_FileIcon)
        
    app = QApplication.instance()
    if app:
        return QApplication.style().standardIcon(fallback_style)
    return QIcon()

def format_error_message(error_obj: Any) -> str:
    """Format an exception, QUrl, or error object into an actionable, user-friendly message.
    
    Args:
        error_obj: Error object, exception, or QUrl
        
    Returns:
        Formatted error message string
    """
    if isinstance(error_obj, QUrl):
        err_str = error_obj.errorString() if hasattr(error_obj, 'errorString') else ""
        raw = error_obj.toString()[:80]
        if err_str:
            return f"Invalid URL ({err_str}): {raw}"
        return f"Invalid or malformed URL: {raw}"
    elif isinstance(error_obj, Exception):
        return f"{type(error_obj).__name__}: {str(error_obj)}"
    return str(error_obj)

def is_safe_local_path(path_str: str) -> bool:
    """Check whether a given path string is safe to open as a local file.
    Prevents path traversal into sensitive operating system databases and credential stores.
    
    Args:
        path_str: Local file path string
        
    Returns:
        True if safe, False if restricted or sensitive
    """
    normalized = path_str.lower().replace('/', '\\')
    for sensitive in SENSITIVE_FILE_PATTERNS:
        sensitive_norm = sensitive.lower().replace('/', '\\')
        if sensitive_norm in normalized:
            return False
    return True
