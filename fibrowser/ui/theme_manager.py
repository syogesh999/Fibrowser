import logging
from typing import Optional, Any
from fibrowser.config import THEMES, Theme

logger = logging.getLogger(__name__)

class ThemeManager:
    """Manager for generating theme stylesheets and validating theme configurations."""
    
    @staticmethod
    def validate_theme_name(theme_name: str) -> str:
        """Validate whether theme_name exists in THEMES, returning 'Dark' as fallback.
        
        Args:
            theme_name: Name of the theme to validate
            
        Returns:
            Validated theme name string
        """
        if theme_name in THEMES:
            return theme_name
        logger.warning(f"Theme '{theme_name}' not found, falling back to 'Dark'")
        return "Dark"

    @staticmethod
    def get_accent_color(theme_name: str) -> str:
        """Get the accent color hex string for a given theme name."""
        valid_name = ThemeManager.validate_theme_name(theme_name)
        return THEMES[valid_name].accent

    @staticmethod
    def generate_stylesheet(theme_name: str) -> str:
        """Generate comprehensive Qt stylesheet for the entire application interface.
        
        Args:
            theme_name: Name of theme defined in config.THEMES
            
        Returns:
            Complete CSS stylesheet string for QMainWindow and child widgets
        """
        valid_name = ThemeManager.validate_theme_name(theme_name)
        theme: Theme = THEMES[valid_name]
        
        return f"""
            /* Global Base Typography & Elements */
            QWidget {{
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                font-size: 13px;
            }}
            
            QMainWindow {{
                background-color: {theme.bg};
            }}
            
            /* Dialogs Styling */
            QDialog {{
                background-color: {theme.bg};
                color: {theme.fg};
                border: 1px solid {theme.hover};
            }}
            
            /* Tooltips */
            QToolTip {{
                background-color: {theme.tab_bg};
                color: {theme.fg};
                border: 1px solid {theme.accent};
                border-radius: 4px;
                padding: 5px;
            }}
            
            /* Tab Widget & Bar */
            QTabWidget::pane {{
                border: none;
                margin: 0px;
            }}
            
            QTabBar::tab {{
                background: {theme.tab_bg};
                color: {theme.fg};
                padding: 6px 14px;
                margin: 4px 2px;
                border-radius: 12px;
                border: 1px solid {theme.hover};
            }}
            
            QTabBar::tab:hover {{
                background: {theme.hover};
            }}
            
            QTabBar::tab:selected {{
                background: {theme.tab_active};
                border: 1px solid {theme.accent};
                color: {theme.fg};
            }}
            
            QTabBar QToolButton {{
                background: {theme.tab_bg};
                border-radius: 12px;
                margin: 4px;
                width: 24px;
                height: 24px;
                color: {theme.fg};
            }}
            
            QTabBar QToolButton:hover {{
                background: {theme.hover};
            }}
            
            /* Address Bar */
            QLineEdit {{
                background: {theme.url_bg};
                border: 1px solid {theme.hover};
                border-radius: 16px;
                padding: 6px 12px;
                color: {theme.fg};
                selection-background-color: {theme.accent};
            }}
            
            QLineEdit:focus {{
                border: 1px solid {theme.accent};
                background: {theme.bg};
            }}
            
            /* Search / Engine Combo Box */
            QComboBox {{
                background: {theme.url_bg};
                border: 1px solid {theme.hover};
                border-radius: 16px;
                padding: 6px 12px;
                color: {theme.fg};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            QComboBox QAbstractItemView {{
                background: {theme.bg};
                color: {theme.fg};
                selection-background-color: {theme.accent};
                selection-color: {theme.bg};
                border: 1px solid {theme.hover};
            }}
            
            /* Toolbars */
            QToolBar {{
                border: none;
                background: {theme.tab_bg};
                spacing: 4px;
                padding: 4px;
            }}
            
            QToolBar::separator {{
                width: 1px;
                background-color: {theme.hover};
                margin: 6px 4px;
            }}
            
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
                color: {theme.fg};
            }}
            
            QToolButton:hover {{
                background: {theme.hover};
            }}
            
            QToolButton:pressed {{
                background: {theme.accent};
            }}
            
            /* Circular Toolbar Navigation Buttons */
            QToolBar QPushButton {{
                background: transparent;
                border: none;
                border-radius: 18px;
                padding: 0px;
                color: {theme.fg};
            }}
            
            QToolBar QPushButton:hover {{
                background: {theme.hover};
            }}
            
            QToolBar QPushButton:pressed {{
                background: {theme.accent};
                color: {theme.bg};
            }}
            
            /* Dialog & General PushButtons */
            QPushButton {{
                background: {theme.tab_bg};
                color: {theme.fg};
                border: 1px solid {theme.hover};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background: {theme.hover};
            }}
            
            QPushButton:pressed {{
                background: {theme.accent};
                color: {theme.bg};
            }}
            
            /* Status Bar */
            QStatusBar {{
                background: {theme.bg};
                color: {theme.fg};
                border-top: 1px solid {theme.hover};
            }}
            
            /* Loading Progress Bar */
            QProgressBar {{
                border: none;
                background: transparent;
                height: 3px;
            }}
            
            QProgressBar::chunk {{
                background: {theme.accent};
                border-radius: 1px;
            }}
            
            /* List Widget Items & Download Bars */
            QListWidget {{
                background: {theme.bg};
                color: {theme.fg};
                border: 1px solid {theme.hover};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QListWidget::item {{
                padding: 6px;
                border-radius: 4px;
            }}
            
            QListWidget::item:hover {{
                background: {theme.hover};
            }}
            
            QListWidget::item:selected {{
                background: {theme.accent};
                color: {theme.bg};
            }}
            
            QListWidget QProgressBar {{
                border: 1px solid {theme.hover};
                background-color: {theme.url_bg};
                height: 14px;
                text-align: center;
                font-size: 10px;
                color: {theme.fg};
                border-radius: 7px;
            }}
            
            QListWidget QProgressBar::chunk {{
                background: {theme.accent};
                border-radius: 6px;
            }}
            
            /* Text Edit / Console */
            QPlainTextEdit, QTextEdit {{
                background: {theme.tab_bg};
                color: {theme.fg};
                border: 1px solid {theme.hover};
                border-radius: 4px;
            }}
            
            /* Context Menus */
            QMenu {{
                background: {theme.bg};
                color: {theme.fg};
                border: 1px solid {theme.hover};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
            }}
            
            QMenu::item:selected {{
                background: {theme.accent};
                color: {theme.bg};
            }}
            
            /* Scrollbars */
            QScrollBar:vertical {{
                border: none;
                background: {theme.tab_bg};
                width: 10px;
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background: {theme.url_bg};
                min-height: 20px;
                border-radius: 5px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: {theme.accent};
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            
            QScrollBar:horizontal {{
                border: none;
                background: {theme.tab_bg};
                height: 10px;
                margin: 0px;
            }}
            
            QScrollBar::handle:horizontal {{
                background: {theme.url_bg};
                min-width: 20px;
                border-radius: 5px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background: {theme.accent};
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
            }}
            
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """

    @staticmethod
    def apply_to_window(window: Any, theme_name: str) -> str:
        """Apply theme stylesheet to window and validate name with notifications.
        
        Args:
            window: Target QMainWindow instance
            theme_name: Theme name to apply
            
        Returns:
            The active applied theme name
        """
        valid_name = ThemeManager.validate_theme_name(theme_name)
        if valid_name != theme_name:
            if hasattr(window, 'show_toast'):
                window.show_toast(f"Theme '{theme_name}' not found. Using Dark theme.")
            if hasattr(window, '_save_settings'):
                window.current_theme = valid_name
                window._save_settings()

        stylesheet = ThemeManager.generate_stylesheet(valid_name)
        window.setStyleSheet(stylesheet)
        return valid_name
