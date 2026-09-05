import logging
from typing import Any, Optional
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QComboBox, QLineEdit, QPushButton, QLabel, QWidget)
from fibrowser.config import (DEFAULT_HOME_PAGE, DEFAULT_SEARCH_ENGINE, 
                              APP_NAME, APP_VERSION, SEARCH_ENGINES, THEMES, get_icon)

logger = logging.getLogger(__name__)

class WelcomeDialog(QDialog):
    """Lightweight and unintrusive first-run welcome dialog to configure initial preferences."""
    
    def __init__(self, window: Any, parent: Optional[QWidget] = None) -> None:
        """Initialize welcome dialog.
        
        Args:
            window: Parent MainWindow reference
            parent: Optional parent widget
        """
        super().__init__(parent or window)
        self.window = window
        self.setWindowTitle(f"Welcome to {APP_NAME}")
        self.setWindowIcon(get_icon("fibrowser.ico"))
        self.setMinimumSize(480, 400)
        
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize welcome dialog UI layout."""
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        self.setLayout(layout)
        
        # Header with branding
        header_label = QLabel(f"<b>Welcome to {APP_NAME} v{APP_VERSION}</b>")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        self.sub_label = QLabel("Your private, fast, and modern desktop web browser.")
        self.sub_label.setObjectName("welcomeSubtitle")
        self.sub_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.sub_label)
        
        layout.addSpacing(6)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        layout.addLayout(form_layout)
        
        # Homepage option
        self.homepage_combo = QComboBox()
        self.homepage_combo.addItems(["MSN (Default)", "Bing", "Google", "Custom URL"])
        self.homepage_combo.setCurrentIndex(0)
        form_layout.addRow("Homepage:", self.homepage_combo)
        
        self.custom_homepage_edit = QLineEdit()
        self.custom_homepage_edit.setPlaceholderText("https://example.com")
        self.custom_homepage_edit.setVisible(False)
        form_layout.addRow("Custom URL:", self.custom_homepage_edit)
        
        self.homepage_combo.currentTextChanged.connect(self._on_homepage_changed)
        
        # Default Search Engine
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(list(SEARCH_ENGINES.keys()))
        self.engine_combo.setCurrentText(DEFAULT_SEARCH_ENGINE)
        form_layout.addRow("Search Engine:", self.engine_combo)
        
        # Initial Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText("Dark")
        form_layout.addRow("Color Theme:", self.theme_combo)
        
        # Live preview theme on change
        self.theme_combo.currentTextChanged.connect(self._preview_theme)
        
        layout.addSpacing(10)
        
        # Button layout
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("🚀 Get Started")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet("padding: 8px 24px; font-weight: bold; font-size: 14px;")
        self.start_btn.clicked.connect(self._save_and_start)
        btn_layout.addStretch()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_homepage_changed(self, text: str) -> None:
        """Handle custom URL input visibility."""
        self.custom_homepage_edit.setVisible(text == "Custom URL")

    def _preview_theme(self, theme_name: str) -> None:
        """Preview selected theme."""
        if hasattr(self.window, 'apply_theme'):
            self.window.apply_theme(theme_name)

    def _save_and_start(self) -> None:
        """Apply preferences and mark first run completed."""
        choice = self.homepage_combo.currentText()
        if choice == "MSN (Default)":
            homepage_url = "https://www.msn.com"
        elif choice == "Bing":
            homepage_url = "https://www.bing.com"
        elif choice == "Google":
            homepage_url = "https://www.google.com"
        else:
            homepage_url = self.custom_homepage_edit.text().strip() or "https://www.msn.com"
            
        self.window.homepage = homepage_url
        self.window.current_engine = self.engine_combo.currentText()
        self.window.current_theme = self.theme_combo.currentText()
        self.window.first_run_completed = True
        
        if hasattr(self.window, 'apply_theme'):
            self.window.apply_theme(self.window.current_theme)
        if hasattr(self.window, 'set_search_engine'):
            self.window.set_search_engine(self.window.current_engine)
        if hasattr(self.window, '_save_settings'):
            self.window._save_settings()
            
        # Navigate current tab to chosen homepage if still at default or empty
        current = self.window.current_tab()
        if current and hasattr(current, 'browser'):
            curr_url = current.browser.url().toString()
            if not curr_url or curr_url == "about:blank" or "msn.com" in curr_url or "bing.com" in curr_url:
                self.window.navigate_to(homepage_url)
                
        self.accept()
