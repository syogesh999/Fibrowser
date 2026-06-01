import logging
from typing import Optional, List, TYPE_CHECKING
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from fibrowser.core.page import BrowserPage

if TYPE_CHECKING:
    from fibrowser.ui.window import Window

logger = logging.getLogger(__name__)

class Tab(QWidget):
    """Browser tab with private browsing support and modern structure"""
    
    def __init__(self, window: 'Window', url: Optional[str] = None, is_private: bool = False, parent=None):
        """Initialize browser tab
        
        Args:
            window: Parent window instance
            url: Initial URL to load
            is_private: Set to True for an off-the-record profile (Private Mode)
            parent: Parent widget
        """
        super(Tab, self).__init__(parent)
        self.window = window
        self.is_private = is_private
        self.tab_history: List[str] = []
        self.progress = 100
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # WebEngine View
        self.browser = QWebEngineView()
        
        if self.is_private:
            # Use custom off-the-record profile managed centrally by the Window
            profile = self.window.get_private_profile()
        else:
            profile = QWebEngineProfile.defaultProfile()
        
        # Set JavaScript settings for better performance
        settings = profile.settings()
        settings.setAttribute(settings.JavascriptEnabled, self.window.js_enabled if hasattr(self.window, 'js_enabled') else True)
        
        # Create custom page with error handling
        custom_page = BrowserPage(profile, window=self.window)
        self.browser.setPage(custom_page)
        
        # Load initial URL
        initial_url = url or self.window.homepage
        self.browser.setUrl(QUrl(initial_url))
        
        # Connect signals
        self.browser.urlChanged.connect(self.update_url)
        self.browser.titleChanged.connect(self.update_title)
        self.browser.iconChanged.connect(self.update_icon)
        self.browser.loadProgress.connect(self.update_progress)
        self.browser.loadFinished.connect(self.on_load_finished)
        
        layout.addWidget(self.browser)
        self.setLayout(layout)
        
        # Tab metadata
        self.title = "New Tab"
        self.icon = QIcon()
        self.favicon_url: Optional[str] = None
        
    def update_url(self, url: QUrl) -> None:
        """Update address bar when URL changes
        
        Args:
            url: New URL
        """
        url_str = url.toString()
        self.tab_history.append(url_str)
        
        if self.window.current_tab() == self:
            if hasattr(self.window, 'URLBar') and self.window.URLBar:
                self.window.URLBar.setText(url_str)
                self.window.URLBar.setCursorPosition(0)
            if hasattr(self.window, 'update_bookmark_button_state'):
                self.window.update_bookmark_button_state()
        
        try:
            self.window.log_action(f"Navigated to: {url_str[:60]}...")
        except Exception:
            pass
        
    def update_title(self, title: str) -> None:
        """Update tab title when page title changes
        
        Args:
            title: New page title
        """
        # Truncate long titles
        self.title = title[:30] + "..." if len(title) > 30 else title or "New Tab"
        
        if self.window.tabs:
            index = self.window.tabs.indexOf(self)
            if index != -1:
                prefix = "🔒 " if self.is_private else ""
                self.window.tabs.setTabText(index, prefix + self.title)
                if self.is_private:
                    self.window.tabs.tabBar().setTabTextColor(index, QColor("#d9534f"))
            
    def update_icon(self, icon: QIcon) -> None:
        """Update tab icon when favicon changes
        
        Args:
            icon: New favicon icon
        """
        self.icon = icon
        if self.window.tabs:
            index = self.window.tabs.indexOf(self)
            if index != -1:
                self.window.tabs.setTabIcon(index, icon)
            
    def update_progress(self, progress: int) -> None:
        """Update progress bar during page load
        
        Args:
            progress: Load progress percentage (0-100)
        """
        self.progress = progress
        if self.window.current_tab() == self:
            if hasattr(self.window, 'progress_bar') and self.window.progress_bar:
                self.window.progress_bar.setVisible(progress < 100)
                self.window.progress_bar.setValue(progress)

    def on_load_finished(self, ok: bool) -> None:
        """Inject Web Dark Mode automatically if active on navigation"""
        if ok and hasattr(self.window, 'web_dark_mode_active') and self.window.web_dark_mode_active:
            js = """
            (function() {
                var el = document.getElementById('fibrowser-dark-mode');
                if (!el) {
                    var style = document.createElement('style');
                    style.id = 'fibrowser-dark-mode';
                    style.innerHTML = 'html { filter: invert(1) hue-rotate(180deg) !important; background-color: #111 !important; } img, video, iframe, canvas { filter: invert(1) hue-rotate(180deg) !important; }';
                    document.head.appendChild(style);
                }
            })();
            """
            self.browser.page().runJavaScript(js)
