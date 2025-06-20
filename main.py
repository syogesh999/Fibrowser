import sys
import os
import json
from datetime import datetime
from PyQt5.QtCore import QUrl, Qt, QSize, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QKeySequence, QPalette, QColor, QDesktopServices, QPixmap
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineDownloadItem
from PyQt5.QtWidgets import (QMainWindow, QApplication, QStatusBar, QToolBar, QAction, 
                             QLineEdit, QTabWidget, QWidget, QVBoxLayout, QPushButton,
                             QMenu, QHBoxLayout, QLabel, QFrame, QDialog, QTextEdit,
                             QFileDialog, QProgressBar, QStyle, QShortcut, QToolButton,
                             QSizePolicy, QStackedWidget, QListWidget, QListWidgetItem)

# ----------------------------
# Constants and Configuration
# ----------------------------
DEFAULT_HOME_PAGE = "https://www.bing.com"
SEARCH_ENGINES = {
    "Google": "https://www.google.com/search?q={}",
    "Bing": "https://www.bing.com/search?q={}",
    "DuckDuckGo": "https://duckduckgo.com/?q={}",
    "YouTube": "https://www.youtube.com/results?search_query={}"
}
THEMES = {
    "Light": {
        "bg": "#ffffff",
        "fg": "#000000",
        "tab_bg": "#f1f1f1",
        "tab_active": "#ffffff",
        "url_bg": "#f1f3f4"
    },
    "Dark": {
        "bg": "#202124",
        "fg": "#e8eaed",
        "tab_bg": "#3c4043",
        "tab_active": "#202124",
        "url_bg": "#525355"
    },
    "Blue": {
        "bg": "#e3f2fd",
        "fg": "#0d47a1",
        "tab_bg": "#bbdefb",
        "tab_active": "#e3f2fd",
        "url_bg": "#bbdefb"
    }
}

class AnimatedButton(QPushButton):
    """Button with hover animation"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.PointingHandCursor)
        self._animation = QPropertyAnimation(self, b"iconSize")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.OutBack)
        
    def enterEvent(self, event):
        self._animation.setStartValue(self.iconSize())
        self._animation.setEndValue(QSize(28, 28))
        self._animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._animation.setStartValue(self.iconSize())
        self._animation.setEndValue(QSize(24, 24))
        self._animation.start()
        super().leaveEvent(event)

class DownloadItemWidget(QWidget):
    """Custom widget for download items"""
    def __init__(self, download_item, parent=None):
        super().__init__(parent)
        self.download = download_item
        
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        self.icon = QLabel()
        icon_pixmap = QStyle.standardIcon(
            QApplication.style(), 
            QStyle.SP_FileIcon
        ).pixmap(24, 24)
        self.icon.setPixmap(icon_pixmap)
        layout.addWidget(self.icon)
        
        self.filename = QLabel(os.path.basename(download_item.path()))
        layout.addWidget(self.filename, 1)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress, 2)
        
        self.speed_label = QLabel("0 KB/s")
        layout.addWidget(self.speed_label)
        
        self.download.downloadProgress.connect(self.update_progress)
        self.download.stateChanged.connect(self.update_state)
        
    def update_progress(self, bytes_received, bytes_total):
        if bytes_total > 0:
            percent = int((bytes_received / bytes_total) * 100)
            self.progress.setValue(percent)
            
            # Calculate download speed
            elapsed = self.download.startTime().secsTo(datetime.now().time())
            if elapsed > 0:
                speed = bytes_received / (elapsed * 1024)
                self.speed_label.setText(f"{speed:.1f} KB/s")
                
    def update_state(self, state):
        if state == QWebEngineDownloadItem.DownloadCompleted:
            self.progress.setValue(100)
            self.speed_label.setText("Completed")

class DownloadManager(QDialog):
    """Download manager window"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloads")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("<h2>Downloads</h2>")
        layout.addWidget(header)
        
        # Download list
        self.download_list = QListWidget()
        self.download_list.setAlternatingRowColors(True)
        layout.addWidget(self.download_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)
        
        self.clear_btn = QPushButton("Clear Completed")
        self.clear_btn.clicked.connect(self.clear_completed)
        btn_layout.addWidget(self.clear_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.hide)
        btn_layout.addWidget(self.close_btn)
        
        self.downloads = []
        
    def add_download(self, download_item):
        """Add a new download to the manager"""
        item = QListWidgetItem(self.download_list)
        widget = DownloadItemWidget(download_item, self)
        item.setSizeHint(widget.sizeHint())
        self.download_list.addItem(item)
        self.download_list.setItemWidget(item, widget)
        self.downloads.append(widget)
        
    def clear_completed(self):
        """Remove completed downloads from the list"""
        for i in range(self.download_list.count() - 1, -1, -1):
            item = self.download_list.item(i)
            widget = self.download_list.itemWidget(item)
            if widget.progress.value() == 100:
                self.download_list.takeItem(i)

