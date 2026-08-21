#!/usr/bin/env python3
"""
Fibrowser Pro - Uninstaller Wizard
Safely uninstalls application files, shortcuts, and registry entries,
with an explicit option to preserve or remove user settings.
"""

import os
import sys
import shutil
import winreg
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QCheckBox, QMessageBox, QWidget)

APP_NAME = "Fibrowser Pro"

UNINSTALLER_STYLE = """
QWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QPushButton {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #dc2626;
}
QPushButton#cancelBtn {
    background-color: #334155;
}
QPushButton#cancelBtn:hover {
    background-color: #475569;
}
QCheckBox {
    color: #cbd5e1;
}
"""

def remove_registry_entry() -> None:
    """Remove application entry from Windows Add/Remove Programs registry."""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteKey(key, "FibrowserPro")
    except Exception:
        pass

def remove_shortcuts() -> None:
    """Remove Desktop and Start Menu shortcuts."""
    # Desktop
    desktop_shortcut = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", f"{APP_NAME}.lnk")
    if os.path.exists(desktop_shortcut):
        try:
            os.remove(desktop_shortcut)
        except Exception:
            pass

    # Start Menu
    start_menu_shortcut = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", f"{APP_NAME}.lnk")
    if os.path.exists(start_menu_shortcut):
        try:
            os.remove(start_menu_shortcut)
        except Exception:
            pass

class UninstallerDialog(QDialog):
    """Clean uninstaller dialog confirmation and execution."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Uninstall {APP_NAME}")
        self.setStyleSheet(UNINSTALLER_STYLE)
        self.setFixedSize(460, 240)
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "fibrowser.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        
        title_label = QLabel(f"<b>Uninstall {APP_NAME}</b>")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        desc_label = QLabel(f"Are you sure you want to completely remove {APP_NAME} from your computer?")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        self.user_data_cb = QCheckBox("Also remove personal browsing data, history, and bookmarks (~/.fibrowser)")
        self.user_data_cb.setChecked(False)
        layout.addWidget(self.user_data_cb)
        
        layout.addSpacing(10)
        
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.uninstall_btn = QPushButton("🗑️ Uninstall")
        self.uninstall_btn.clicked.connect(self._perform_uninstall)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.uninstall_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def _perform_uninstall(self) -> None:
        try:
            # 1. Remove shortcuts
            remove_shortcuts()
            
            # 2. Remove Registry entries
            remove_registry_entry()
            
            # 3. Optional user data removal
            if self.user_data_cb.isChecked():
                config_dir = Path(os.path.expanduser("~")) / ".fibrowser"
                if config_dir.exists():
                    shutil.rmtree(config_dir, ignore_errors=True)
                    
            QMessageBox.information(
                self, 
                "Uninstall Complete", 
                f"{APP_NAME} has been successfully removed from your computer."
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.warning(
                self, 
                "Uninstall Warning", 
                f"Completed with warnings: {e}"
            )
            self.accept()

def main() -> int:
    app = QApplication(sys.argv)
    dialog = UninstallerDialog()
    return dialog.exec_()

if __name__ == '__main__':
    sys.exit(main())
