import os
import json
import time
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

from PyQt5.QtCore import QUrl, Qt, QSize, QTimer, QPoint
from PyQt5.QtGui import QIcon, QKeySequence, QColor
from PyQt5.QtWebEngineWidgets import (QWebEngineView, QWebEngineProfile, 
                                      QWebEngineDownloadItem, QWebEnginePage)
from PyQt5.QtWidgets import (QMainWindow, QStatusBar, QToolBar, QAction, 
                             QLineEdit, QTabWidget, QWidget, QVBoxLayout, QPushButton,
                             QMenu, QHBoxLayout, QLabel, QDialog,
                             QFileDialog, QProgressBar, QStyle, QShortcut, QToolButton,
                             QListWidget, QListWidgetItem, QComboBox, QCheckBox, QFormLayout,
                             QMessageBox, QPlainTextEdit, QSplitter)

# Local package imports
from fibrowser.config import (DEFAULT_HOME_PAGE, APP_NAME, APP_VERSION, WINDOW_MIN_WIDTH, 
                              WINDOW_MIN_HEIGHT, SEARCH_ENGINES, THEMES, MAX_TABS, 
                              TAB_THROTTLE_SECONDS, HISTORY_MAX_SIZE, HISTORY_SAVE_DEBOUNCE_MS,
                              PROGRESS_BAR_HEIGHT, DEFAULT_ZOOM, LOG_FILE_NAME, 
                              get_icon, format_error_message, is_safe_local_path)
from fibrowser.ui.widgets import AnimatedButton, ToastNotification
from fibrowser.ui.downloads import DownloadManager
from fibrowser.ui.tab import Tab
from fibrowser.ui.shortcut_manager import ShortcutManager
from fibrowser.ui.theme_manager import ThemeManager
from fibrowser.ui.dialogs.settings_dialog import SettingsDialog
from fibrowser.ui.dialogs.history_dialog import HistoryDialog

logger = logging.getLogger(__name__)

