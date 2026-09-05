#!/usr/bin/env python3
"""
Fibrowser Pro - Professional Windows Installer
Provides a clean, multi-stage installation wizard with real progress tracking,
shortcut creation, registry uninstaller registration, and launch confirmation.
"""

import os
import sys
import shutil
import subprocess
import winreg
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPixmap
from PyQt5.QtWidgets import (QApplication, QWizard, QWizardPage, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QCheckBox, QProgressBar, QFileDialog, QMessageBox, 
                             QWidget, QStyle)

APP_NAME = "Fibrowser Pro"
APP_VERSION = "2.0.0"
DEFAULT_INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\Public"), "Programs", "Fibrowser Pro")

INSTALLER_STYLE = """
QWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QWizard {
    background-color: #0f172a;
}
QLabel {
    color: #f8fafc;
}
QLineEdit {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
}
QLineEdit:focus {
    border: 1px solid #38bdf8;
}
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: #334155;
    color: #64748b;
}
QProgressBar {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    height: 22px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #6366f1);
    border-radius: 5px;
}
QCheckBox {
    color: #f8fafc;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #1e293b;
}
QCheckBox::indicator:checked {
    background-color: #38bdf8;
    border-color: #38bdf8;
}
"""

def create_windows_shortcut(target_path: str, shortcut_path: str, icon_path: Optional[str] = None, description: str = "") -> bool:
    """Create native Windows .lnk shortcut using PowerShell COM WScript.Shell."""
    try:
        ps_script = f"""
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
        $Shortcut.TargetPath = '{target_path}'
        $Shortcut.WorkingDirectory = '{os.path.dirname(target_path)}'
        $Shortcut.Description = '{description}'
        """
        if icon_path and os.path.exists(icon_path):
            ps_script += f"\n$Shortcut.IconLocation = '{icon_path}'"
        ps_script += "\n$Shortcut.Save()"
        
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
        res = subprocess.run(cmd, capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return res.returncode == 0
    except Exception:
        return False

def register_uninstall_entry(install_dir: str, exe_path: str, icon_path: str) -> None:
    """Register application in Windows Add/Remove Programs registry."""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FibrowserPro"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, f"{APP_NAME}")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Fibrowser Team")
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, icon_path)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            uninstall_cmd = f'python "{os.path.join(install_dir, "uninstall.py")}"'
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_cmd)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass


class InstallWorker(QThread):
    """Background installation worker executing real stages."""
    progress_changed = pyqtSignal(int, str)
    install_finished = pyqtSignal(bool, str)

    def __init__(self, target_dir: str, create_desktop: bool, create_startmenu: bool, source_dir: str) -> None:
        super().__init__()
        self.target_dir = target_dir
        self.create_desktop = create_desktop
        self.create_startmenu = create_startmenu
        self.source_dir = source_dir

    def run(self) -> None:
        try:
            # Stage 1: Preparing
            self.progress_changed.emit(10, "Preparing installation environment...")
            os.makedirs(self.target_dir, exist_ok=True)
            self.msleep(300)

            # Stage 2: Copying Binaries and Core Files
            self.progress_changed.emit(25, "Extracting and installing application files...")
            
            # Check if compiled dist/FibrowserPro.exe exists or copy project source
            dist_exe = os.path.join(self.source_dir, "dist", "FibrowserPro.exe")
            target_exe = os.path.join(self.target_dir, "FibrowserPro.exe")
            
            if os.path.exists(dist_exe):
                shutil.copy2(dist_exe, target_exe)
            
            # Copy source package for full self-contained operation
            for item in ["fibrowser", "assets", "main.py", "requirements.txt", "README.md", "LICENSE"]:
                src = os.path.join(self.source_dir, item)
                dst = os.path.join(self.target_dir, item)
                if os.path.exists(src):
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
            self.msleep(300)

            # Stage 3: Installing Uninstaller
            self.progress_changed.emit(50, "Configuring uninstallation support...")
            uninstaller_src = os.path.join(self.source_dir, "uninstall.py")
            if os.path.exists(uninstaller_src):
                shutil.copy2(uninstaller_src, os.path.join(self.target_dir, "uninstall.py"))
            self.msleep(200)

            # Stage 4: Creating Shortcuts
            self.progress_changed.emit(70, "Creating Windows shortcuts...")
            icon_path = os.path.join(self.target_dir, "assets", "icons", "fibrowser.ico")
            
            # Desktop shortcut
            if self.create_desktop:
                desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
                if os.path.exists(desktop_dir):
                    shortcut_file = os.path.join(desktop_dir, f"{APP_NAME}.lnk")
                    create_windows_shortcut(target_exe, shortcut_file, icon_path, f"{APP_NAME} - Fast & Private Web Browser")

            # Start Menu shortcut
            if self.create_startmenu:
                appdata = os.environ.get("APPDATA", "")
                programs_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
                if os.path.exists(programs_dir):
                    shortcut_file = os.path.join(programs_dir, f"{APP_NAME}.lnk")
                    create_windows_shortcut(target_exe, shortcut_file, icon_path, f"{APP_NAME} - Fast & Private Web Browser")
            self.msleep(200)

            # Stage 5: Register in Windows Uninstall Registry
            self.progress_changed.emit(85, "Registering application with Windows...")
            register_uninstall_entry(self.target_dir, target_exe, icon_path)
            self.msleep(200)

            # Stage 6: Finalizing
            self.progress_changed.emit(100, "Installation complete.")
            self.msleep(200)
            self.install_finished.emit(True, "")

        except Exception as e:
            self.install_finished.emit(False, str(e))


