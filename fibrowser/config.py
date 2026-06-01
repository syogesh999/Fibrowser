import os
import sys
from pathlib import Path
from typing import Dict
from dataclasses import dataclass
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStyle

DEFAULT_HOME_PAGE = "https://www.bing.com"
APP_NAME = "Fibrowser Pro"
APP_VERSION = "2.0.0"
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 700

SEARCH_ENGINES: Dict[str, str] = {
    "Google": "https://www.google.com/search?q={}",
    "Bing": "https://www.bing.com/search?q={}",
    "DuckDuckGo": "https://duckduckgo.com/?q={}",
    "YouTube": "https://www.youtube.com/results?search_query={}",
    "Wikipedia": "https://en.wikipedia.org/w/index.php?search={}"
}

@dataclass
class Theme:
    """Theme color configuration"""
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

# Helper to find resources bundled with PyInstaller
def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Resolved to parent of this file's directory if in config.py
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def get_icon(name: str, fallback_style: QStyle.StandardPixmap) -> QIcon:
    """Load icon from assets directory or fallback to standard style icon"""
    icon_path = get_resource_path(os.path.join("assets", "icons", name))
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    return QApplication.style().standardIcon(fallback_style)
