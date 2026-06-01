import os
import json
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

from PyQt5.QtCore import QUrl, Qt, QSize, QTimer, QPoint
from PyQt5.QtGui import QIcon, QKeySequence, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineDownloadItem, QWebEnginePage
from PyQt5.QtWidgets import (QMainWindow, QStatusBar, QToolBar, QAction, 
                             QLineEdit, QTabWidget, QWidget, QVBoxLayout, QPushButton,
                             QMenu, QHBoxLayout, QLabel, QDialog,
                             QFileDialog, QProgressBar, QStyle, QShortcut, QToolButton,
                             QListWidget, QListWidgetItem, QComboBox, QCheckBox, QFormLayout,
                             QMessageBox, QPlainTextEdit, QSplitter)

# Local package imports
from fibrowser.config import (DEFAULT_HOME_PAGE, APP_NAME, APP_VERSION, WINDOW_MIN_WIDTH, 
                              WINDOW_MIN_HEIGHT, SEARCH_ENGINES, THEMES, get_icon)
from fibrowser.ui.widgets import AnimatedButton, ToastNotification
from fibrowser.ui.downloads import DownloadManager
from fibrowser.ui.tab import Tab

logger = logging.getLogger(__name__)

class Window(QMainWindow):
    """Main browser window with enhanced features, modern UI, and improved performance"""
    
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)
        
        # Window configuration
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setWindowIcon(get_icon("favicon.png", QStyle.SP_ComputerIcon))
        
        # Initialize storage paths
        self.config_dir = Path(os.path.expanduser("~")) / ".fibrowser"
        self.config_dir.mkdir(exist_ok=True)
        self.session_file = self.config_dir / "session.json"
        self.history_file = self.config_dir / "history.json"
        self.bookmarks_file = self.config_dir / "bookmarks.json"
        self.settings_file = self.config_dir / "config.json"
        
        # Browser configurations and state
        self.homepage = DEFAULT_HOME_PAGE
        self.current_theme = "Dark"
        self.is_private_mode = False
        self.current_engine = "Google"
        self.bookmarks: Dict[str, str] = {}
        self.history: List[str] = []
        self.closed_tabs_stack: List[str] = []
        self.web_dark_mode_active = False
        self.default_zoom = 1.0
        self.js_enabled = True
        self.clear_on_exit = False
        self._private_profile: Optional[QWebEngineProfile] = None
        
        # Load user configurations & data
        self._load_settings()
        
        # Initialize UI
        self._init_ui()
        self._register_shortcuts()
        self._load_bookmarks()
        self._load_history()
        
        # Apply theme and restore session
        self.apply_theme(self.current_theme)
        self.restore_session()
        
        # Register global download listener (connected centrally to prevent duplicates & leaks)
        QWebEngineProfile.defaultProfile().downloadRequested.connect(self.on_download_requested)
        
        logger.info(f"{APP_NAME} v{APP_VERSION} started")
        self.log_action("🚀 Browser started successfully")
        
    def get_private_profile(self) -> QWebEngineProfile:
        """Get or create the off-the-record profile for private browsing"""
        if not self._private_profile:
            # Create off-the-record profile (no storage name = off-the-record)
            self._private_profile = QWebEngineProfile(self)
            self._private_profile.downloadRequested.connect(self.on_download_requested)
            
            settings = self._private_profile.settings()
            settings.setAttribute(settings.JavascriptEnabled, self.js_enabled)
        return self._private_profile

    def _load_settings(self) -> None:
        """Load browser settings from config file"""
        self.homepage = DEFAULT_HOME_PAGE
        self.current_engine = "Google"
        self.current_theme = "Dark"
        self.default_zoom = 1.0
        self.js_enabled = True
        self.clear_on_exit = False
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    self.homepage = data.get("homepage", DEFAULT_HOME_PAGE)
                    self.current_engine = data.get("search_engine", "Google")
                    self.current_theme = data.get("theme", "Dark")
                    self.default_zoom = data.get("default_zoom", 1.0)
                    self.js_enabled = data.get("javascript_enabled", True)
                    self.clear_on_exit = data.get("clear_on_exit", False)
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            
    def _save_settings(self) -> None:
        """Save browser settings to config file"""
        try:
            data = {
                "homepage": self.homepage,
                "search_engine": self.current_engine,
                "theme": self.current_theme,
                "default_zoom": self.default_zoom,
                "javascript_enabled": self.js_enabled,
                "clear_on_exit": self.clear_on_exit
            }
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def _init_ui(self) -> None:
        """Initialize user interface components"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)
        
        # Navigation toolbar
        self._create_navigation_toolbar()
        main_layout.addWidget(self.nav_toolbar)
        
        # Bookmarks toolbar
        self._create_bookmarks_toolbar()
        main_layout.addWidget(self.bookmarks_toolbar)
        
        # Find Bar
        self.find_bar = QWidget()
        find_layout = QHBoxLayout(self.find_bar)
        find_layout.setContentsMargins(10, 4, 10, 4)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find in page...")
        self.find_input.textChanged.connect(self.find_text)
        self.find_input.returnPressed.connect(self.find_next)
        
        find_next_btn = QPushButton("Next")
        find_next_btn.clicked.connect(self.find_next)
        find_close_btn = QPushButton("✕")
        find_close_btn.setFlat(True)
        find_close_btn.clicked.connect(self.hide_find_bar)
        
        find_layout.addWidget(QLabel("🔍 Find:"))
        find_layout.addWidget(self.find_input)
        find_layout.addWidget(find_next_btn)
        find_layout.addWidget(find_close_btn)
        self.find_bar.setVisible(False)
        main_layout.addWidget(self.find_bar)

        # Tab Widget Wrapped in Splitter for DevTools
        self.splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(self.splitter)
        
        # Tabs container (widget to hold tabs)
        self.tabs_container = QWidget()
        self.tabs_layout = QVBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        
        self._create_tabs()
        self.tabs_layout.addWidget(self.tabs)
        self.splitter.addWidget(self.tabs_container)
        
        # Real Developer console
        self.dev_tools_view = QWebEngineView()
        self.dev_tools_view.setVisible(False)
        self.splitter.addWidget(self.dev_tools_view)
        
        # Set devtools default size allocation
        self.splitter.setSizes([600, 200])
        
        # Actions Log Console Widget
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(80)
        self.console.setMaximumHeight(150)
        self.console.setVisible(False)
        main_layout.addWidget(self.console)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, 1)
        
        # Private mode indicator
        self.private_indicator = QLabel("🔒 Private")
        self.private_indicator.setVisible(False)
        self.status_bar.addPermanentWidget(self.private_indicator)
        
        # Zoom indicator
        self.zoom_indicator = QLabel("🔍 100%")
        self.status_bar.addPermanentWidget(self.zoom_indicator)
        
        # Download manager
        self.download_manager = DownloadManager(self)
        
    def _create_navigation_toolbar(self) -> None:
        """Create navigation toolbar with all controls"""
        self.nav_toolbar = QToolBar('Navigation')
        self.nav_toolbar.setMovable(False)
        self.nav_toolbar.setIconSize(QSize(24, 24))
        self.nav_toolbar.setObjectName("NavToolbar")
        
        # Navigation buttons
        self.back_btn = AnimatedButton()
        self.back_btn.setIcon(get_icon("back_icon.png", QStyle.SP_ArrowBack))
        self.back_btn.setToolTip("Back (Alt+Left)")
        self.back_btn.clicked.connect(self.navigate_back)
        
        self.forward_btn = AnimatedButton()
        self.forward_btn.setIcon(get_icon("next_icon.png", QStyle.SP_ArrowForward))
        self.forward_btn.setToolTip("Forward (Alt+Right)")
        self.forward_btn.clicked.connect(self.navigate_forward)
        
        self.refresh_btn = AnimatedButton()
        self.refresh_btn.setIcon(get_icon("refresh_icon.png", QStyle.SP_BrowserReload))
        self.refresh_btn.setToolTip("Refresh (F5)")
        self.refresh_btn.clicked.connect(self.refresh_page)
        
        self.home_btn = AnimatedButton()
        self.home_btn.setIcon(get_icon("home_icon.png", QStyle.SP_DirHomeIcon))
        self.home_btn.setToolTip("Home (Alt+Home)")
        self.home_btn.clicked.connect(self.go_to_home)
        
        # Address bar
        self.URLBar = QLineEdit()
        self.URLBar.setPlaceholderText("🔍 Search or enter URL...")
        self.URLBar.returnPressed.connect(self.load_url)
        self.URLBar.setClearButtonEnabled(True)
        self.URLBar.setMaximumHeight(36)
        
        # Search engine selector
        self.search_combo = QComboBox()
        self.search_combo.addItems(list(SEARCH_ENGINES.keys()))
        self.search_combo.setCurrentText(self.current_engine)
        self.search_combo.currentTextChanged.connect(self.set_search_engine)
        self.search_combo.setMaximumWidth(120)
        self.search_combo.setToolTip("Select search engine")
        
        # Feature buttons
        self.bookmarks_btn = AnimatedButton()
        self.bookmarks_btn.setIcon(get_icon("bookmarks_icon.png", QStyle.SP_DirLinkIcon))
        self.bookmarks_btn.setToolTip("Bookmarks (Ctrl+B)")
        self.bookmarks_btn.clicked.connect(self.toggle_bookmarks_bar)
        
        self.history_btn = AnimatedButton()
        self.history_btn.setIcon(get_icon("history_icon.png", QStyle.SP_FileDialogListView))
        self.history_btn.setToolTip("History (Ctrl+H)")
        self.history_btn.clicked.connect(self.show_history)
        
        self.downloads_btn = AnimatedButton()
        self.downloads_btn.setIcon(get_icon("downloads_icon.png", QStyle.SP_DialogSaveButton))
        self.downloads_btn.setToolTip("Downloads (Ctrl+J)")
        self.downloads_btn.clicked.connect(self.show_downloads)
        
        self.private_btn = AnimatedButton()
        self.private_btn.setIcon(get_icon("private_icon.png", QStyle.SP_FileDialogEnd))
        self.private_btn.setToolTip("Private Mode (Ctrl+Shift+P)")
        self.private_btn.clicked.connect(self.toggle_private_mode)
        
        self.settings_btn = AnimatedButton()
        self.settings_btn.setIcon(get_icon("settings_icon.png", QStyle.SP_FileDialogDetailedView))
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        
        self.web_dark_btn = AnimatedButton()
        self.web_dark_btn.setIcon(get_icon("web_dark_icon.png", QStyle.SP_DesktopIcon))
        self.web_dark_btn.setToolTip("Toggle Web Dark Mode")
        self.web_dark_btn.clicked.connect(self.toggle_web_dark_mode)
        
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
        self.nav_toolbar.addWidget(self.history_btn)
        self.nav_toolbar.addWidget(self.downloads_btn)
        self.nav_toolbar.addWidget(self.private_btn)
        self.nav_toolbar.addWidget(self.web_dark_btn)
        self.nav_toolbar.addWidget(self.settings_btn)
        
    def _create_bookmarks_toolbar(self) -> None:
        """Create bookmarks toolbar"""
        self.bookmarks_toolbar = QToolBar('Bookmarks')
        self.bookmarks_toolbar.setMovable(False)
        self.bookmarks_toolbar.setVisible(False)
        self.bookmarks_toolbar.setObjectName("BookmarksToolbar")
        
        # Default bookmarks
        default_bookmarks = {
            "🔍 Google": "https://www.google.com",
            "📺 YouTube": "https://www.youtube.com",
            "💻 GitHub": "https://github.com",
            "📚 StackOverflow": "https://stackoverflow.com",
            "🐍 PyPI": "https://pypi.org",
            "📖 Wikipedia": "https://en.wikipedia.org"
        }
        
        self.bookmarks.update(default_bookmarks)
        self._refresh_bookmarks_toolbar()
        
    def _refresh_bookmarks_toolbar(self) -> None:
        """Refresh bookmarks toolbar with current bookmarks"""
        # Clear all widgets
        for action in self.bookmarks_toolbar.actions():
            self.bookmarks_toolbar.removeAction(action)
        
        # Add bookmarks
        for name, url in self.bookmarks.items():
            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFlat(True)
            btn.setToolTip(url)
            btn.clicked.connect(lambda checked, u=url: self.navigate_to(u))
            
            # Setup right-click delete context menu
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, n=name: self._show_bookmark_context_menu(pos, b, n)
            )
            
            self.bookmarks_toolbar.addWidget(btn)
        
        self.bookmarks_toolbar.addSeparator()
        
        # Add bookmark button
        add_bookmark_btn = QPushButton("➕ Add")
        add_bookmark_btn.setCursor(Qt.PointingHandCursor)
        add_bookmark_btn.setFlat(True)
        add_bookmark_btn.clicked.connect(self._add_current_bookmark)
        self.bookmarks_toolbar.addWidget(add_bookmark_btn)

    def _show_bookmark_context_menu(self, pos: QPoint, button: QPushButton, name: str) -> None:
        """Show context menu for bookmarks to allow deletion"""
        menu = QMenu(self)
        delete_action = QAction("🗑️ Delete Bookmark", self)
        delete_action.triggered.connect(lambda: self._delete_bookmark(name))
        menu.addAction(delete_action)
        menu.exec_(button.mapToGlobal(pos))
        
    def _delete_bookmark(self, name: str) -> None:
        """Delete a bookmark by name"""
        if name in self.bookmarks:
            del self.bookmarks[name]
            self._refresh_bookmarks_toolbar()
            self._save_bookmarks()
            self.log_action(f"🗑️ Bookmark deleted: {name}")
        
    def _create_tabs(self) -> None:
        """Create tab widget with enhanced features"""
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        
        # New tab button
        self.new_tab_btn = QToolButton()
        self.new_tab_btn.setText("➕")
        self.new_tab_btn.setToolTip("New Tab (Ctrl+T)")
        self.new_tab_btn.setCursor(Qt.PointingHandCursor)
        self.new_tab_btn.setMinimumSize(30, 30)
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab())
        self.tabs.setCornerWidget(self.new_tab_btn, Qt.TopRightCorner)
        
    def _register_shortcuts(self) -> None:
        """Register all keyboard shortcuts"""
        # Tab management
        QShortcut(QKeySequence("Ctrl+T"), self, lambda: self.add_new_tab())
        QShortcut(QKeySequence("Ctrl+W"), self, self.close_current_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self.next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self.previous_tab)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self, self.reopen_closed_tab)
        
        # Navigation
        QShortcut(QKeySequence("Ctrl+L"), self, self.focus_address_bar)
        QShortcut(QKeySequence("F5"), self, self.refresh_page)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self, self.hard_refresh)
        QShortcut(QKeySequence("Ctrl+H"), self, self.show_history)
        QShortcut(QKeySequence("Alt+Left"), self, self.navigate_back)
        QShortcut(QKeySequence("Alt+Right"), self, self.navigate_forward)
        QShortcut(QKeySequence("Alt+Home"), self, self.go_to_home)
        
        # Features
        QShortcut(QKeySequence("Ctrl+J"), self, self.show_downloads)
        QShortcut(QKeySequence("Ctrl+B"), self, self.toggle_bookmarks_bar)
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, self.toggle_private_mode)
        QShortcut(QKeySequence("F12"), self, self.toggle_dev_tools)
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.reset_zoom)
        QShortcut(QKeySequence("Ctrl+F"), self, self.show_find_bar)
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Esc"), self, self.hide_find_bar)
        
    def add_new_tab(self, url: Optional[str] = None, is_private: bool = False) -> Tab:
        """Add a new browser tab
        
        Args:
            url: Optional URL to load in the new tab
            is_private: True to open tab in Private Mode
            
        Returns:
            The newly created Tab instance
        """
        is_tab_private = is_private or self.is_private_mode
        
        tab = Tab(self, url, is_private=is_tab_private)
        tab_title = "New Tab"
        if is_tab_private:
            tab_title = "🔒 Private Tab"
            
        index = self.tabs.addTab(tab, tab_title)
        
        if is_tab_private:
            self.tabs.tabBar().setTabTextColor(index, QColor("#d9534f"))
            
        self.tabs.setCurrentIndex(index)
        self.URLBar.setFocus()
        
        # Apply default zoom if configured
        if hasattr(self, 'default_zoom'):
            tab.browser.setZoomFactor(self.default_zoom)
            
        mode_str = "Private" if is_tab_private else "Normal"
        self.log_action(f"📑 New {mode_str} tab opened (#{index + 1})")
        return tab
        
    def close_tab(self, index: int) -> None:
        """Close tab at specified index and reclaim memory"""
        if self.tabs.count() > 1:
            tab = self.tabs.widget(index)
            if tab and hasattr(tab, 'browser'):
                # Store URL for undo in stack
                url_str = tab.browser.url().toString()
                if url_str and url_str != self.homepage:
                    self.closed_tabs_stack.append(url_str)
            
            # Detach devtools before deleting tab
            if tab and hasattr(tab, 'browser') and hasattr(self, 'dev_tools_view') and self.dev_tools_view.isVisible():
                try:
                    tab.browser.page().setDevToolsPage(None)
                except Exception:
                    pass
                    
            self.tabs.removeTab(index)
            if tab:
                tab.deleteLater() # Explicit memory reclaim in PyQt
            self.log_action(f"🗙 Tab closed")
        else:
            self.close()
            
    def close_current_tab(self) -> None:
        """Close the currently active tab"""
        self.close_tab(self.tabs.currentIndex())
        
    def reopen_closed_tab(self) -> None:
        """Reopen closed tabs sequentially from closed stack"""
        if hasattr(self, 'closed_tabs_stack') and self.closed_tabs_stack:
            url = self.closed_tabs_stack.pop()
            self.add_new_tab(url)
            self.log_action("📑 Reopened closed tab")
        else:
            self.show_toast("No closed tabs to reopen")
            
    def next_tab(self) -> None:
        """Switch to next tab"""
        current = self.tabs.currentIndex()
        next_index = (current + 1) % self.tabs.count()
        self.tabs.setCurrentIndex(next_index)
        
    def previous_tab(self) -> None:
        """Switch to previous tab"""
        current = self.tabs.currentIndex()
        prev_index = (current - 1) % self.tabs.count()
        self.tabs.setCurrentIndex(prev_index)
        
    def tab_changed(self, index: int) -> None:
        """Handle tab change events"""
        if index >= 0:
            tab = self.tabs.widget(index)
            if tab and hasattr(tab, 'browser'):
                url = tab.browser.url().toString()
                self.URLBar.setText(url)
                self.URLBar.setCursorPosition(0)
                if hasattr(self, 'dev_tools_view') and self.dev_tools_view.isVisible():
                    tab.browser.page().setDevToolsPage(self.dev_tools_view.page())
                
                # Sync loading progress bar
                if hasattr(self, 'progress_bar') and self.progress_bar:
                    progress = getattr(tab, 'progress', 100)
                    self.progress_bar.setVisible(progress < 100)
                    self.progress_bar.setValue(progress)
                    
                # Sync status bar zoom indicator
                if hasattr(self, 'zoom_indicator') and self.zoom_indicator:
                    zoom = tab.browser.zoomFactor()
                    self.zoom_indicator.setText(f"🔍 {int(zoom * 100)}%")
                    
                # Sync bookmark highlight
                self.update_bookmark_button_state()
            
    def current_tab(self) -> Optional[Tab]:
        """Get the current active tab
        
        Returns:
            The currently active Tab instance or None
        """
        return self.tabs.currentWidget()
        
    def navigate_back(self) -> None:
        """Navigate back in browser history"""
        if self.current_tab():
            self.current_tab().browser.back()
            
    def navigate_forward(self) -> None:
        """Navigate forward in browser history"""
        if self.current_tab():
            self.current_tab().browser.forward()
            
    def refresh_page(self) -> None:
        """Refresh current page"""
        if self.current_tab():
            self.current_tab().browser.reload()
            
    def hard_refresh(self) -> None:
        """Hard refresh (clear cache and reload)"""
        if self.current_tab():
            self.current_tab().browser.triggerPageAction(QWebEnginePage.ReloadAndBypassCache)
            self.log_action("🔄 Hard refresh performed (bypassing cache)")
            self.show_toast("Hard refresh performed")
            
    def go_to_home(self) -> None:
        """Navigate to home page"""
        if self.current_tab():
            self.current_tab().browser.setUrl(QUrl(self.homepage))
            
    def load_url(self) -> None:
        """Load URL from address bar with smart parsing (supporting local Windows files & search encoding)"""
        if not self.current_tab():
            return
            
        text = self.URLBar.text().strip()
        if not text:
            return
        
        try:
            # Check if it looks like a local file path
            is_local_file = False
            # Match Windows drive paths (e.g. C:\path or D:/path) or absolute paths
            if os.path.isabs(text) or (len(text) > 1 and text[1] == ':' and text[0].isalpha()):
                is_local_file = True
                url = QUrl.fromLocalFile(text)
            else:
                # Check if it's a search query or URL
                is_search = False
                if ' ' in text:
                    is_search = True
                elif text.startswith(('http://', 'https://', 'file://', 'view-source:')):
                    is_search = False
                elif '.' in text and not text.endswith('.'):
                    is_search = False
                else:
                    is_search = True
                    
                if is_search:
                    # URL-encode the search query using urllib.parse.quote
                    encoded_query = urllib.parse.quote(text)
                    search_url = SEARCH_ENGINES.get(self.current_engine, SEARCH_ENGINES["Google"]).format(encoded_query)
                    url = QUrl(search_url)
                else:
                    # Add standard scheme if not provided
                    if not text.startswith(('http://', 'https://', 'file://', 'view-source:')):
                        text = 'https://' + text
                    url = QUrl(text)
            
            # Verify URL is valid
            if not url.isValid():
                self.log_action(f"❌ Invalid URL: {url.errorString()}")
                return
                
            self.current_tab().browser.setUrl(url)
            self.add_to_history(url.toString())
            
        except Exception as e:
            logger.error(f"URL load error: {str(e)}")
            self.log_action(f"❌ Error: {str(e)}")
                
    def navigate_to(self, url: str) -> None:
        """Navigate to specific URL
        
        Args:
            url: URL to navigate to
        """
        if self.current_tab():
            self.current_tab().browser.setUrl(QUrl(url))
            self.add_to_history(url)
            
    def set_search_engine(self, engine: str) -> None:
        """Set the default search engine
        
        Args:
            engine: Search engine name
        """
        if engine in SEARCH_ENGINES:
            self.current_engine = engine
            self.search_combo.setCurrentText(engine)
            self.log_action(f"🔍 Search engine: {engine}")
        
    def zoom_in(self) -> None:
        """Increase page zoom level"""
        if self.current_tab():
            current_zoom = self.current_tab().browser.zoomFactor()
            new_zoom = min(current_zoom + 0.1, 3.0)
            self.current_tab().browser.setZoomFactor(new_zoom)
            self.log_action(f"🔍 Zoom: {int(new_zoom * 100)}%")
            if hasattr(self, 'zoom_indicator') and self.zoom_indicator:
                self.zoom_indicator.setText(f"🔍 {int(new_zoom * 100)}%")
            
    def zoom_out(self) -> None:
        """Decrease page zoom level"""
        if self.current_tab():
            current_zoom = self.current_tab().browser.zoomFactor()
            new_zoom = max(current_zoom - 0.1, 0.5)
            self.current_tab().browser.setZoomFactor(new_zoom)
            self.log_action(f"🔍 Zoom: {int(new_zoom * 100)}%")
            if hasattr(self, 'zoom_indicator') and self.zoom_indicator:
                self.zoom_indicator.setText(f"🔍 {int(new_zoom * 100)}%")
            
    def reset_zoom(self) -> None:
        """Reset page zoom to default"""
        if self.current_tab():
            self.current_tab().browser.setZoomFactor(1.0)
            self.log_action("🔍 Zoom: 100%")
            if hasattr(self, 'zoom_indicator') and self.zoom_indicator:
                self.zoom_indicator.setText("🔍 100%")
            
    def show_downloads(self) -> None:
        """Show download manager window"""
        self.download_manager.show()
        self.download_manager.raise_()
        self.download_manager.activateWindow()
        
    def show_settings(self) -> None:
        """Show settings dialog"""
        self._show_settings_dialog()
        
    def toggle_bookmarks_bar(self) -> None:
        """Toggle bookmarks toolbar visibility"""
        visible = not self.bookmarks_toolbar.isVisible()
        self.bookmarks_toolbar.setVisible(visible)
        self.log_action(f"📚 Bookmarks {'shown' if visible else 'hidden'}")
        
    def toggle_private_mode(self) -> None:
        """Toggle private browsing mode"""
        self.is_private_mode = not self.is_private_mode
        self.private_indicator.setVisible(self.is_private_mode)
        
        # Style indicator based on current state
        if self.is_private_mode:
            self.private_indicator.setStyleSheet("color: #d9534f; font-weight: bold;")
            self.log_action("🔒 Private mode enabled - new tabs will browse privately")
        else:
            self.private_indicator.setStyleSheet("")
            self.log_action("🔒 Private mode disabled")
            
    def focus_address_bar(self) -> None:
        """Set focus and select all text in address bar"""
        self.URLBar.setFocus()
        self.URLBar.selectAll()
        
    def toggle_dev_tools(self) -> None:
        """Toggle developer console visibility"""
        if not self.current_tab(): return
        visible = not self.dev_tools_view.isVisible()
        self.dev_tools_view.setVisible(visible)
        if visible:
            self.current_tab().browser.page().setDevToolsPage(self.dev_tools_view.page())
        else:
            self.current_tab().browser.page().setDevToolsPage(None)
        self.log_action(f"👨‍💻 Dev Tools {'shown' if visible else 'hidden'}")

    def show_find_bar(self):
        """Show Find in Page bar"""
        self.find_bar.setVisible(True)
        self.find_input.setFocus()
        self.find_input.selectAll()
        
    def hide_find_bar(self):
        """Hide Find in Page bar"""
        self.find_bar.setVisible(False)
        if self.current_tab():
            self.current_tab().browser.findText("") # Clear search
            
    def find_text(self, text):
        """Find text in page"""
        if self.current_tab():
            self.current_tab().browser.findText(text)
            
    def find_next(self):
        """Find next occurrence in page"""
        if self.current_tab():
            self.current_tab().browser.findText(self.find_input.text())
            
    def toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
            self.log_action("🔳 Exited Fullscreen")
        else:
            self.showFullScreen()
            self.log_action("🔲 Entered Fullscreen (Press F11 to exit)")
            
    def toggle_web_dark_mode(self) -> None:
        """Toggle Web Dark Mode globally and apply to all tabs"""
        if not hasattr(self, 'web_dark_mode_active'):
            self.web_dark_mode_active = False
            
        self.web_dark_mode_active = not self.web_dark_mode_active
        mode_str = "Enabled" if self.web_dark_mode_active else "Disabled"
        self.log_action(f"🌓 Web Dark Mode {mode_str}")
        self.show_toast(f"Web Dark Mode {mode_str}")
        
        # Style button border/background based on current state
        if self.web_dark_mode_active:
            self.web_dark_btn.setStyleSheet(f"background-color: {self.current_theme_color()}; border-radius: 18px;")
        else:
            self.web_dark_btn.setStyleSheet("")
            
        # JS to inject/remove stylesheet
        js_enable = """
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
        js_disable = """
        (function() {
            var el = document.getElementById('fibrowser-dark-mode');
            if (el) { el.remove(); }
        })();
        """
        js = js_enable if self.web_dark_mode_active else js_disable
        
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab and hasattr(tab, 'browser'):
                tab.browser.page().runJavaScript(js)
        
    def show_history(self) -> None:
        """Show browsing history dialog with search filtering"""
        dialog = QDialog(self)
        dialog.setWindowTitle("📜 Browsing History")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText("🔍 Search history...")
        search_layout.addWidget(search_input)
        layout.addLayout(search_layout)
        
        # History list
        history_list = QListWidget()
        
        def populate_history(filter_text=""):
            history_list.clear()
            filtered_history = [url for url in self.history if filter_text.lower() in url.lower()]
            for i, url in enumerate(reversed(filtered_history[-100:]), 1):
                item = QListWidgetItem(f"{i}. {url}")
                item.setData(Qt.UserRole, url)
                history_list.addItem(item)
                
        populate_history()
        search_input.textChanged.connect(populate_history)
        
        history_list.itemDoubleClicked.connect(
            lambda item: self.navigate_to(item.data(Qt.UserRole)) or dialog.close()
        )
        layout.addWidget(history_list)
        
        # Context menu for deleting individual item
        history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        history_list.customContextMenuRequested.connect(
            lambda pos: self._show_history_context_menu(pos, history_list)
        )
        
        # Setup Delete key shortcut
        shortcut = QShortcut(QKeySequence(Qt.Key_Delete), dialog)
        shortcut.activated.connect(lambda: self._delete_selected_history_item(history_list))
        
        # Buttons
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("🗑️ Clear History")
        
        def clear_history_action():
            if QMessageBox.question(dialog, "Clear History", 
                "Are you sure you want to clear all browsing history?",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.history.clear()
                self._save_history()
                history_list.clear()
                self.log_action("🗑️ Browsing history cleared")
                self.show_toast("Browsing history cleared")
                
        clear_btn.clicked.connect(clear_history_action)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def _show_history_context_menu(self, pos: QPoint, list_widget: QListWidget) -> None:
        """Show context menu to delete selected history item"""
        item = list_widget.itemAt(pos)
        if not item:
            return
            
        menu = QMenu(self)
        delete_action = QAction("🗑️ Remove from History", self)
        url = item.data(Qt.UserRole)
        delete_action.triggered.connect(lambda: self._delete_history_item(url, list_widget))
        menu.addAction(delete_action)
        menu.exec_(list_widget.mapToGlobal(pos))
        
    def _delete_history_item(self, url: str, list_widget: QListWidget) -> None:
        """Remove a single URL from history"""
        if url in self.history:
            self.history = [h for h in self.history if h != url]
            self._save_history()
            
            # Refresh list widget
            list_widget.clear()
            for i, h_url in enumerate(reversed(self.history[-100:]), 1):
                item = QListWidgetItem(f"{i}. {h_url}")
                item.setData(Qt.UserRole, h_url)
                list_widget.addItem(item)
            self.log_action(f"🗑️ Removed from history: {url[:50]}...")
            
    def _delete_selected_history_item(self, list_widget: QListWidget) -> None:
        """Delete selected history item using Delete key"""
        item = list_widget.currentItem()
        if item:
            url = item.data(Qt.UserRole)
            self._delete_history_item(url, list_widget)
        
    def _add_current_bookmark(self) -> None:
        """Add current page as bookmark"""
        if not self.current_tab():
            return
            
        url = self.current_tab().browser.url().toString()
        title = self.current_tab().title or "Bookmark"
        
        self.bookmarks[title] = url
        self._refresh_bookmarks_toolbar()
        self._save_bookmarks()
        self.log_action(f"⭐ Bookmarked: {title}")
        self.show_toast(f"Bookmarked: {title}")
        
    def _show_settings_dialog(self) -> None:
        """Show settings dialog with theme, homepage, search engine, zoom, javascript, and exit actions"""
        dialog = QDialog(self)
        dialog.setWindowTitle("⚙️ Settings")
        dialog.setMinimumSize(450, 420)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # Theme selector
        theme_combo = QComboBox()
        theme_combo.addItems(list(THEMES.keys()))
        theme_combo.setCurrentText(self.current_theme)
        form_layout.addRow("Theme:", theme_combo)
        
        # Homepage input
        homepage_edit = QLineEdit()
        homepage_edit.setText(self.homepage)
        form_layout.addRow("Homepage:", homepage_edit)
        
        # Search Engine selector
        engine_combo = QComboBox()
        engine_combo.addItems(list(SEARCH_ENGINES.keys()))
        engine_combo.setCurrentText(self.current_engine)
        form_layout.addRow("Search Engine:", engine_combo)
        
        # Default Zoom selector
        zoom_combo = QComboBox()
        zoom_options = ["50%", "75%", "100%", "125%", "150%", "200%"]
        zoom_combo.addItems(zoom_options)
        zoom_val_str = f"{int(self.default_zoom * 100)}%"
        if zoom_val_str in zoom_options:
            zoom_combo.setCurrentText(zoom_val_str)
        else:
            zoom_combo.setCurrentText("100%")
        form_layout.addRow("Default Zoom:", zoom_combo)
        
        # Javascript checkbox
        js_cb = QCheckBox("Enable JavaScript (faster rendering)")
        js_cb.setChecked(self.js_enabled)
        form_layout.addRow("Security:", js_cb)
        
        # Clear on Exit checkbox
        exit_cb = QCheckBox("Clear browsing history on exit")
        exit_cb.setChecked(self.clear_on_exit)
        form_layout.addRow("Privacy:", exit_cb)
        
        # Clear Cache Button
        clear_cache_btn = QPushButton("🧹 Clear Browser Cache Now")
        def clear_cache_action():
            QWebEngineProfile.defaultProfile().clearHttpCache()
            if self._private_profile:
                self._private_profile.clearHttpCache()
            QMessageBox.information(dialog, "Cache Cleared", "Browser cache cleared successfully.")
        clear_cache_btn.clicked.connect(clear_cache_action)
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
        save_btn = QPushButton("✓ Save")
        cancel_btn = QPushButton("✕ Cancel")
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # Live theme preview support
        theme_combo.currentTextChanged.connect(self.apply_theme)
        original_theme = self.current_theme
        
        def save_settings():
            self.homepage = homepage_edit.text().strip() or DEFAULT_HOME_PAGE
            self.current_engine = engine_combo.currentText()
            self.current_theme = theme_combo.currentText()
            
            # Zoom parser
            zoom_text = zoom_combo.currentText().replace("%", "")
            try:
                self.default_zoom = float(zoom_text) / 100.0
            except ValueError:
                self.default_zoom = 1.0
                
            self.js_enabled = js_cb.isChecked()
            self.clear_on_exit = exit_cb.isChecked()
            
            # Apply JS configuration
            QWebEngineProfile.defaultProfile().settings().setAttribute(
                QWebEngineProfile.defaultProfile().settings().JavascriptEnabled, self.js_enabled
            )
            if self._private_profile:
                self._private_profile.settings().setAttribute(
                    self._private_profile.settings().JavascriptEnabled, self.js_enabled
                )
                
            self.apply_theme(self.current_theme)
            self.set_search_engine(self.current_engine)
            self._save_settings()
            self.log_action("⚙️ Settings saved successfully")
            self.show_toast("Settings saved successfully")
            dialog.accept()
            
        def cancel_settings():
            # Revert theme preview
            if theme_combo.currentText() != original_theme:
                self.apply_theme(original_theme)
            dialog.reject()
            
        save_btn.clicked.connect(save_settings)
        cancel_btn.clicked.connect(cancel_settings)
        
        dialog.exec_()
        
    def apply_theme(self, theme_name: str) -> None:
        """Apply color theme to the browser
        
        Args:
            theme_name: Name of the theme to apply
        """
        if theme_name not in THEMES:
            logger.warning(f"Theme '{theme_name}' not found, using Dark")
            theme_name = "Dark"
        
        self.current_theme = theme_name
        theme = THEMES[theme_name]
        
        # Generate modern stylesheet with custom scrollbars, tooltips, dialogs, and fonts
        stylesheet = f"""
            /* Global Font and Base Styles */
            QWidget {{
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                font-size: 13px;
            }}
            
            QMainWindow {{
                background-color: {theme.bg};
            }}
            
            /* Dialogs styling */
            QDialog {{
                background-color: {theme.bg};
                border: 1px solid {theme.hover};
            }}
            
            /* Tooltips styling */
            QToolTip {{
                background-color: {theme.tab_bg};
                color: {theme.fg};
                border: 1px solid {theme.accent};
                border-radius: 4px;
                padding: 4px;
            }}
            
            /* Tabs */
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
            
            /* Combo Box */
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
            }}
            
            /* Toolbar */
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
            
            /* Circular Toolbar PushButtons (Navigation/Action buttons) */
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
            
            /* General Dialog/Normal PushButtons */
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
            
            /* Thin WebEngine Page Loading Progress Bar */
            QProgressBar {{
                border: none;
                background: transparent;
                height: 3px;
            }}
            QProgressBar::chunk {{
                background: {theme.accent};
                border-radius: 1px;
            }}
            
            /* List Widget Download Progress Bar */
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
            
            /* Lists */
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
            
            /* Text Edit / Console */
            QPlainTextEdit, QTextEdit {{
                background: {theme.tab_bg};
                color: {theme.fg};
                border: 1px solid {theme.hover};
                border-radius: 4px;
            }}
            
            /* Menu */
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
        
        self.setStyleSheet(stylesheet)
        logger.info(f"Theme applied: {theme_name}")
        self.log_action(f"🎨 Theme: {theme_name}")
        
    def log_action(self, message: str) -> None:
        """Log action to console and status bar
        
        Args:
            message: Action message to log
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        try:
            if hasattr(self, 'console') and self.console:
                self.console.appendPlainText(log_entry)
                
                # Auto-scroll to bottom
                scrollbar = self.console.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass
        
        try:
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(message)
        except Exception:
            pass
        
    def add_to_history(self, url: str) -> None:
        """Add URL to browsing history"""
        current = self.current_tab()
        is_tab_private = current.is_private if current else False
        
        if not self.is_private_mode and not is_tab_private and url.startswith(('http://', 'https://')):
            self.history.append(url)
            # Keep only last 500 items
            if len(self.history) > 500:
                self.history = self.history[-500:]
            self._save_history()
            
    def _save_history(self) -> None:
        """Save browsing history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
            
    def _load_history(self) -> None:
        """Load browsing history from file"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            self.history = []
            
    def _save_bookmarks(self) -> None:
        """Save bookmarks to file"""
        try:
            with open(self.bookmarks_file, 'w') as f:
                json.dump(self.bookmarks, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving bookmarks: {e}")
            
    def _load_bookmarks(self) -> None:
        """Load bookmarks from file"""
        try:
            if self.bookmarks_file.exists():
                with open(self.bookmarks_file, 'r') as f:
                    saved_bookmarks = json.load(f)
                    self.bookmarks.update(saved_bookmarks)
            self._refresh_bookmarks_toolbar()
        except Exception as e:
            logger.error(f"Error loading bookmarks: {e}")
            
    def contextMenuEvent(self, event) -> None:
        """Handle right-click context menu"""
        menu = QMenu(self)
        
        # Tab actions
        new_tab_action = QAction("📑 New Tab", self)
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        menu.addAction(new_tab_action)
        
        close_tab_action = QAction("🗙 Close Tab", self)
        close_tab_action.triggered.connect(self.close_current_tab)
        menu.addAction(close_tab_action)
        
        menu.addSeparator()
        
        # Theme selector
        theme_menu = menu.addMenu("🎨 Theme")
        for theme_name in THEMES.keys():
            theme_action = QAction(theme_name, self)
            theme_action.triggered.connect(lambda _, t=theme_name: self.apply_theme(t))
            theme_menu.addAction(theme_action)
        
        menu.addSeparator()
        
        # Console toggle
        toggle_log_action = QAction("📝 Toggle Log Console", self)
        toggle_log_action.triggered.connect(self.toggle_log_console)
        menu.addAction(toggle_log_action)
        
        # Privacy
        private_action = QAction(
            f"{'🔓 Disable' if self.is_private_mode else '🔒 Enable'} Private Mode",
            self
        )
        private_action.triggered.connect(self.toggle_private_mode)
        menu.addAction(private_action)
        
        menu.exec_(event.globalPos())
 
    def toggle_log_console(self) -> None:
        """Toggle the visibility of the actions log console"""
        visible = not self.console.isVisible()
        self.console.setVisible(visible)
        self.log_action(f"📝 Log console {'shown' if visible else 'hidden'}")
  
    def handle_ssl_error(self, error) -> bool:
        """Handle SSL certificate errors"""
        dialog = QDialog(self)
        dialog.setWindowTitle("🔒 SSL Certificate Error")
        layout = QVBoxLayout()
        
        message = QLabel(
            f"<b>SSL Certificate Error</b><br>"
            f"<code>{error.errorDescription()}</code><br><br>"
            f"Website: <code>{error.url().host()}</code><br><br>"
            f"Do you want to proceed anyway?"
        )
        layout.addWidget(message)
        
        btn_layout = QHBoxLayout()
        proceed_btn = QPushButton("✓ Proceed")
        cancel_btn = QPushButton("✕ Cancel")
        
        proceed_btn.clicked.connect(lambda: (
            error.ignoreCertificateError(),
            dialog.accept()
        ))
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(proceed_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        return dialog.exec_() == QDialog.Accepted
    
    def on_download_requested(self, download: QWebEngineDownloadItem) -> None:
        """Handle download requests centrally to prevent multiple dialog prompts"""
        try:
            url = download.url().toString()[:60]
            self.log_action(f"📥 Download requested: {url}...")
            
            # Suggest target path
            suggested = os.path.basename(download.path() or download.url().path().split('/')[-1] or 'download')
            default_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            default_path = os.path.join(default_dir, suggested)
            
            # Show save dialog
            path, _ = QFileDialog.getSaveFileName(
                self, 
                'Save File As', 
                default_path,
                "All Files (*.*)"
            )
            
            if not path:
                download.cancel()
                return
            
            try:
                download.setPath(path)
            except Exception as e:
                logger.debug(f"Could not set download path: {e}")
            
            download.accept()
            
            # Add to download manager
            if hasattr(self, 'download_manager') and self.download_manager:
                self.download_manager.add_download(download)
                self.download_manager.show()
                self.log_action(f"✓ Download started: {os.path.basename(path)}")
                
        except Exception as e:
            logger.error(f"Download request error: {str(e)}")
            self.log_action(f"❌ Download error: {str(e)}")

    def save_session(self) -> None:
        """Save current session data"""
        session_data = {
            "tabs": [],
            "current_tab": self.tabs.currentIndex(),
            "theme": self.current_theme
        }
        
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab and hasattr(tab, 'browser'):
                url = tab.browser.url().toString()
                title = getattr(tab, 'title', 'New Tab')
                session_data["tabs"].append({
                    "url": url,
                    "title": title
                })
        
        try:
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            logger.info("Session saved")
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
    
    def restore_session(self) -> None:
        """Restore previous session or load default tab"""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)
                
                # Restore theme
                theme = session_data.get("theme", self.current_theme)
                self.apply_theme(theme)
                
                # Restore tabs
                tabs_data = session_data.get("tabs", [])
                if tabs_data:
                    # Clear existing placeholder tabs and reclaim memory
                    while self.tabs.count() > 0:
                        tab = self.tabs.widget(0)
                        self.tabs.removeTab(0)
                        if tab:
                            tab.deleteLater()
                    for tab_data in tabs_data:
                        self.add_new_tab(tab_data.get("url"))
                    
                    # Set active tab
                    current_tab_index = session_data.get("current_tab", 0)
                    if 0 <= current_tab_index < self.tabs.count():
                        self.tabs.setCurrentIndex(current_tab_index)
                
                logger.info("Session restored")
                self.log_action("✓ Session restored")
                
        except Exception as e:
            logger.error(f"Error restoring session: {str(e)}")
            
        # Ensure we always have at least one tab open
        if self.tabs.count() == 0:
            self.add_new_tab()
    
    def closeEvent(self, event) -> None:
        """Handle window close event"""
        if hasattr(self, 'clear_on_exit') and self.clear_on_exit:
            self.history.clear()
            self._save_history()
            logger.info("Browsing history cleared on exit")
            
        self.save_session()
        self._save_settings()
        logger.info("Fibrowser Pro closed")
        event.accept()

    def handle_html5_fullscreen(self, request) -> None:
        """Handle fullscreen toggling from a QWebEnginePage request"""
        request.accept()
        if request.toggleOn():
            self._was_maximized = self.isMaximized()
            self._prev_toolbar_visibility = self.nav_toolbar.isVisible()
            self._prev_bookmarks_visibility = self.bookmarks_toolbar.isVisible()
            self._prev_statusbar_visibility = self.status_bar.isVisible()
            self._prev_tabs_visibility = self.tabs.tabBar().isVisible()
            
            self.showFullScreen()
            self.nav_toolbar.setVisible(False)
            self.bookmarks_toolbar.setVisible(False)
            self.status_bar.setVisible(False)
            self.tabs.tabBar().setVisible(False)
            self.log_action("📺 Page entered fullscreen mode")
        else:
            if hasattr(self, '_was_maximized') and self._was_maximized:
                self.showMaximized()
            else:
                self.showNormal()
                
            self.nav_toolbar.setVisible(getattr(self, '_prev_toolbar_visibility', True))
            self.bookmarks_toolbar.setVisible(getattr(self, '_prev_bookmarks_visibility', False))
            self.status_bar.setVisible(getattr(self, '_prev_statusbar_visibility', True))
            self.tabs.tabBar().setVisible(getattr(self, '_prev_tabs_visibility', True))
            self.log_action("📺 Page exited fullscreen mode")

    def show_toast(self, message: str) -> None:
        """Show a temporary overlay toast notification"""
        try:
            ToastNotification(message, self)
        except Exception as e:
            logger.error(f"Error showing toast: {e}")

    def update_bookmark_button_state(self) -> None:
        """Update bookmark button background based on whether current URL is bookmarked"""
        if not self.current_tab() or not hasattr(self, 'bookmarks_btn') or not self.bookmarks_btn:
            return
            
        current_url = self.current_tab().browser.url().toString()
        is_bookmarked = current_url in self.bookmarks.values()
        
        if is_bookmarked:
            accent = self.current_theme_color()
            self.bookmarks_btn.setStyleSheet(f"background-color: {accent}; border-radius: 18px;")
            self.bookmarks_btn.setToolTip("Page Bookmarked")
        else:
            self.bookmarks_btn.setStyleSheet("")
            self.bookmarks_btn.setToolTip("Bookmark this page (Ctrl+B)")

    def current_theme_color(self) -> str:
        """Get the current theme accent color"""
        if hasattr(self, 'current_theme') and self.current_theme in THEMES:
            return THEMES[self.current_theme].accent
        return "#3b82f6"