class Window(QMainWindow):
    """Main browser window coordinating tabs, toolbar, settings, downloads, and security."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize main browser window and subsystems."""
        super(Window, self).__init__(*args, **kwargs)
        
        # Window configuration
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setWindowIcon(get_icon("favicon.png", QStyle.SP_ComputerIcon))
        
        # Storage directory and file paths
        self.config_dir: Path = Path(os.path.expanduser("~")) / ".fibrowser"
        self.config_dir.mkdir(exist_ok=True)
        self.session_file: Path = self.config_dir / "session.json"
        self.history_file: Path = self.config_dir / "history.json"
        self.bookmarks_file: Path = self.config_dir / "bookmarks.json"
        self.settings_file: Path = self.config_dir / "config.json"
        self.log_file: Path = self.config_dir / LOG_FILE_NAME
        
        # Browser state
        self.homepage: str = DEFAULT_HOME_PAGE
        self.current_theme: str = "Dark"
        self.is_private_mode: bool = False
        self.current_engine: str = "Google"
        self.bookmarks: Dict[str, str] = {}
        self.bookmarks_history: List[Dict[str, str]] = []
        self.bookmarks_future: List[Dict[str, str]] = []
        self.history: List[str] = []
        self.closed_tabs_stack: List[str] = []
        self.web_dark_mode_active: bool = False
        self.default_zoom: float = DEFAULT_ZOOM
        self.js_enabled: bool = True
        self.clear_on_exit: bool = False
        self._private_profile: Optional[QWebEngineProfile] = None
        self._last_tab_create_time: float = 0.0
        self._history_save_timer: Optional[QTimer] = None
        self._history_dirty: bool = False
        
        # Shortcut manager
        self.shortcut_mgr = ShortcutManager(self)
        
        # Load user configurations & data with error recovery
        self._load_settings()
        
        # Initialize UI components
        self._init_ui()
        self._register_shortcuts()
        self._load_bookmarks()
        self._load_history()
        
        # Apply theme and restore session
        self.apply_theme(self.current_theme)
        self.restore_session()
        
        # Register global download listener
        QWebEngineProfile.defaultProfile().downloadRequested.connect(self.on_download_requested)
        
        logger.info(f"{APP_NAME} v{APP_VERSION} started")
        self.log_action("🚀 Browser started successfully")

    def get_private_profile(self) -> QWebEngineProfile:
        """Get or create the off-the-record profile for private browsing with strict memory isolation."""
        if not self._private_profile:
            # Create off-the-record profile (no storage name = off-the-record)
            self._private_profile = QWebEngineProfile(self)
            
            # Explicitly enforce memory-only cache and zero persistent cookies (HIGH-003)
            self._private_profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
            self._private_profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
            
            self._private_profile.downloadRequested.connect(self.on_download_requested)
            
            settings = self._private_profile.settings()
            settings.setAttribute(settings.JavascriptEnabled, self.js_enabled)
        return self._private_profile

    def _recover_corrupted_file(self, file_path: Path) -> None:
        """Backup corrupted JSON file to .bak to preserve diagnostic data (MED-009)."""
        try:
            if file_path.exists():
                bak_path = file_path.with_suffix(file_path.suffix + ".bak")
                if bak_path.exists():
                    bak_path.unlink()
                file_path.rename(bak_path)
                logger.warning(f"Corrupted configuration backed up to {bak_path}")
        except Exception as e:
            logger.error(f"Failed to backup corrupted file {file_path}: {e}")

    def _load_settings(self) -> None:
        """Load browser settings from config file with error recovery."""
        self.homepage = DEFAULT_HOME_PAGE
        self.current_engine = "Google"
        self.current_theme = "Dark"
        self.default_zoom = DEFAULT_ZOOM
        self.js_enabled = True
        self.clear_on_exit = False
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.homepage = data.get("homepage", DEFAULT_HOME_PAGE)
                    self.current_engine = data.get("search_engine", "Google")
                    self.current_theme = ThemeManager.validate_theme_name(data.get("theme", "Dark"))
                    self.default_zoom = float(data.get("default_zoom", DEFAULT_ZOOM))
                    self.js_enabled = bool(data.get("javascript_enabled", True))
                    self.clear_on_exit = bool(data.get("clear_on_exit", False))
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.error(f"Corrupted settings file, resetting to defaults: {e}")
            self._recover_corrupted_file(self.settings_file)
            self._save_settings()

    def _save_settings(self) -> None:
        """Save browser settings to config file."""
        try:
            data = {
                "homepage": self.homepage,
                "search_engine": self.current_engine,
                "theme": self.current_theme,
                "default_zoom": self.default_zoom,
                "javascript_enabled": self.js_enabled,
                "clear_on_exit": self.clear_on_exit
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def _init_ui(self) -> None:
        """Initialize user interface components and layouts."""
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
        
        # Tabs container
        self.tabs_container = QWidget()
        self.tabs_layout = QVBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        
        self._create_tabs()
        self.tabs_layout.addWidget(self.tabs)
        self.splitter.addWidget(self.tabs_container)
        
        # Developer console
        self.dev_tools_view = QWebEngineView()
        self.dev_tools_view.setVisible(False)
        self.splitter.addWidget(self.dev_tools_view)
        
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
        self.progress_bar.setMaximumHeight(PROGRESS_BAR_HEIGHT)
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
        """Create navigation toolbar with controls."""
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
        """Create bookmarks toolbar."""
        self.bookmarks_toolbar = QToolBar('Bookmarks')
        self.bookmarks_toolbar.setMovable(False)
        self.bookmarks_toolbar.setVisible(False)
        self.bookmarks_toolbar.setObjectName("BookmarksToolbar")
        
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
        """Refresh bookmarks toolbar with organized items, sorting options, and action buttons."""
        for action in self.bookmarks_toolbar.actions():
            self.bookmarks_toolbar.removeAction(action)
        
        # Add sorted bookmark buttons (MED-005)
        for name in sorted(self.bookmarks.keys()):
            url = self.bookmarks[name]
            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFlat(True)
            btn.setToolTip(f"{name}\n{url}")
            btn.clicked.connect(lambda checked, u=url: self.navigate_to(u))
            
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
        add_bookmark_btn.setToolTip("Bookmark current page")
        add_bookmark_btn.clicked.connect(self._add_current_bookmark)
        self.bookmarks_toolbar.addWidget(add_bookmark_btn)
        
        # Undo button if undo stack is not empty (MED-007)
        if self.bookmarks_history:
            undo_btn = QPushButton("↩️ Undo")
            undo_btn.setCursor(Qt.PointingHandCursor)
            undo_btn.setFlat(True)
            undo_btn.setToolTip("Undo bookmark change")
            undo_btn.clicked.connect(self.undo_bookmark_action)
            self.bookmarks_toolbar.addWidget(undo_btn)

    def _show_bookmark_context_menu(self, pos: QPoint, button: QPushButton, name: str) -> None:
        """Show context menu for bookmarks to allow deletion and undo."""
        menu = QMenu(self)
        delete_action = QAction("🗑️ Delete Bookmark", self)
        delete_action.triggered.connect(lambda: self._delete_bookmark(name))
        menu.addAction(delete_action)
        
        if self.bookmarks_history:
            undo_action = QAction("↩️ Undo Last Change", self)
            undo_action.triggered.connect(self.undo_bookmark_action)
            menu.addAction(undo_action)
            
        menu.exec_(button.mapToGlobal(pos))
        
    def _delete_bookmark(self, name: str) -> None:
        """Delete a bookmark with undo stack snapshot (MED-007)."""
        if name in self.bookmarks:
            self.bookmarks_history.append(self.bookmarks.copy())
            self.bookmarks_future.clear()
            del self.bookmarks[name]
            self._refresh_bookmarks_toolbar()
            self._save_bookmarks()
            self.log_action(f"🗑️ Bookmark deleted: {name}")

    def undo_bookmark_action(self) -> None:
        """Undo last bookmark action (MED-007)."""
        if self.bookmarks_history:
            self.bookmarks_future.append(self.bookmarks.copy())
            self.bookmarks = self.bookmarks_history.pop()
            self._refresh_bookmarks_toolbar()
            self._save_bookmarks()
            self.log_action("↩️ Restored previous bookmarks")
            self.show_toast("Restored previous bookmarks")

    def redo_bookmark_action(self) -> None:
        """Redo last undone bookmark action (MED-007)."""
        if self.bookmarks_future:
            self.bookmarks_history.append(self.bookmarks.copy())
            self.bookmarks = self.bookmarks_future.pop()
            self._refresh_bookmarks_toolbar()
            self._save_bookmarks()
            self.log_action("↪️ Reapplied bookmarks")
            self.show_toast("Reapplied bookmarks")

    def _create_tabs(self) -> None:
        """Create tab widget."""
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        
        self.new_tab_btn = QToolButton()
        self.new_tab_btn.setText("➕")
        self.new_tab_btn.setToolTip("New Tab (Ctrl+T)")
        self.new_tab_btn.setCursor(Qt.PointingHandCursor)
        self.new_tab_btn.setMinimumSize(30, 30)
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab())
        self.tabs.setCornerWidget(self.new_tab_btn, Qt.TopRightCorner)

    def _register_shortcuts(self) -> None:
        """Register all keyboard shortcuts centrally using ShortcutManager (MED-002)."""
        # Tab management
        self.shortcut_mgr.register("new_tab", "Ctrl+T", lambda: self.add_new_tab(), "Open a new tab")
        self.shortcut_mgr.register("close_tab", "Ctrl+W", self.close_current_tab, "Close current tab")
        self.shortcut_mgr.register("next_tab", "Ctrl+Tab", self.next_tab, "Switch to next tab")
        self.shortcut_mgr.register("prev_tab", "Ctrl+Shift+Tab", self.previous_tab, "Switch to previous tab")
        self.shortcut_mgr.register("reopen_tab", "Ctrl+Shift+T", self.reopen_closed_tab, "Reopen closed tab")
        
        # Navigation
        self.shortcut_mgr.register("focus_url", "Ctrl+L", self.focus_address_bar, "Focus address bar")
        self.shortcut_mgr.register("refresh", "F5", self.refresh_page, "Refresh page")
        self.shortcut_mgr.register("hard_refresh", "Ctrl+Shift+R", self.hard_refresh, "Hard refresh page")
        self.shortcut_mgr.register("show_history", "Ctrl+H", self.show_history, "Show history dialog")
        self.shortcut_mgr.register("nav_back", "Alt+Left", self.navigate_back, "Navigate back")
        self.shortcut_mgr.register("nav_forward", "Alt+Right", self.navigate_forward, "Navigate forward")
        self.shortcut_mgr.register("nav_home", "Alt+Home", self.go_to_home, "Go to home")
        
        # Features & Windows
        self.shortcut_mgr.register("show_downloads", "Ctrl+J", self.show_downloads, "Show download manager")
        self.shortcut_mgr.register("toggle_bookmarks", "Ctrl+B", self.toggle_bookmarks_bar, "Toggle bookmarks bar")
        self.shortcut_mgr.register("toggle_private", "Ctrl+Shift+P", self.toggle_private_mode, "Toggle private mode")
        self.shortcut_mgr.register("dev_tools", "F12", self.toggle_dev_tools, "Toggle developer tools")
        self.shortcut_mgr.register("zoom_in", "Ctrl+=", self.zoom_in, "Zoom in")
        self.shortcut_mgr.register("zoom_out", "Ctrl+-", self.zoom_out, "Zoom out")
        self.shortcut_mgr.register("zoom_reset", "Ctrl+0", self.reset_zoom, "Reset zoom")
        self.shortcut_mgr.register("find", "Ctrl+F", self.show_find_bar, "Find in page")
        self.shortcut_mgr.register("fullscreen", "F11", self.toggle_fullscreen, "Toggle fullscreen")
        self.shortcut_mgr.register("hide_find", "Esc", self.hide_find_bar, "Hide find bar")
        self.shortcut_mgr.register("undo_bookmark", "Ctrl+Z", self.undo_bookmark_action, "Undo bookmark change")

    def add_new_tab(self, url: Optional[str] = None, is_private: bool = False) -> Optional[Tab]:
        """Add a new browser tab with rate-limiting and maximum tab guard (HIGH-007).
        
        Args:
            url: Optional URL to load in the new tab
            is_private: True to open tab in Private Mode
            
        Returns:
            The newly created Tab instance or None if throttled/capped
        """
        # Guard max tabs
        if self.tabs.count() >= MAX_TABS:
            self.show_toast(f"Maximum tab limit reached ({MAX_TABS} tabs)")
            logger.warning(f"Tab creation rejected: maximum limit ({MAX_TABS}) reached")
            return None
            
        # Guard tab creation throttling (minimum 100ms interval)
        now = time.time()
        if now - self._last_tab_create_time < TAB_THROTTLE_SECONDS:
            return None
        self._last_tab_create_time = now
        
        is_tab_private = is_private or self.is_private_mode
        tab = Tab(self, url, is_private=is_tab_private)
        tab_title = "🔒 Private Tab" if is_tab_private else "New Tab"
            
        index = self.tabs.addTab(tab, tab_title)
        
        if is_tab_private:
            self.tabs.tabBar().setTabTextColor(index, QColor("#d9534f"))
            
        self.tabs.setCurrentIndex(index)
        self.URLBar.setFocus()
        
        if hasattr(self, 'default_zoom'):
            tab.browser.setZoomFactor(self.default_zoom)
            
        mode_str = "Private" if is_tab_private else "Normal"
        self.log_action(f"📑 New {mode_str} tab opened (#{index + 1})")
        return tab

    def close_tab(self, index: int) -> None:
        """Close tab at specified index and reclaim memory."""
        if self.tabs.count() > 1:
            tab = self.tabs.widget(index)
            if tab and hasattr(tab, 'browser'):
                url_str = tab.browser.url().toString()
                if url_str and url_str != self.homepage:
                    self.closed_tabs_stack.append(url_str)
            
            if tab and hasattr(tab, 'browser') and hasattr(self, 'dev_tools_view') and self.dev_tools_view.isVisible():
                try:
                    tab.browser.page().setDevToolsPage(None)
                except Exception:
                    pass
                    
            self.tabs.removeTab(index)
            if tab:
                tab.deleteLater()
            self.log_action(f"🗙 Tab closed")
        else:
            self.close()

    def close_current_tab(self) -> None:
        """Close the currently active tab."""
        self.close_tab(self.tabs.currentIndex())

    def reopen_closed_tab(self) -> None:
        """Reopen closed tabs sequentially from closed stack."""
        if hasattr(self, 'closed_tabs_stack') and self.closed_tabs_stack:
            url = self.closed_tabs_stack.pop()
            self.add_new_tab(url)
            self.log_action(f"📑 Reopened closed tab: {url}")
        else:
            self.show_toast("No closed tabs to reopen")

    def next_tab(self) -> None:
        """Switch to next tab."""
        current = self.tabs.currentIndex()
        next_index = (current + 1) % self.tabs.count()
        self.tabs.setCurrentIndex(next_index)

    def previous_tab(self) -> None:
        """Switch to previous tab."""
        current = self.tabs.currentIndex()
        prev_index = (current - 1) % self.tabs.count()
        self.tabs.setCurrentIndex(prev_index)

    def tab_changed(self, index: int) -> None:
        """Handle active tab change event."""
        if index >= 0:
            tab = self.tabs.widget(index)
            if tab and hasattr(tab, 'browser'):
                url = tab.browser.url().toString()
                self.URLBar.setText(url)
                self.URLBar.setCursorPosition(0)
                if hasattr(self, 'dev_tools_view') and self.dev_tools_view.isVisible():
                    tab.browser.page().setDevToolsPage(self.dev_tools_view.page())
                
                if hasattr(self, 'progress_bar') and self.progress_bar:
                    progress = getattr(tab, 'progress', 100)
                    self.progress_bar.setVisible(progress < 100)
                    self.progress_bar.setValue(progress)
                    
                if hasattr(self, 'zoom_indicator') and self.zoom_indicator:
                    zoom = tab.browser.zoomFactor()
                    self.zoom_indicator.setText(f"🔍 {int(zoom * 100)}%")
                    
                self.update_bookmark_button_state()

    def current_tab(self) -> Optional[Tab]:
        """Get the current active Tab widget."""
        return self.tabs.currentWidget()

    def navigate_back(self) -> None:
        """Navigate back in browser history."""
        if self.current_tab():
            self.current_tab().browser.back()

    def navigate_forward(self) -> None:
        """Navigate forward in browser history."""
        if self.current_tab():
            self.current_tab().browser.forward()

    def refresh_page(self) -> None:
        """Refresh current page."""
        if self.current_tab():
            self.current_tab().browser.reload()

    def hard_refresh(self) -> None:
        """Hard refresh bypassing cache."""
        if self.current_tab():
            self.current_tab().browser.triggerPageAction(QWebEnginePage.ReloadAndBypassCache)
            self.log_action("🔄 Hard refresh performed (bypassing cache)")
            self.show_toast("Hard refresh performed")

    def go_to_home(self) -> None:
        """Navigate to home page."""
        if self.current_tab():
            self.current_tab().browser.setUrl(QUrl(self.homepage))

    def load_url(self) -> None:
        """Load URL from address bar with input sanitization and local file protection (CRIT-003, HIGH-001)."""
        if not self.current_tab():
            return
            
        text = self.URLBar.text().strip()
        if not text:
            return
        
        try:
            # Check if it looks like a local file path
            is_local_file = False
            if os.path.isabs(text) or (len(text) > 1 and text[1] == ':' and text[0].isalpha()):
                is_local_file = True
                
                # Check sensitive system file access security rule (CRIT-003)
                if not is_safe_local_path(text):
                    logger.warning(f"Blocked attempt to access sensitive system path: {text}")
                    self.log_action(f"⛔ Access blocked: Protected system file")
                    QMessageBox.critical(self, "Security Restriction", 
                        f"Access to sensitive system file is blocked:\n{text}")
                    return
                    
                # Check file existence (CRIT-003)
                if not os.path.exists(text):
                    logger.warning(f"Local file does not exist: {text}")
                    self.log_action(f"❌ File not found: {text}")
                    self.show_toast(f"File not found:\n{os.path.basename(text)}")
                    return
                    
                url = QUrl.fromLocalFile(text)
            else:
                # Check if it's a search query or URL
                is_search = False
                if ' ' in text:
                    is_search = True
                elif text.startswith(('http://', 'https://', 'file://', 'view-source:', 'about:')):
                    is_search = False
                elif '.' in text and not text.endswith('.'):
                    is_search = False
                else:
                    is_search = True
                    
                if is_search:
                    # Sanitize search query with quote_plus (HIGH-001)
                    encoded_query = urllib.parse.quote_plus(text)
                    engine_template = SEARCH_ENGINES.get(self.current_engine, SEARCH_ENGINES["Google"])
                    search_url = engine_template.format(encoded_query)
                    url = QUrl(search_url)
                else:
                    if not text.startswith(('http://', 'https://', 'file://', 'view-source:', 'about:')):
                        text = 'https://' + text
                    url = QUrl(text)
            
            # Verify URL validity
            if not url.isValid():
                err_msg = format_error_message(url)
                self.log_action(f"❌ {err_msg}")
                self.show_toast(f"Invalid URL: {text[:40]}")
                return
                
            self.current_tab().browser.setUrl(url)
            self.add_to_history(url.toString())
            
        except Exception as e:
            err_msg = format_error_message(e)
            logger.error(f"URL load error: {err_msg}")
            self.log_action(f"❌ Error: {err_msg}")

    def navigate_to(self, url: str) -> None:
        """Navigate to specific URL string.
        
        Args:
            url: Target URL string
        """
        if self.current_tab() and url:
            qurl = QUrl(url)
            if qurl.isValid():
                self.current_tab().browser.setUrl(qurl)
                self.add_to_history(url)

    def set_search_engine(self, engine: str) -> None:
        """Set the default search engine.
        
        Args:
            engine: Engine name in SEARCH_ENGINES
        """
        if engine in SEARCH_ENGINES:
            self.current_engine = engine
            self.search_combo.setCurrentText(engine)
            self.log_action(f"🔍 Search engine: {engine}")

    def zoom_in(self) -> None:
        """Increase page zoom level."""
        if self.current_tab():
            current_zoom = self.current_tab().browser.zoomFactor()
            new_zoom = min(current_zoom + 0.1, 3.0)
            self.current_tab().browser.setZoomFactor(new_zoom)
            self.log_action(f"🔍 Zoom: {int(new_zoom * 100)}%")
            if hasattr(self, 'zoom_indicator') and self.zoom_indicator:
                self.zoom_indicator.setText(f"🔍 {int(new_zoom * 100)}%")

    def zoom_out(self) -> None:
        """Decrease page zoom level."""
        if self.current_tab():
            current_zoom = self.current_tab().browser.zoomFactor()
            new_zoom = max(current_zoom - 0.1, 0.5)
            self.current_tab().browser.setZoomFactor(new_zoom)
            self.log_action(f"🔍 Zoom: {int(new_zoom * 100)}%")
            if hasattr(self, 'zoom_indicator') and self.zoom_indicator:
                self.zoom_indicator.setText(f"🔍 {int(new_zoom * 100)}%")

    def reset_zoom(self) -> None:
        """Reset page zoom to 100%."""
        if self.current_tab():
            self.current_tab().browser.setZoomFactor(1.0)
            self.log_action("🔍 Zoom: 100%")
            if hasattr(self, 'zoom_indicator') and self.zoom_indicator:
                self.zoom_indicator.setText("🔍 100%")

    def show_downloads(self) -> None:
        """Show download manager window."""
        self.download_manager.show()
        self.download_manager.raise_()
        self.download_manager.activateWindow()

    def show_settings(self) -> None:
        """Show settings dialog using modularized SettingsDialog (CRIT-002)."""
        dialog = SettingsDialog(self)
        dialog.exec_()

    def toggle_bookmarks_bar(self) -> None:
        """Toggle bookmarks toolbar visibility."""
        visible = not self.bookmarks_toolbar.isVisible()
        self.bookmarks_toolbar.setVisible(visible)
        self.log_action(f"📚 Bookmarks {'shown' if visible else 'hidden'}")

    def toggle_private_mode(self) -> None:
        """Toggle private browsing mode."""
        self.is_private_mode = not self.is_private_mode
        self.private_indicator.setVisible(self.is_private_mode)
        
        if self.is_private_mode:
            self.private_indicator.setStyleSheet("color: #d9534f; font-weight: bold;")
            self.log_action("🔒 Private mode enabled - new tabs will browse privately")
        else:
            self.private_indicator.setStyleSheet("")
            self.log_action("🔒 Private mode disabled")

    def focus_address_bar(self) -> None:
        """Set focus and select all text in address bar."""
        self.URLBar.setFocus()
        self.URLBar.selectAll()

    def toggle_dev_tools(self) -> None:
        """Toggle developer tools visibility."""
        if not self.current_tab():
            return
        visible = not self.dev_tools_view.isVisible()
        self.dev_tools_view.setVisible(visible)
        if visible:
            self.current_tab().browser.page().setDevToolsPage(self.dev_tools_view.page())
        else:
            self.current_tab().browser.page().setDevToolsPage(None)
        self.log_action(f"👨‍💻 Dev Tools {'shown' if visible else 'hidden'}")

    def show_find_bar(self) -> None:
        """Show Find in Page bar."""
        self.find_bar.setVisible(True)
        self.find_input.setFocus()
        self.find_input.selectAll()

    def hide_find_bar(self) -> None:
        """Hide Find in Page bar."""
        self.find_bar.setVisible(False)
        if self.current_tab():
            self.current_tab().browser.findText("")

    def find_text(self, text: str) -> None:
        """Find text in active page."""
        if self.current_tab():
            self.current_tab().browser.findText(text)

    def find_next(self) -> None:
        """Find next match in active page."""
        if self.current_tab():
            self.current_tab().browser.findText(self.find_input.text())

    def toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
            self.log_action("🔳 Exited Fullscreen")
        else:
            self.showFullScreen()
            self.log_action("🔲 Entered Fullscreen (Press F11 to exit)")

    def toggle_web_dark_mode(self) -> None:
        """Toggle Web Dark Mode globally and apply clean CSS injection to all tabs (MED-001)."""
        self.web_dark_mode_active = not self.web_dark_mode_active
        mode_str = "Enabled" if self.web_dark_mode_active else "Disabled"
        self.log_action(f"🌓 Web Dark Mode {mode_str}")
        self.show_toast(f"Web Dark Mode {mode_str}")
        
        if self.web_dark_mode_active:
            self.web_dark_btn.setStyleSheet(f"background-color: {self.current_theme_color()}; border-radius: 18px;")
        else:
            self.web_dark_btn.setStyleSheet("")
            
        js_enable = """
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
        """Show browsing history dialog using modularized HistoryDialog (CRIT-002, MED-008)."""
        dialog = HistoryDialog(self)
        dialog.exec_()

    def _add_current_bookmark(self) -> None:
        """Add current page to bookmarks with undo stack snapshot (MED-007)."""
        if not self.current_tab():
            return
            
        url = self.current_tab().browser.url().toString()
        title = getattr(self.current_tab(), 'title', "Bookmark") or "Bookmark"
        
        self.bookmarks_history.append(self.bookmarks.copy())
        self.bookmarks_future.clear()
        
        self.bookmarks[title] = url
        self._refresh_bookmarks_toolbar()
        self._save_bookmarks()
        self.log_action(f"⭐ Bookmarked: {title}")
        self.show_toast(f"Bookmarked: {title}")

    def apply_theme(self, theme_name: str) -> None:
        """Apply theme styling using ThemeManager (CRIT-002, HIGH-005)."""
        self.current_theme = ThemeManager.apply_to_window(self, theme_name)
        logger.info(f"Theme applied: {self.current_theme}")
        self.log_action(f"🎨 Theme: {self.current_theme}")

    def log_action(self, message: str) -> None:
        """Log action to in-memory console, persistent debug.log, and status bar (MED-010)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Persist log entry to debug.log file (MED-010)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + "\n")
        except Exception:
            pass
        
        # Display in-memory console
        try:
            if hasattr(self, 'console') and self.console:
                self.console.appendPlainText(log_entry)
                scrollbar = self.console.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass
        
        # Display status bar
        try:
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(message)
        except Exception:
            pass

    def add_to_history(self, url: str) -> None:
        """Add URL to browsing history with bounded size and debounced disk save (HIGH-006, MED-011)."""
        current = self.current_tab()
        is_tab_private = current.is_private if current else False
        
        if not self.is_private_mode and not is_tab_private and url and url.startswith(('http://', 'https://', 'file://')):
            self.history.append(url)
            # Bound history size to HISTORY_MAX_SIZE
            if len(self.history) > HISTORY_MAX_SIZE:
                self.history = self.history[-HISTORY_MAX_SIZE:]
            
            # Debounce disk write with singleShot timer to prevent disk thrashing (MED-011)
            self._history_dirty = True
            if self._history_save_timer is None:
                self._history_save_timer = QTimer(self)
                self._history_save_timer.setSingleShot(True)
                self._history_save_timer.timeout.connect(self._flush_history)
            self._history_save_timer.start(HISTORY_SAVE_DEBOUNCE_MS)

    def _flush_history(self) -> None:
        """Synchronously flush history buffer to file."""
        if self._history_dirty:
            self._save_history()
            self._history_dirty = False

    def _save_history(self) -> None:
        """Save browsing history to file."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f)
        except Exception as e:
            logger.error(f"Error saving history: {e}")

    def _load_history(self) -> None:
        """Load browsing history from file with error recovery (MED-009)."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                    if not isinstance(self.history, list):
                        self.history = []
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Corrupted history file: {e}")
            self._recover_corrupted_file(self.history_file)
            self.history = []

    def _save_bookmarks(self) -> None:
        """Save bookmarks to file."""
        try:
            with open(self.bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump(self.bookmarks, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving bookmarks: {e}")

    def _load_bookmarks(self) -> None:
        """Load bookmarks from file with error recovery (MED-009)."""
        try:
            if self.bookmarks_file.exists():
                with open(self.bookmarks_file, 'r', encoding='utf-8') as f:
                    saved_bookmarks = json.load(f)
                    if isinstance(saved_bookmarks, dict):
                        self.bookmarks.update(saved_bookmarks)
            self._refresh_bookmarks_toolbar()
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Corrupted bookmarks file: {e}")
            self._recover_corrupted_file(self.bookmarks_file)

    def contextMenuEvent(self, event: Any) -> None:
        """Handle right-click context menu."""
        menu = QMenu(self)
        
        new_tab_action = QAction("📑 New Tab", self)
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        menu.addAction(new_tab_action)
        
        close_tab_action = QAction("🗙 Close Tab", self)
        close_tab_action.triggered.connect(self.close_current_tab)
        menu.addAction(close_tab_action)
        
        menu.addSeparator()
        
        # Theme submenu
        theme_menu = menu.addMenu("🎨 Theme")
        for theme_name in THEMES.keys():
            theme_action = QAction(theme_name, self)
            theme_action.triggered.connect(lambda _, t=theme_name: self.apply_theme(t))
            theme_menu.addAction(theme_action)
        
        menu.addSeparator()
        
        # Log console toggle
        toggle_log_action = QAction("📝 Toggle Log Console", self)
        toggle_log_action.triggered.connect(self.toggle_log_console)
        menu.addAction(toggle_log_action)
        
        # Privacy toggle
        private_action = QAction(
            f"{'🔓 Disable' if self.is_private_mode else '🔒 Enable'} Private Mode",
            self
        )
        private_action.triggered.connect(self.toggle_private_mode)
        menu.addAction(private_action)
        
        menu.exec_(event.globalPos())

    def toggle_log_console(self) -> None:
        """Toggle log console visibility."""
        visible = not self.console.isVisible()
        self.console.setVisible(visible)
        self.log_action(f"📝 Log console {'shown' if visible else 'hidden'}")

    def handle_ssl_error(self, error: Any) -> bool:
        """Handle SSL certificate error dialog prompt with explicit user consent."""
        dialog = QDialog(self)
        dialog.setWindowTitle("🔒 SSL Certificate Error")
        layout = QVBoxLayout()
        
        host_str = error.url().host() if hasattr(error, 'url') else "Unknown"
        desc_str = error.errorDescription() if hasattr(error, 'errorDescription') else "SSL Certificate Validation Failed"
        
        message = QLabel(
            f"<b>SSL Certificate Error</b><br>"
            f"<code>{desc_str}</code><br><br>"
            f"Website: <code>{host_str}</code><br><br>"
            f"Do you want to proceed anyway?"
        )
        layout.addWidget(message)
        
        btn_layout = QHBoxLayout()
        proceed_btn = QPushButton("✓ Proceed")
        cancel_btn = QPushButton("✕ Cancel")
        
        proceed_btn.clicked.connect(lambda: dialog.accept())
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(proceed_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        accepted = (dialog.exec_() == QDialog.Accepted)
        if accepted:
            error.ignoreCertificateError()
            logger.info(f"SSL certificate error ignored for {host_str}")
        return accepted

    def on_download_requested(self, download: QWebEngineDownloadItem) -> None:
        """Handle download requests with rigorous error checking and notifications (CRIT-004)."""
        try:
            url_str = download.url().toString()[:60]
            self.log_action(f"📥 Download requested: {url_str}...")
            
            raw_suggested = download.path() or download.url().path().split('/')[-1] or 'download'
            suggested = os.path.basename(raw_suggested)
            default_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            default_path = os.path.join(default_dir, suggested)
            
            path, _ = QFileDialog.getSaveFileName(
                self, 
                'Save File As', 
                default_path,
                "All Files (*.*)"
            )
            
            if not path:
                download.cancel()
                self.log_action("📥 Download cancelled by user")
                return
            
            try:
                download.setPath(path)
            except Exception as e:
                logger.error(f"Failed to set download path '{path}': {e}")
                QMessageBox.warning(
                    self, 
                    "Download Error", 
                    f"Could not save file to:\n{path}\n\nError: {str(e)}"
                )
                download.cancel()
                return
            
            download.accept()
            
            if hasattr(self, 'download_manager') and self.download_manager:
                self.download_manager.add_download(download)
                self.download_manager.show()
                self.log_action(f"✓ Download started: {os.path.basename(path)}")
                
        except Exception as e:
            err_msg = format_error_message(e)
            logger.error(f"Download request error: {err_msg}")
            self.log_action(f"❌ Download error: {err_msg}")
            QMessageBox.warning(self, "Download Error", f"An error occurred while processing download:\n{err_msg}")

    def save_session(self) -> None:
        """Save session data including URL, title, and zoom factor per tab (MED-004)."""
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
                zoom = tab.browser.zoomFactor()
                session_data["tabs"].append({
                    "url": url,
                    "title": title,
                    "zoom": zoom
                })
        
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)
            logger.info("Session saved")
        except Exception as e:
            logger.error(f"Error saving session: {e}")

    def restore_session(self) -> None:
        """Restore previous session with URL validation, zoom levels, and corrupted file recovery (HIGH-002, MED-004, MED-009)."""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                # Restore theme
                theme = session_data.get("theme", self.current_theme)
                self.apply_theme(theme)
                
                # Restore tabs
                tabs_data = session_data.get("tabs", [])
                if tabs_data and isinstance(tabs_data, list):
                    while self.tabs.count() > 0:
                        tab = self.tabs.widget(0)
                        self.tabs.removeTab(0)
                        if tab:
                            tab.deleteLater()
                            
                    for tab_data in tabs_data:
                        raw_url = tab_data.get("url", "")
                        # Validate URL before restoring (HIGH-002)
                        if raw_url and (raw_url.startswith(('http://', 'https://', 'file://', 'about:')) or os.path.exists(raw_url)):
                            new_tab = self.add_new_tab(raw_url)
                            zoom_val = tab_data.get("zoom")
                            if new_tab and zoom_val:
                                try:
                                    new_tab.browser.setZoomFactor(float(zoom_val))
                                except Exception:
                                    pass
                        else:
                            logger.warning(f"Skipping invalid URL during session restore: {raw_url}")
                    
                    current_tab_index = session_data.get("current_tab", 0)
                    if 0 <= current_tab_index < self.tabs.count():
                        self.tabs.setCurrentIndex(current_tab_index)
                
                logger.info("Session restored successfully")
                self.log_action("✓ Session restored")
                
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.error(f"Corrupted session file: {e}")
            self._recover_corrupted_file(self.session_file)
            
        # Ensure at least one tab is open
        if self.tabs.count() == 0:
            self.add_new_tab()

    def closeEvent(self, event: Any) -> None:
        """Handle window close event, flush pending history, and save settings."""
        self._flush_history()
        
        if hasattr(self, 'clear_on_exit') and self.clear_on_exit:
            self.history.clear()
            self._save_history()
            logger.info("Browsing history cleared on exit")
            
        self.save_session()
        self._save_settings()
        logger.info(f"{APP_NAME} closed")
        event.accept()

    def handle_html5_fullscreen(self, request: Any) -> None:
        """Handle HTML5 fullscreen requests from web content."""
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
        """Display an overlay toast notification."""
        try:
            ToastNotification(message, self)
        except Exception as e:
            logger.error(f"Error showing toast: {e}")

    def update_bookmark_button_state(self) -> None:
        """Update bookmark button visual state based on whether current URL is in bookmarks."""
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
        """Get current theme accent color hex string."""
        return ThemeManager.get_accent_color(self.current_theme)