class Tab(QWidget):
    """Browser tab with enhanced features"""
    def __init__(self, window, url=None, parent=None):
        super(Tab, self).__init__(parent)
        self.window = window
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # WebEngine View
        self.browser = QWebEngineView()
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self.on_download_requested)
        self.browser.setUrl(QUrl(url or DEFAULT_HOME_PAGE))
        
        # Connect signals
        self.browser.urlChanged.connect(self.update_url)
        self.browser.titleChanged.connect(self.update_title)
        self.browser.iconChanged.connect(self.update_icon)
        self.browser.loadProgress.connect(self.update_progress)
        
        layout.addWidget(self.browser)
        self.setLayout(layout)
        
        # Tab state
        self.title = "New Tab"
        self.icon = QIcon()
        
    def update_url(self, url):
        """Update address bar when URL changes"""
        self.window.URLBar.setText(url.toString())
        self.window.URLBar.setCursorPosition(0)
        self.window.log_action(f"Navigated to: {url.toString()}")
        
    def update_title(self, title):
        """Update tab title when page title changes"""
        self.title = title[:30] + "..." if len(title) > 30 else title
        index = self.window.tabs.indexOf(self)
        if index != -1:
            self.window.tabs.setTabText(index, self.title)
            
    def update_icon(self, icon):
        """Update tab icon when favicon changes"""
        self.icon = icon
        index = self.window.tabs.indexOf(self)
        if index != -1:
            self.window.tabs.setTabIcon(index, icon)
            
    def update_progress(self, progress):
        """Update progress bar during page load"""
        self.window.progress_bar.setVisible(progress < 100)
        self.window.progress_bar.setValue(progress)
        
    def on_download_requested(self, download):
        """Handle download requests"""
        download.accept()
        self.window.download_manager.add_download(download)
        self.window.download_manager.show()
        self.window.log_action(f"Download started: {os.path.basename(download.path())}")

