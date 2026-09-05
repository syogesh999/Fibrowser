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
                             QMenu, QHBoxLayout, QLabel, QDialog, QApplication,
                             QFileDialog, QProgressBar, QStyle, QShortcut, QToolButton,
                             QListWidget, QListWidgetItem, QComboBox, QCheckBox, QFormLayout,
                             QMessageBox, QPlainTextEdit, QSplitter)

# Local package imports
from fibrowser.config import (DEFAULT_HOME_PAGE, DEFAULT_SEARCH_ENGINE, APP_NAME, APP_VERSION, 
                              WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, SEARCH_ENGINES, THEMES, 
                              MAX_TABS, TAB_THROTTLE_SECONDS, HISTORY_MAX_SIZE, 
                              HISTORY_SAVE_DEBOUNCE_MS, PROGRESS_BAR_HEIGHT, DEFAULT_ZOOM, 
                              LOG_FILE_NAME, get_icon, format_error_message, is_safe_local_path)
from fibrowser.ui.widgets import AnimatedButton, ToastNotification
from fibrowser.ui.downloads import DownloadManager
from fibrowser.ui.tab import Tab
from fibrowser.ui.shortcut_manager import ShortcutManager
from fibrowser.ui.theme_manager import ThemeManager
from fibrowser.ui.dialogs.settings_dialog import SettingsDialog
from fibrowser.ui.dialogs.history_dialog import HistoryDialog
from fibrowser.ui.dialogs.welcome_dialog import WelcomeDialog

logger = logging.getLogger(__name__)

