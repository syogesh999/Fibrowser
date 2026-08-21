import logging
from typing import Any, Optional
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QComboBox, QLineEdit, QCheckBox, QPushButton, 
                             QLabel, QMessageBox, QWidget)
from PyQt5.QtWebEngineWidgets import QWebEngineProfile
from fibrowser.config import (DEFAULT_HOME_PAGE, APP_NAME, APP_VERSION, 
                              SEARCH_ENGINES, THEMES)

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """Browser settings and preferences configuration dialog."""
    
    def __init__(self, window: Any, parent: Optional[QWidget] = None) -> None:
        """Initialize settings dialog.
        
        Args:
            window: Parent MainWindow reference
            parent: Parent widget
        """
        super().__init__(parent or window)
        self.window = window
        self.setWindowTitle("⚙️ Settings")
        self.setMinimumSize(460, 430)
        
        self.original_theme = getattr(window, 'current_theme', 'Dark')
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize settings dialog UI components."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(self.original_theme)
        form_layout.addRow("Theme:", self.theme_combo)
        
        # Homepage input
        self.homepage_edit = QLineEdit()
        self.homepage_edit.setText(getattr(self.window, 'homepage', DEFAULT_HOME_PAGE))
        form_layout.addRow("Homepage:", self.homepage_edit)
        
        # Search Engine selector
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(list(SEARCH_ENGINES.keys()))
        self.engine_combo.setCurrentText(getattr(self.window, 'current_engine', "Google"))
        form_layout.addRow("Search Engine:", self.engine_combo)
        
        # Default Zoom selector
        self.zoom_combo = QComboBox()
        zoom_options = ["50%", "75%", "100%", "125%", "150%", "200%"]
        self.zoom_combo.addItems(zoom_options)
        curr_zoom = getattr(self.window, 'default_zoom', 1.0)
        zoom_val_str = f"{int(curr_zoom * 100)}%"
        if zoom_val_str in zoom_options:
            self.zoom_combo.setCurrentText(zoom_val_str)
        else:
            self.zoom_combo.setCurrentText("100%")
        form_layout.addRow("Default Zoom:", self.zoom_combo)
        
        # Javascript checkbox
        self.js_cb = QCheckBox("Enable JavaScript (faster rendering)")
        self.js_cb.setChecked(getattr(self.window, 'js_enabled', True))
        form_layout.addRow("Security:", self.js_cb)
        
        # Clear on Exit checkbox
        self.exit_cb = QCheckBox("Clear browsing history on exit")
        self.exit_cb.setChecked(getattr(self.window, 'clear_on_exit', False))
        form_layout.addRow("Privacy:", self.exit_cb)
        
        # Clear Cache Button
        clear_cache_btn = QPushButton("🧹 Clear Browser Cache Now")
        clear_cache_btn.clicked.connect(self._clear_cache_action)
        form_layout.addRow("Maintenance:", clear_cache_btn)
        
        form_layout.addRow("", QLabel(""))
        
        # About section
        info = QLabel(
            f"<b>{APP_NAME} v{APP_VERSION}</b><br>"
            f"A modern, secure, and feature-rich PyQt5 browser."
        )
        form_layout.addRow("About:", info)
        
        # Buttons layout
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("✓ Save")
        self.cancel_btn = QPushButton("✕ Cancel")
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # Live theme preview
        self.theme_combo.currentTextChanged.connect(self._preview_theme)
        self.save_btn.clicked.connect(self._save_settings)
        self.cancel_btn.clicked.connect(self._cancel_settings)

    def _preview_theme(self, theme_name: str) -> None:
        """Preview selected theme live."""
        if hasattr(self.window, 'apply_theme'):
            self.window.apply_theme(theme_name)

    def _clear_cache_action(self) -> None:
        """Clear default and private profile HTTP caches."""
        try:
            QWebEngineProfile.defaultProfile().clearHttpCache()
            if hasattr(self.window, '_private_profile') and self.window._private_profile:
                self.window._private_profile.clearHttpCache()
            QMessageBox.information(self, "Cache Cleared", "Browser cache cleared successfully.")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            QMessageBox.warning(self, "Cache Error", f"Could not clear cache: {e}")

    def _save_settings(self) -> None:
        """Persist settings to window state and file."""
        try:
            self.window.homepage = self.homepage_edit.text().strip() or DEFAULT_HOME_PAGE
            self.window.current_engine = self.engine_combo.currentText()
            self.window.current_theme = self.theme_combo.currentText()
            
            # Zoom parsing
            zoom_text = self.zoom_combo.currentText().replace("%", "")
            try:
                self.window.default_zoom = float(zoom_text) / 100.0
            except ValueError:
                self.window.default_zoom = 1.0
                
            self.window.js_enabled = self.js_cb.isChecked()
            self.window.clear_on_exit = self.exit_cb.isChecked()
            
            # Apply JS settings to default profile and private profile
            default_settings = QWebEngineProfile.defaultProfile().settings()
            default_settings.setAttribute(
                default_settings.JavascriptEnabled, self.window.js_enabled
            )
            if hasattr(self.window, '_private_profile') and self.window._private_profile:
                priv_settings = self.window._private_profile.settings()
                priv_settings.setAttribute(
                    priv_settings.JavascriptEnabled, self.window.js_enabled
                )
                
            if hasattr(self.window, 'apply_theme'):
                self.window.apply_theme(self.window.current_theme)
            if hasattr(self.window, 'set_search_engine'):
                self.window.set_search_engine(self.window.current_engine)
            if hasattr(self.window, '_save_settings'):
                self.window._save_settings()
                
            if hasattr(self.window, 'log_action'):
                self.window.log_action("⚙️ Settings saved successfully")
            if hasattr(self.window, 'show_toast'):
                self.window.show_toast("Settings saved successfully")
                
            self.accept()
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {e}")

    def _cancel_settings(self) -> None:
        """Cancel and revert live theme preview if changed."""
        if self.theme_combo.currentText() != self.original_theme:
            if hasattr(self.window, 'apply_theme'):
                self.window.apply_theme(self.original_theme)
        self.reject()
