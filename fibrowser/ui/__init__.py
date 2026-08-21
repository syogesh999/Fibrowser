"""
Fibrowser Pro - UI Module
"""

__all__ = [
    "Window", 
    "Tab", 
    "DownloadManager", 
    "DownloadItemWidget", 
    "AnimatedButton", 
    "ToastNotification",
    "ShortcutManager",
    "ThemeManager",
    "SettingsDialog",
    "HistoryDialog"
]

from fibrowser.ui.widgets import AnimatedButton, ToastNotification
from fibrowser.ui.downloads import DownloadManager, DownloadItemWidget
from fibrowser.ui.shortcut_manager import ShortcutManager
from fibrowser.ui.theme_manager import ThemeManager
from fibrowser.ui.dialogs.settings_dialog import SettingsDialog
from fibrowser.ui.dialogs.history_dialog import HistoryDialog
from fibrowser.ui.tab import Tab
from fibrowser.ui.window import Window