class Window(QMainWindow):
    """Main browser window coordinating tabs, toolbar, settings, downloads, and security."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize main browser window and subsystems."""
        super(Window, self).__init__(*args, **kwargs)
        
        # Window configuration
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        try:
            self.setWindowIcon(get_icon("fibrowser.ico", QStyle.SP_ComputerIcon))
        except Exception:
            self.setWindowIcon(get_icon("fibrowser.png", QStyle.SP_ComputerIcon))
        
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
        self.current_engine: str = DEFAULT_SEARCH_ENGINE
        self.bookmarks: Dict[str, str] = {}
        self.bookmarks_history: List[Dict[str, str]] = []
        self.bookmarks_future: List[Dict[str, str]] = []
        self.history: List[str] = []
        self.closed_tabs_stack: List[str] = []
        self.web_dark_mode_active: bool = False
        self.default_zoom: float = DEFAULT_ZOOM
        self.js_enabled: bool = True
        self.clear_on_exit: bool = False
        self.first_run_completed: bool = False
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
        
        # Check first run experience
        if not self.first_run_completed:
            QTimer.singleShot(400, self.show_welcome_dialog)
            
        logger.info(f"{APP_NAME} v{APP_VERSION} started")
        self.log_action("🚀 Browser started successfully")

    def show_welcome_dialog(self) -> None:
        """Display first-run welcome dialog to configure initial preferences."""
        dialog = WelcomeDialog(self, self)
        dialog.exec_()

    def get_private_profile(self) -> QWebEngineProfile:
        """Get or create the off-the-record profile for private browsing with strict memory isolation."""
        if not self._private_profile:
            self._private_profile = QWebEngineProfile(self)
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
        self.current_engine = DEFAULT_SEARCH_ENGINE
        self.current_theme = "Dark"
        self.default_zoom = DEFAULT_ZOOM
        self.js_enabled = True
        self.clear_on_exit = False
        self.first_run_completed = False
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.homepage = data.get("homepage", DEFAULT_HOME_PAGE)
                    self.current_engine = data.get("search_engine", DEFAULT_SEARCH_ENGINE)
                    self.current_theme = ThemeManager.validate_theme_name(data.get("theme", "Dark"))
                    self.default_zoom = float(data.get("default_zoom", DEFAULT_ZOOM))
                    self.js_enabled = bool(data.get("javascript_enabled", True))
                    self.clear_on_exit = bool(data.get("clear_on_exit", False))
                    self.first_run_completed = bool(data.get("first_run_completed", False))
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
                "clear_on_exit": self.clear_on_exit,
                "first_run_completed": self.first_run_completed
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
        self.find_bar.setObjectName("find_bar")
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
        
        # Address bar with custom context menu
        self.URLBar = QLineEdit()
        self.URLBar.setPlaceholderText("🔍 Search Google or enter URL (e.g. msn.com, calc 25*25)...")
        self.URLBar.returnPressed.connect(self.load_url)
        self.URLBar.setClearButtonEnabled(True)
        self.URLBar.setMaximumHeight(36)
        self.URLBar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.URLBar.customContextMenuRequested.connect(self._show_urlbar_context_menu)
        
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

    def _show_urlbar_context_menu(self, pos: QPoint) -> None:
        """Show extended context menu with Paste & Go, Paste & Search, Copy URL."""
        menu = self.URLBar.createStandardContextMenu()
        menu.addSeparator()
        
        paste_go_act = menu.addAction("📋 Paste and Go")
        paste_search_act = menu.addAction("🔍 Paste and Search")
        copy_url_act = menu.addAction("🔗 Copy Current Page URL")
        
        clipboard = QApplication.clipboard()
        clip_text = clipboard.text().strip()
        
        paste_go_act.setEnabled(bool(clip_text))
        paste_search_act.setEnabled(bool(clip_text))
        
        action = menu.exec_(self.URLBar.mapToGlobal(pos))
        if action == paste_go_act and clip_text:
            self.URLBar.setText(clip_text)
            self.load_url()
        elif action == paste_search_act and clip_text:
            template = SEARCH_ENGINES.get(self.current_engine, SEARCH_ENGINES["Google"])
            search_url = template.format(urllib.parse.quote_plus(clip_text))
            self.URLBar.setText(search_url)
            self.navigate_to(search_url)
        elif action == copy_url_act:
            current = self.current_tab()
            if current and hasattr(current, 'browser'):
                clipboard.setText(current.browser.url().toString())
                self.show_toast("🔗 URL copied to clipboard")

    def _create_bookmarks_toolbar(self) -> None:
        """Create bookmarks toolbar."""
        self.bookmarks_toolbar = QToolBar('Bookmarks')
        self.bookmarks_toolbar.setMovable(False)
        self.bookmarks_toolbar.setVisible(False)
        self.bookmarks_toolbar.setObjectName("BookmarksToolbar")
        
        default_bookmarks = {
            "🔍 Google": "https://www.google.com",
            "📰 MSN": "https://www.msn.com",
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
        
        # Undo button if undo stack is not empty
        if self.bookmarks_history:
            undo_btn = QPushButton("↩️ Undo")
            undo_btn.setCursor(Qt.PointingHandCursor)
            undo_btn.setFlat(True)
            undo_btn.setToolTip("Undo bookmark change (Ctrl+Z)")
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
        """Delete a bookmark with undo stack snapshot."""
        if name in self.bookmarks:
            self.bookmarks_history.append(self.bookmarks.copy())
            self.bookmarks_future.clear()
            del self.bookmarks[name]
            self._refresh_bookmarks_toolbar()
            self._save_bookmarks()
            self.log_action(f"🗑️ Bookmark deleted: {name}")

    def undo_bookmark_action(self) -> None:
        """Undo last bookmark action."""
        if self.bookmarks_history:
            self.bookmarks_future.append(self.bookmarks.copy())
            self.bookmarks = self.bookmarks_history.pop()
            self._refresh_bookmarks_toolbar()
            self._save_bookmarks()
            self.log_action("↩️ Restored previous bookmarks")
            self.show_toast("Restored previous bookmarks")

    def redo_bookmark_action(self) -> None:
        """Redo last undone bookmark action."""
        if self.bookmarks_future:
            self.bookmarks_history.append(self.bookmarks.copy())
            self.bookmarks = self.bookmarks_future.pop()
            self._refresh_bookmarks_toolbar()
            self._save_bookmarks()
            self.log_action("↪️ Reapplied bookmarks")
            self.show_toast("Reapplied bookmarks")

    def _create_tabs(self) -> None:
        """Create tab widget with custom context menu for tab management."""
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        
        # Right-click context menu on tabs
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self._show_tab_context_menu)
        
        self.new_tab_btn = QToolButton()
        self.new_tab_btn.setText("➕")
        self.new_tab_btn.setToolTip("New Tab (Ctrl+T)")
        self.new_tab_btn.setCursor(Qt.PointingHandCursor)
        self.new_tab_btn.setMinimumSize(30, 30)
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab())
        self.tabs.setCornerWidget(self.new_tab_btn, Qt.TopRightCorner)

    def _show_tab_context_menu(self, pos: QPoint) -> None:
        """Show rich tab context menu on right clicking tabs."""
        tab_index = self.tabs.tabBar().tabAt(pos)
        if tab_index == -1:
            return
            
        tab = self.tabs.widget(tab_index)
        menu = QMenu(self)
        
        dup_act = menu.addAction("📑 Duplicate Tab")
        
        is_pinned = getattr(tab, 'is_pinned', False)
        pin_act = menu.addAction("📍 Unpin Tab" if is_pinned else "📌 Pin Tab")
        
        is_muted = getattr(tab, 'is_muted', False)
        mute_act = menu.addAction("🔊 Unmute Tab" if is_muted else "🔇 Mute Tab")
        
        menu.addSeparator()
        reload_act = menu.addAction("🔄 Reload Tab")
        close_act = menu.addAction("🗙 Close Tab")
        close_others_act = menu.addAction("🗙 Close Other Tabs")
        close_right_act = menu.addAction("➡️ Close Tabs to the Right")
        
        if self.closed_tabs_stack:
            menu.addSeparator()
            reopen_act = menu.addAction("↩️ Reopen Closed Tab")
        else:
            reopen_act = None
            
        action = menu.exec_(self.tabs.mapToGlobal(pos))
        if not action:
            return
            
        if action == dup_act:
            if hasattr(tab, 'browser'):
                self.add_new_tab(tab.browser.url().toString(), is_private=getattr(tab, 'is_private', False))
        elif action == pin_act:
            if hasattr(tab, 'set_pinned'):
                tab.set_pinned(not is_pinned)
        elif action == mute_act:
            if hasattr(tab, 'set_muted'):
                tab.set_muted(not is_muted)
        elif action == reload_act:
            if hasattr(tab, 'browser'):
                tab.browser.reload()
        elif action == close_act:
            self.close_tab(tab_index)
        elif action == close_others_act:
            self._close_other_tabs(tab_index)
        elif action == close_right_act:
            self._close_tabs_to_right(tab_index)
        elif action == reopen_act:
            self.reopen_closed_tab()

    def _close_other_tabs(self, keep_index: int) -> None:
        """Close all tabs except the specified index (preserving pinned tabs)."""
        keep_widget = self.tabs.widget(keep_index)
        for i in reversed(range(self.tabs.count())):
            w = self.tabs.widget(i)
            if w != keep_widget and not getattr(w, 'is_pinned', False):
                self.close_tab(i)

    def _close_tabs_to_right(self, from_index: int) -> None:
        """Close all tabs to the right of the specified index."""
        for i in reversed(range(from_index + 1, self.tabs.count())):
            w = self.tabs.widget(i)
            if not getattr(w, 'is_pinned', False):
                self.close_tab(i)

    def duplicate_current_tab(self) -> None:
        """Duplicate currently active tab."""
        current = self.current_tab()
        if current and hasattr(current, 'browser'):
            self.add_new_tab(current.browser.url().toString(), is_private=getattr(current, 'is_private', False))

    def _register_shortcuts(self) -> None:
        """Register all keyboard shortcuts centrally using ShortcutManager."""
        # Tab management
        self.shortcut_mgr.register("new_tab", "Ctrl+T", lambda: self.add_new_tab(), "Open a new tab")
        self.shortcut_mgr.register("close_tab", "Ctrl+W", self.close_current_tab, "Close current tab")
        self.shortcut_mgr.register("next_tab", "Ctrl+Tab", self.next_tab, "Switch to next tab")
        self.shortcut_mgr.register("prev_tab", "Ctrl+Shift+Tab", self.previous_tab, "Switch to previous tab")
        self.shortcut_mgr.register("reopen_tab", "Ctrl+Shift+T", self.reopen_closed_tab, "Reopen closed tab")
        self.shortcut_mgr.register("dup_tab", "Ctrl+K", self.duplicate_current_tab, "Duplicate current tab")
        
        # Navigation
        self.shortcut_mgr.register("focus_url", "Ctrl+L", self.focus_address_bar, "Focus address bar")
        self.shortcut_mgr.register("refresh", "F5", self.refresh_page, "Refresh page")
        self.shortcut_mgr.register("hard_refresh", "Ctrl+Shift+R", self.hard_refresh, "Hard refresh page")
        self.shortcut_mgr.register("show_history", "Ctrl+H", self.show_history, "Show history dialog")
        self.shortcut_mgr.register("nav_back", "Alt+Left", self.navigate_back, "Navigate back")
        self.shortcut_mgr.register("nav_forward", "Alt+Right", self.navigate_forward, "Navigate forward")
        self.shortcut_mgr.register("nav_home", "Alt+Home", self.go_to_home, "Go to home")
        
        # Page Actions
        self.shortcut_mgr.register("view_source", "Ctrl+U", self.view_page_source, "View page source")
        self.shortcut_mgr.register("save_page", "Ctrl+S", self.save_page_as, "Save page as HTML")
        self.shortcut_mgr.register("print_page", "Ctrl+P", self.print_page, "Print page to PDF")
        
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

    def view_page_source(self) -> None:
        """Open current page HTML source code in a reader dialog."""
        current = self.current_tab()
        if current and hasattr(current, 'browser'):
            current.browser.page().toHtml(self._display_source_code)

    def _display_source_code(self, html: str) -> None:
        """Display source code dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Page Source Viewer")
        dialog.setWindowIcon(get_icon("fibrowser.ico"))
        dialog.resize(850, 600)
        layout = QVBoxLayout(dialog)
        edit = QPlainTextEdit(dialog)
        edit.setReadOnly(True)
        edit.setPlainText(html)
        edit.setStyleSheet("font-family: Consolas, monospace; font-size: 13px;")
        layout.addWidget(edit)
        dialog.exec_()

    def save_page_as(self) -> None:
        """Save current page as HTML file."""
        current = self.current_tab()
        if not current or not hasattr(current, 'browser'):
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Page As", "page.html", "HTML Files (*.html *.htm);;All Files (*)")
        if path:
            current.browser.page().save(path, QWebEnginePage.SingleHtmlSaveFormat)
            self.show_toast(f"Page saved to {os.path.basename(path)}")

    def print_page(self) -> None:
        """Print current page to PDF file."""
        current = self.current_tab()
        if not current or not hasattr(current, 'browser'):
            return
        path, _ = QFileDialog.getSaveFileName(self, "Print to PDF", "document.pdf", "PDF Files (*.pdf)")
        if path:
            current.browser.page().printToPdf(path)
            self.show_toast(f"Page exported as PDF to {os.path.basename(path)}")

    def add_new_tab(self, url: Optional[str] = None, is_private: bool = False) -> Optional[Tab]:
        """Add a new browser tab with rate-limiting and maximum tab guard."""
        if self.tabs.count() >= MAX_TABS:
            self.show_toast(f"Maximum tab limit reached ({MAX_TABS} tabs)")
            logger.warning(f"Tab creation rejected: maximum limit ({MAX_TABS}) reached")
            return None
            
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
            self.log_action("🗙 Tab closed")
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
        """Load URL from address bar with input sanitization, math evaluator, and quick commands."""
        if not self.current_tab():
            return
            
        raw_text = self.URLBar.text().strip()
        if not raw_text:
            return
        
        # 1. Quick Math Calculation check (e.g. "calc 25 * 25" or "= 10 + 5")
        math_expr = None
        if raw_text.startswith("calc "):
            math_expr = raw_text[5:].strip()
        elif raw_text.startswith("= "):
            math_expr = raw_text[2:].strip()
        elif raw_text.startswith("=") and len(raw_text) > 1:
            math_expr = raw_text[1:].strip()
            
        if math_expr:
            try:
                allowed = set("0123456789+-*/().% ")
                if all(c in allowed for c in math_expr):
                    result = eval(math_expr, {"__builtins__": None}, {})
                    self.show_toast(f"🧮 Result: {result}")
                    self.log_action(f"Calculator: {math_expr} = {result}")
                    return
            except Exception as e:
                self.show_toast(f"Calculation Error: {e}")
                return

        # 2. Quick Command shortcuts
        cmd_lower = raw_text.lower()
        if cmd_lower in ("open settings", "settings"):
            self.show_settings()
            return
        elif cmd_lower in ("open downloads", "downloads"):
            self.show_downloads()
            return
        elif cmd_lower in ("open history", "history"):
            self.show_history()
            return
        elif cmd_lower in ("open bookmarks", "bookmarks"):
            self.toggle_bookmarks_bar()
            return

        # 3. Standard URL Navigation or Search Query
        try:
            is_local_file = False
            if os.path.isabs(raw_text) or (len(raw_text) > 1 and raw_text[1] == ':' and raw_text[0].isalpha()):
                is_local_file = True
                
                if not is_safe_local_path(raw_text):
                    logger.warning(f"Blocked attempt to access sensitive system path: {raw_text}")
                    self.log_action("⛔ Access blocked: Protected system file")
                    QMessageBox.critical(self, "Security Restriction", 
                        f"Access to sensitive system file is blocked:\n{raw_text}")
                    return
                    
                if not os.path.exists(raw_text):
                    logger.warning(f"Local file does not exist: {raw_text}")
                    self.log_action(f"❌ File not found: {raw_text}")
                    self.show_toast(f"File not found:\n{os.path.basename(raw_text)}")
                    return
                    
                url = QUrl.fromLocalFile(raw_text)
            else:
                is_search = False
                if ' ' in raw_text:
                    is_search = True
                elif raw_text.startswith(('http://', 'https://', 'file://', 'view-source:', 'about:')):
                    is_search = False
                elif '.' in raw_text and not raw_text.endswith('.'):
                    is_search = False
                else:
                    is_search = True
                    
                if is_search:
                    encoded_query = urllib.parse.quote_plus(raw_text)
                    engine_template = SEARCH_ENGINES.get(self.current_engine, SEARCH_ENGINES["Google"])
                    search_url = engine_template.format(encoded_query)
                    url = QUrl(search_url)
                else:
                    if not raw_text.startswith(('http://', 'https://', 'file://', 'view-source:', 'about:')):
                        raw_text = 'https://' + raw_text
                    url = QUrl(raw_text)
            
            if not url.isValid():
                err_msg = format_error_message(url)
                self.log_action(f"❌ {err_msg}")
                self.show_toast(f"Invalid URL: {raw_text[:40]}")
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
            self.current_tab().browser.setZoomFactor(DEFAULT_ZOOM)
            self.log_action("🔍 Zoom reset to 100%")
            if hasattr(self, 'zoom_indicator') and self.zoom_indicator:
                self.zoom_indicator.setText("🔍 100%")

    def show_find_bar(self) -> None:
        """Display page search find bar."""
        self.find_bar.setVisible(True)
        self.find_input.setFocus()
        self.find_input.selectAll()

    def hide_find_bar(self) -> None:
        """Hide find bar and clear search highlights."""
        self.find_bar.setVisible(False)
        if self.current_tab():
            self.current_tab().browser.findText("")

    def find_text(self, text: str) -> None:
        """Search text in page content."""
        if self.current_tab():
            self.current_tab().browser.findText(text)

    def find_next(self) -> None:
        """Find next occurrence of text in page."""
        if self.current_tab():
            self.current_tab().browser.findText(self.find_input.text())

    def toggle_fullscreen(self) -> None:
        """Toggle window fullscreen display mode."""
        if self.isFullScreen():
            self.showNormal()
            self.log_action("📺 Exited fullscreen")
        else:
            self.showFullScreen()
            self.log_action("📺 Entered fullscreen")

    def toggle_bookmarks_bar(self) -> None:
        """Toggle bookmarks bar visibility."""
        is_visible = not self.bookmarks_toolbar.isVisible()
        self.bookmarks_toolbar.setVisible(is_visible)
        state_str = "shown" if is_visible else "hidden"
        self.log_action(f"⭐ Bookmarks toolbar {state_str}")

    def toggle_private_mode(self) -> None:
        """Toggle private browsing mode."""
        self.is_private_mode = not self.is_private_mode
        self.private_indicator.setVisible(self.is_private_mode)
        
        if self.is_private_mode:
            self.private_btn.setStyleSheet("background-color: #d9534f; border-radius: 18px;")
            self.show_toast("🔒 Private Browsing Enabled")
            self.log_action("🔒 Switched to Private Mode")
        else:
            self.private_btn.setStyleSheet("")
            self.show_toast("🔓 Private Browsing Disabled")
            self.log_action("🔓 Switched to Normal Mode")
            
        self.add_new_tab(is_private=self.is_private_mode)

    def toggle_dev_tools(self) -> None:
        """Toggle embedded WebEngine developer console."""
        if not hasattr(self, 'dev_tools_view'):
            return
            
        is_visible = not self.dev_tools_view.isVisible()
        self.dev_tools_view.setVisible(is_visible)
        
        current = self.current_tab()
        if current and hasattr(current, 'browser'):
            if is_visible:
                current.browser.page().setDevToolsPage(self.dev_tools_view.page())
                self.log_action("🛠️ DevTools opened")
            else:
                current.browser.page().setDevToolsPage(None)
                self.log_action("🛠️ DevTools closed")

    def toggle_web_dark_mode(self) -> None:
        """Toggle smart Web Dark Mode CSS script injection across tabs."""
        self.web_dark_mode_active = not self.web_dark_mode_active
        
        if self.web_dark_mode_active:
            self.web_dark_btn.setStyleSheet("background-color: #4a148c; border-radius: 18px;")
            self.show_toast("🌓 Web Dark Mode Enabled")
            self.log_action("🌓 Web Dark Mode turned ON")
            
            # Apply to all currently open tabs
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if tab and hasattr(tab, 'on_load_finished'):
                    tab.on_load_finished(True)
        else:
            self.web_dark_btn.setStyleSheet("")
            self.show_toast("☀️ Web Dark Mode Disabled")
            self.log_action("☀️ Web Dark Mode turned OFF")
            
            # Remove dark stylesheet from all open tabs
            js = """
            (function() {
                var el = document.getElementById('fibrowser-dark-mode');
                if (el) el.remove();
            })();
            """
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if tab and hasattr(tab, 'browser'):
                    tab.browser.page().runJavaScript(js)

    def show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self, self)
        dialog.exec_()

    def show_history(self) -> None:
        """Show browsing history dialog."""
        dialog = HistoryDialog(self, self)
        dialog.exec_()

    def show_downloads(self) -> None:
        """Show download manager dialog."""
        self.download_manager.show_manager()

    def focus_address_bar(self) -> None:
        """Focus and select all address bar text."""
        self.URLBar.setFocus()
        self.URLBar.selectAll()

    def apply_theme(self, theme_name: str) -> None:
        """Apply custom CSS theme stylesheet."""
        theme_name = ThemeManager.validate_theme_name(theme_name)
        self.current_theme = theme_name
        stylesheet = ThemeManager.generate_stylesheet(theme_name)
        self.setStyleSheet(stylesheet)
        self.log_action(f"🎨 Theme changed: {theme_name}")

    def log_action(self, action: str) -> None:
        """Record user action to status bar, console widget, and disk log file."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {action}"
        
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(action[:60])
            
        if hasattr(self, 'console') and self.console:
            self.console.appendPlainText(log_entry)
            
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{log_entry}\n")
        except Exception:
            pass

    def add_to_history(self, url: str) -> None:
        """Add URL to browsing history and schedule debounced save."""
        current = self.current_tab()
        if current and getattr(current, 'is_private', False):
            return
            
        if self.is_private_mode:
            return
            
        if url and url != "about:blank":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"[{timestamp}] {url}"
            self.history.insert(0, entry)
            
            if len(self.history) > HISTORY_MAX_SIZE:
                self.history = self.history[:HISTORY_MAX_SIZE]
                
            self._history_dirty = True
            
            if not self._history_save_timer:
                self._history_save_timer = QTimer(self)
                self._history_save_timer.setSingleShot(True)
                self._history_save_timer.timeout.connect(self._flush_history)
                
            self._history_save_timer.start(HISTORY_SAVE_DEBOUNCE_MS)

    def _flush_history(self) -> None:
        """Flush debounced history to disk file."""
        if self._history_dirty:
            self._save_history()
            self._history_dirty = False

    def _load_history(self) -> None:
        """Load history from history.json with corruption recovery."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                    if not isinstance(self.history, list):
                        self.history = []
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.error(f"Corrupted history file, backing up and resetting: {e}")
            self._recover_corrupted_file(self.history_file)
            self.history = []

    def _save_history(self) -> None:
        """Save history to history.json."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")

    def _load_bookmarks(self) -> None:
        """Load bookmarks from bookmarks.json with corruption recovery."""
        try:
            if self.bookmarks_file.exists():
                with open(self.bookmarks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.bookmarks.update(data)
                        self._refresh_bookmarks_toolbar()
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.error(f"Corrupted bookmarks file, backing up: {e}")
            self._recover_corrupted_file(self.bookmarks_file)

    def _save_bookmarks(self) -> None:
        """Save bookmarks to bookmarks.json."""
        try:
            with open(self.bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump(self.bookmarks, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving bookmarks: {e}")

    def _add_current_bookmark(self) -> None:
        """Add current active page to bookmarks."""
        current = self.current_tab()
        if not current or not hasattr(current, 'browser'):
            return
            
        url = current.browser.url().toString()
        title = current.browser.title().strip() or "Untitled Bookmark"
        
        self.bookmarks_history.append(self.bookmarks.copy())
        self.bookmarks_future.clear()
        
        self.bookmarks[title] = url
        self._refresh_bookmarks_toolbar()
        self._save_bookmarks()
        self.update_bookmark_button_state()
        self.show_toast(f"⭐ Bookmarked: {title[:25]}")
        self.log_action(f"⭐ Bookmark added: {title}")

    def on_download_requested(self, download: QWebEngineDownloadItem) -> None:
        """Handle download requests and pass to DownloadManager."""
        try:
            default_path = download.path()
            suggested_filename = os.path.basename(default_path)
            downloads_dir = str(Path.home() / "Downloads")
            os.makedirs(downloads_dir, exist_ok=True)
            
            target_path = os.path.join(downloads_dir, suggested_filename)
            
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Download File",
                target_path,
                "All Files (*)"
            )
            
            if not save_path:
                download.cancel()
                self.log_action(f"Download cancelled: {suggested_filename}")
                return
                
            download.setPath(save_path)
            download.accept()
            self.download_manager.add_download(download)
            self.show_downloads()
            self.log_action(f"📥 Download started: {suggested_filename}")
            
        except Exception as e:
            logger.error(f"Download request handling failed: {e}")
            try:
                download.cancel()
            except Exception:
                pass
            QMessageBox.warning(self, "Download Error", f"Unable to start download:\n{e}")

    def save_session(self) -> None:
        """Save open non-private tab URLs and zoom levels to session.json."""
        session_data = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab and hasattr(tab, 'browser') and not getattr(tab, 'is_private', False):
                url = tab.browser.url().toString()
                if url and url != "about:blank":
                    zoom = tab.browser.zoomFactor()
                    session_data.append({
                        "url": url,
                        "zoom": zoom,
                        "pinned": getattr(tab, 'is_pinned', False)
                    })
                    
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving session: {e}")

    def restore_session(self) -> None:
        """Restore previous session tabs and zoom factors with corruption recovery."""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    if isinstance(session_data, list) and session_data:
                        for item in session_data:
                            if isinstance(item, dict):
                                url = item.get("url")
                                zoom = item.get("zoom", DEFAULT_ZOOM)
                                pinned = item.get("pinned", False)
                                if url:
                                    tab = self.add_new_tab(url)
                                    if tab:
                                        tab.browser.setZoomFactor(float(zoom))
                                        if pinned and hasattr(tab, 'set_pinned'):
                                            tab.set_pinned(True)
                            elif isinstance(item, str):
                                self.add_new_tab(item)
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.error(f"Corrupted session file: {e}")
            self._recover_corrupted_file(self.session_file)
            
        if self.tabs.count() == 0:
            self.add_new_tab(self.homepage)

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