class Window(QMainWindow):
    """Main browser window with enhanced features"""
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)
        
        # Window settings
        self.setWindowTitle("Fibrowser Pro")
        self.setMinimumSize(800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        
        # Add new tab button
        self.new_tab_btn = QToolButton()
        self.new_tab_btn.setText("+")
        self.new_tab_btn.setCursor(Qt.PointingHandCursor)
        self.new_tab_btn.clicked.connect(self.add_new_tab)
        self.tabs.setCornerWidget(self.new_tab_btn, Qt.TopRightCorner)
        
        # Add initial tab
        self.add_new_tab()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        
        # Create navigation toolbar
        self.nav_toolbar = QToolBar('Navigation Toolbar')
        self.nav_toolbar.setMovable(False)
        self.nav_toolbar.setIconSize(QSize(24, 24))
        
        # Navigation buttons with animations
        self.back_btn = AnimatedButton()
        self.back_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.back_btn.setToolTip("Back")
        self.back_btn.clicked.connect(self.navigate_back)
        
        self.forward_btn = AnimatedButton()
        self.forward_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        self.forward_btn.setToolTip("Forward")
        self.forward_btn.clicked.connect(self.navigate_forward)
        
        self.refresh_btn = AnimatedButton()
        self.refresh_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.refresh_btn.setToolTip("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_page)
        
        self.home_btn = AnimatedButton()
        self.home_btn.setIcon(self.style().standardIcon(QStyle.SP_DirHomeIcon))
        self.home_btn.setToolTip("Home")
        self.home_btn.clicked.connect(self.go_to_home)
        
        # Address bar with search suggestions
        self.URLBar = QLineEdit()
        self.URLBar.setPlaceholderText("Search or enter address")
        self.URLBar.returnPressed.connect(self.load_url)
        self.URLBar.setClearButtonEnabled(True)
        
        # Search engine selector
        self.search_combo = QToolButton()
        self.search_combo.setText("Google ▼")
        self.search_combo.setPopupMode(QToolButton.InstantPopup)
        self.search_combo.setToolTip("Select Search Engine")
        
        search_menu = QMenu()
        for engine in SEARCH_ENGINES:
            action = QAction(engine, self)
            action.triggered.connect(lambda _, e=engine: self.set_search_engine(e))
            search_menu.addAction(action)
        self.search_combo.setMenu(search_menu)
        self.current_engine = "Google"
        
        # Bookmarks button
        self.bookmarks_btn = AnimatedButton()
        self.bookmarks_btn.setIcon(self.style().standardIcon(QStyle.SP_DirLinkIcon))
        self.bookmarks_btn.setToolTip("Bookmarks")
        
        # Downloads button
        self.downloads_btn = AnimatedButton()
        self.downloads_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.downloads_btn.setToolTip("Downloads")
        self.downloads_btn.clicked.connect(self.show_downloads)
        
        # Settings button
        self.settings_btn = AnimatedButton()
        self.settings_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        
        # Add widgets to toolbar
        self.nav_toolbar.addWidget(self.back_btn)
        self.nav_toolbar.addWidget(self.forward_btn)
        self.nav_toolbar.addWidget(self.refresh_btn)
        self.nav_toolbar.addWidget(self.home_btn)
        self.nav_toolbar.addSeparator()
        self.nav_toolbar.addWidget(self.search_combo)
        self.nav_toolbar.addWidget(self.URLBar)
        self.nav_toolbar.addSeparator()
        self.nav_toolbar.addWidget(self.bookmarks_btn)
        self.nav_toolbar.addWidget(self.downloads_btn)
        self.nav_toolbar.addWidget(self.settings_btn)
        
        # Bookmarks toolbar
        self.bookmarks_toolbar = QToolBar('Bookmarks')
        self.bookmarks_toolbar.setVisible(False)
        
        # Add bookmarks
        bookmarks = {
            "Google": "https://www.google.com",
            "YouTube": "https://www.youtube.com",
            "GitHub": "https://github.com",
            "StackOverflow": "https://stackoverflow.com",
            "PyPI": "https://pypi.org"
        }
        
        for name, url in bookmarks.items():
            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFlat(True)
            btn.clicked.connect(lambda checked, u=url: self.navigate_to(u))
            self.bookmarks_toolbar.addWidget(btn)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Developer console
        self.console = QTextEdit()
        self.console.setVisible(False)
        self.console.setMinimumHeight(100)
        
        # Add widgets to main layout
        main_layout.addWidget(self.nav_toolbar)
        main_layout.addWidget(self.bookmarks_toolbar)
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.console)
        
        # Initialize managers
        self.download_manager = DownloadManager(self)
        self.log_action("Browser started")
        
        # Apply theme
        self.apply_theme("Dark")
        
        # Register shortcuts
        self.register_shortcuts()
        
    def register_shortcuts(self):
        """Register keyboard shortcuts"""
        # Tab management
        QShortcut(QKeySequence("Ctrl+T"), self, self.add_new_tab)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close_current_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self.next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self.previous_tab)
        
        # Navigation
        QShortcut(QKeySequence("Ctrl+L"), self, self.focus_address_bar)
        QShortcut(QKeySequence("F5"), self, self.refresh_page)
        QShortcut(QKeySequence("Ctrl+F5"), self, self.hard_refresh)
        QShortcut(QKeySequence("Ctrl+H"), self, self.show_history)
        
        # Developer tools
        QShortcut(QKeySequence("F12"), self, self.toggle_dev_tools)
        
    def add_new_tab(self, url=None):
        """Add a new browser tab"""
        tab = Tab(self, url)
        index = self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentIndex(index)
        
        # Set focus to address bar
        self.URLBar.setFocus()
        
        self.log_action(f"New tab opened: {index+1}")
        return tab
        
    def close_tab(self, index):
        """Close tab at specified index"""
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
            self.log_action(f"Tab closed: {index+1}")
            
    def close_current_tab(self):
        """Close the currently active tab"""
        current_index = self.tabs.currentIndex()
        self.close_tab(current_index)
        
    def next_tab(self):
        """Switch to next tab"""
        current = self.tabs.currentIndex()
        next_index = (current + 1) % self.tabs.count()
        self.tabs.setCurrentIndex(next_index)
        
    def previous_tab(self):
        """Switch to previous tab"""
        current = self.tabs.currentIndex()
        prev_index = (current - 1) % self.tabs.count()
        self.tabs.setCurrentIndex(prev_index)
        
    def tab_changed(self, index):
        """Handle tab change events"""
        if index >= 0:
            tab = self.tabs.widget(index)
            self.URLBar.setText(tab.browser.url().toString())
            self.URLBar.setCursorPosition(0)
            
    def current_tab(self):
        """Get the current active tab"""
        return self.tabs.currentWidget()
        
    def navigate_back(self):
        """Navigate back in history"""
        if self.current_tab():
            self.current_tab().browser.back()
            
    def navigate_forward(self):
        """Navigate forward in history"""
        if self.current_tab():
            self.current_tab().browser.forward()
            
    def refresh_page(self):
        """Refresh current page"""
        if self.current_tab():
            self.current_tab().browser.reload()
            
    def hard_refresh(self):
        """Hard refresh (ignore cache)"""
        if self.current_tab():
            self.current_tab().browser.reload()
            self.log_action("Hard refresh performed")
            
    def go_to_home(self):
        """Navigate to home page"""
        if self.current_tab():
            self.current_tab().browser.setUrl(QUrl(DEFAULT_HOME_PAGE))
            
    def load_url(self):
        """Load URL from address bar"""
        if self.current_tab():
            text = self.URLBar.text()
            
            # Check if it's a search query
            if ' ' in text or '.' not in text:
                search_url = SEARCH_ENGINES[self.current_engine].format(text)
                self.current_tab().browser.setUrl(QUrl(search_url))
            else:
                # Add https if missing
                if not text.startswith(('http://', 'https://')):
                    text = 'https://' + text
                self.current_tab().browser.setUrl(QUrl(text))
                
    def navigate_to(self, url):
        """Navigate to specific URL"""
        if self.current_tab():
            self.current_tab().browser.setUrl(QUrl(url))
            
    def set_search_engine(self, engine):
        """Set the default search engine"""
        self.current_engine = engine
        self.search_combo.setText(f"{engine} ▼")
        self.log_action(f"Search engine changed to: {engine}")
        
    def show_downloads(self):
        """Show download manager"""
        self.download_manager.show()
        
    def show_settings(self):
        """Show settings dialog"""
        # In a real app, this would open a settings dialog
        self.log_action("Settings opened")
        self.toggle_bookmarks_bar()
        
    def toggle_bookmarks_bar(self):
        """Toggle bookmarks toolbar visibility"""
        visible = not self.bookmarks_toolbar.isVisible()
        self.bookmarks_toolbar.setVisible(visible)
        self.log_action(f"Bookmarks bar {'shown' if visible else 'hidden'}")
        
    def focus_address_bar(self):
        """Set focus to address bar"""
        self.URLBar.setFocus()
        self.URLBar.selectAll()
        
    def toggle_dev_tools(self):
        """Toggle developer tools"""
        visible = not self.console.isVisible()
        self.console.setVisible(visible)
        self.log_action(f"Developer tools {'shown' if visible else 'hidden'}")
        
    def show_history(self):
        """Show browsing history (placeholder)"""
        self.log_action("History viewed")
        
    def apply_theme(self, theme_name):
        """Apply color theme to the browser"""
        theme = THEMES.get(theme_name, THEMES["Dark"])
        
        # Apply stylesheet
        stylesheet = f"""
            QMainWindow, QWidget {{
                background-color: {theme['bg']};
                color: {theme['fg']};
            }}
            QTabWidget::pane {{
                border: 0;
            }}
            QTabBar::tab {{
                background: {theme['tab_bg']};
                color: {theme['fg']};
                padding: 8px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {theme['tab_active']};
                border-bottom: 2px solid #1a73e8;
            }}
            QLineEdit {{
                background: {theme['url_bg']};
                border-radius: 16px;
                padding: 6px 12px;
                color: {theme['fg']};
            }}
            QToolButton {{
                background: transparent;
                border-radius: 4px;
                padding: 4px;
            }}
            QToolButton:hover {{
                background: rgba(255, 255, 255, 0.1);
            }}
            QStatusBar {{
                background: {theme['tab_bg']};
            }}
            QProgressBar {{
                border: 0;
                background: transparent;
            }}
            QProgressBar::chunk {{
                background: #1a73e8;
            }}
        """
        self.setStyleSheet(stylesheet)
        self.log_action(f"Theme applied: {theme_name}")
        
    def log_action(self, message):
        """Log actions to console and status bar"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.console.append(log_entry)
        self.status_label.setText(message)
        
        # Auto-scroll to bottom
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def contextMenuEvent(self, event):
        """Custom context menu for tabs"""
        menu = QMenu(self)
        
        # Tab actions
        new_tab_action = QAction("New Tab", self)
        new_tab_action.triggered.connect(self.add_new_tab)
        
        close_tab_action = QAction("Close Tab", self)
        close_tab_action.triggered.connect(self.close_current_tab)
        
        # Add to menu
        menu.addAction(new_tab_action)
        menu.addAction(close_tab_action)
        menu.addSeparator()
        
        # Theme selector
        theme_menu = menu.addMenu("Themes")
        for theme in THEMES:
            theme_action = QAction(theme, self)
            theme_action.triggered.connect(lambda _, t=theme: self.apply_theme(t))
            theme_menu.addAction(theme_action)
            
        menu.exec_(event.globalPos())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName('Fibrowser Pro')
    app.setWindowIcon(QIcon(app.style().standardIcon(QStyle.SP_ComputerIcon)))
    
    window = Window()
    window.show()
    
    app.exec_()