class WelcomePage(QWizardPage):
    """Setup welcome and destination configuration page."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle(f"Install {APP_NAME}")
        self.setSubTitle("Select installation directory and shortcut preferences.")
        
        layout = QVBoxLayout()
        layout.setSpacing(14)
        
        # Branding info
        info_label = QLabel(f"<b>Welcome to the {APP_NAME} Setup Wizard</b><br>"
                            f"This will install {APP_NAME} v{APP_VERSION} on your computer.")
        layout.addWidget(info_label)
        
        layout.addSpacing(6)
        
        # Destination Folder
        dest_label = QLabel("Destination Folder:")
        layout.addWidget(dest_label)
        
        folder_layout = QHBoxLayout()
        self.dir_input = QLineEdit(DEFAULT_INSTALL_DIR)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        folder_layout.addWidget(self.dir_input)
        folder_layout.addWidget(browse_btn)
        layout.addLayout(folder_layout)
        
        layout.addSpacing(6)
        
        # Options
        self.desktop_cb = QCheckBox("Create a Desktop shortcut")
        self.desktop_cb.setChecked(True)
        layout.addWidget(self.desktop_cb)
        
        self.startmenu_cb = QCheckBox("Create a Start Menu shortcut")
        self.startmenu_cb.setChecked(True)
        layout.addWidget(self.startmenu_cb)
        
        self.launch_cb = QCheckBox("Launch Fibrowser after installation")
        self.launch_cb.setChecked(True)
        layout.addWidget(self.launch_cb)
        
        self.setLayout(layout)

    def _browse_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Folder", self.dir_input.text())
        if folder:
            self.dir_input.setText(os.path.join(folder, "Fibrowser Pro"))


class ProgressPage(QWizardPage):
    """Real-time installation progress page."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Installing Fibrowser Pro")
        self.setSubTitle("Please wait while application files and components are being installed.")
        
        layout = QVBoxLayout()
        layout.setSpacing(14)
        
        self.status_label = QLabel("Preparing installation...")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        self.is_done = False

    def isComplete(self) -> bool:
        return self.is_done


class FinishedPage(QWizardPage):
    """Installation completed page with launch option."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("✓ Fibrowser Pro Installed")
        self.setSubTitle("Installation completed successfully.")
        
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        success_label = QLabel(f"<b>{APP_NAME} is ready to use!</b><br><br>"
                               f"All required components, assets, and shortcuts have been configured.")
        layout.addWidget(success_label)
        
        prompt_label = QLabel("<b>Launch Fibrowser now?</b>")
        prompt_label.setStyleSheet("font-size: 14px; color: #38bdf8;")
        layout.addWidget(prompt_label)
        
        self.launch_checkbox = QCheckBox("Yes, launch Fibrowser Pro")
        self.launch_checkbox.setChecked(True)
        layout.addWidget(self.launch_checkbox)
        
        self.setLayout(layout)


class FibrowserInstallerWizard(QWizard):
    """Main wizard coordinator for setup."""
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} Setup")
        self.setStyleSheet(INSTALLER_STYLE)
        self.setFixedSize(540, 420)
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "fibrowser.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.welcome_page = WelcomePage()
        self.progress_page = ProgressPage()
        self.finished_page = FinishedPage()
        
        self.addPage(self.welcome_page)
        self.addPage(self.progress_page)
        self.addPage(self.finished_page)
        
        self.currentIdChanged.connect(self._on_page_changed)
        self.worker: Optional[InstallWorker] = None

    def _on_page_changed(self, page_id: int) -> None:
        if self.page(page_id) == self.progress_page:
            self.button(QWizard.BackButton).setEnabled(False)
            self.button(QWizard.NextButton).setEnabled(False)
            self._start_installation()

    def _start_installation(self) -> None:
        target_dir = self.welcome_page.dir_input.text().strip()
        desktop = self.welcome_page.desktop_cb.isChecked()
        startmenu = self.welcome_page.startmenu_cb.isChecked()
        source_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.worker = InstallWorker(target_dir, desktop, startmenu, source_dir)
        self.worker.progress_changed.connect(self._update_progress)
        self.worker.install_finished.connect(self._on_install_finished)
        self.worker.start()

    def _update_progress(self, val: int, msg: str) -> None:
        self.progress_page.progress_bar.setValue(val)
        self.progress_page.status_label.setText(msg)

    def _on_install_finished(self, success: bool, err_msg: str) -> None:
        if success:
            self.progress_page.is_done = True
            self.next()
        else:
            QMessageBox.critical(self, "Installation Failed", 
                f"Installation could not be completed.\n\nReason:\n{err_msg}\n\nPlease try again or select another destination folder.")
            self.button(QWizard.BackButton).setEnabled(True)
            self.back()

    def accept(self) -> None:
        """Handle wizard completion and optional app launch."""
        if self.finished_page.launch_checkbox.isChecked():
            target_dir = self.welcome_page.dir_input.text().strip()
            target_exe = os.path.join(target_dir, "FibrowserPro.exe")
            
            if os.path.exists(target_exe):
                try:
                    subprocess.Popen([target_exe], cwd=target_dir)
                except Exception:
                    pass
            else:
                main_py = os.path.join(target_dir, "main.py")
                if os.path.exists(main_py):
                    try:
                        subprocess.Popen([sys.executable, main_py], cwd=target_dir)
                    except Exception:
                        pass
        super().accept()


def main() -> int:
    app = QApplication(sys.argv)
    wizard = FibrowserInstallerWizard()
    wizard.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
