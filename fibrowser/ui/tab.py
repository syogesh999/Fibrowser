import logging
from typing import Optional, List, TYPE_CHECKING, Any
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from fibrowser.core.page import BrowserPage

if TYPE_CHECKING:
    from fibrowser.ui.window import Window

logger = logging.getLogger(__name__)

class Tab(QWidget):
    """Browser tab encapsulating a QWebEngineView, navigation history, progress tracking, audio state, and pinning."""
    
    def __init__(self, window: 'Window', url: Optional[str] = None, is_private: bool = False, parent: Optional[QWidget] = None) -> None:
        """Initialize browser tab.
        
        Args:
            window: Parent MainWindow instance
            url: Initial URL to navigate to
            is_private: Set to True for an isolated off-the-record profile (Private Mode)
            parent: Optional parent widget
        """
        super(Tab, self).__init__(parent)
        self.window = window
        self.is_private = is_private
        self.is_pinned = False
        self.is_muted = False
        self.tab_history: List[str] = []
        self.progress: int = 100
        
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
        
        # Set JavaScript settings
        settings = profile.settings()
        js_setting = getattr(self.window, 'js_enabled', True)
        settings.setAttribute(settings.JavascriptEnabled, js_setting)
        
        # Create custom page with error handling
        custom_page = BrowserPage(profile, window=self.window)
        self.browser.setPage(custom_page)
        
        # Load initial URL
        initial_url = url or getattr(self.window, 'homepage', "https://www.msn.com")
        self.browser.setUrl(QUrl(initial_url))
        
        # Connect signals
        self.browser.urlChanged.connect(self.update_url)
        self.browser.titleChanged.connect(self.update_title)
        self.browser.iconChanged.connect(self.update_icon)
        self.browser.loadProgress.connect(self.update_progress)
        self.browser.loadFinished.connect(self.on_load_finished)
        self.browser.page().recentlyAudibleChanged.connect(self.on_audio_state_changed)
        
        layout.addWidget(self.browser)
        self.setLayout(layout)
        
        # Tab metadata
        self.title: str = "New Tab"
        self.icon: QIcon = QIcon()
        self.favicon_url: Optional[str] = None

    def set_muted(self, muted: bool) -> None:
        """Mute or unmute tab audio.
        
        Args:
            muted: True to mute audio
        """
        self.is_muted = muted
        self.browser.page().setAudioMuted(muted)
        self.update_tab_bar_display()

    def set_pinned(self, pinned: bool) -> None:
        """Pin or unpin tab.
        
        Args:
            pinned: True to pin tab
        """
        self.is_pinned = pinned
        self.update_tab_bar_display()
        
    def on_audio_state_changed(self, recently_audible: bool) -> None:
        """Handle webpage playing sound indicator."""
        self.update_tab_bar_display()
        
    def update_url(self, url: QUrl) -> None:
        """Update address bar and action log when URL changes.
        
        Args:
            url: New QUrl instance
        """
        url_str = url.toString()
        self.tab_history.append(url_str)
        
        if hasattr(self.window, 'current_tab') and self.window.current_tab() == self:
            if hasattr(self.window, 'URLBar') and self.window.URLBar:
                self.window.URLBar.setText(url_str)
                self.window.URLBar.setCursorPosition(0)
            if hasattr(self.window, 'update_bookmark_button_state'):
                self.window.update_bookmark_button_state()
        
        try:
            if hasattr(self.window, 'log_action'):
                self.window.log_action(f"Navigated to: {url_str}")
        except Exception:
            pass
        
    def update_title(self, title: str) -> None:
        """Update tab title when page title changes.
        
        Args:
            title: New page title string
        """
        # Truncate long titles for tab bar display
        self.title = title[:30] + "..." if len(title) > 30 else title or "New Tab"
        self.update_tab_bar_display()
            
    def update_tab_bar_display(self) -> None:
        """Sync tab title with privacy, audio, and pinned state."""
        if hasattr(self.window, 'tabs') and self.window.tabs:
            index = self.window.tabs.indexOf(self)
            if index != -1:
                prefixes = []
                if self.is_pinned:
                    prefixes.append("📌")
                if self.is_private:
                    prefixes.append("🔒")
                if self.is_muted:
                    prefixes.append("🔇")
                elif self.browser.page().recentlyAudible():
                    prefixes.append("🔊")
                    
                prefix_str = " ".join(prefixes) + " " if prefixes else ""
                display_title = prefix_str + (self.title if not self.is_pinned else "")
                self.window.tabs.setTabText(index, display_title.strip())
                if self.is_private:
                    self.window.tabs.tabBar().setTabTextColor(index, QColor("#d9534f"))

    def update_icon(self, icon: QIcon) -> None:
        """Update tab icon when favicon changes.
        
        Args:
            icon: New favicon QIcon
        """
        self.icon = icon
        if hasattr(self.window, 'tabs') and self.window.tabs:
            index = self.window.tabs.indexOf(self)
            if index != -1:
                self.window.tabs.setTabIcon(index, icon)
            
    def update_progress(self, progress: int) -> None:
        """Update progress bar during page load.
        
        Args:
            progress: Load progress percentage (0-100)
        """
        self.progress = progress
        if hasattr(self.window, 'current_tab') and self.window.current_tab() == self:
            if hasattr(self.window, 'progress_bar') and self.window.progress_bar:
                self.window.progress_bar.setVisible(progress < 100)
                self.window.progress_bar.setValue(progress)

    def on_load_finished(self, ok: bool) -> None:
        """Inject Web Dark Mode stylesheet cleanly if active on navigation.
        
        Args:
            ok: Whether load completed successfully
        """
        if ok and hasattr(self.window, 'web_dark_mode_active') and self.window.web_dark_mode_active:
            js = """
            (function() {
                var el = document.getElementById('fibrowser-dark-mode');
                if (!el) {
                    var style = document.createElement('style');
                    style.id = 'fibrowser-dark-mode';
                    style.innerHTML = `
                        html { 
                            filter: invert(0.92) hue-rotate(180deg) !important; 
                            background-color: #121212 !important; 
                        }
                        img, video, canvas, iframe, picture, svg { 
                            filter: invert(1.08) hue-rotate(180deg) !important; 
                        }
                    `;
                    document.head.appendChild(style);
                }
            })();
            """
            self.browser.page().runJavaScript(js)
