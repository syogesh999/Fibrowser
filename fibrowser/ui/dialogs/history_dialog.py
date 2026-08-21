import logging
from typing import Any, Optional, List
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QListWidget, QListWidgetItem, QPushButton, 
                             QMessageBox, QMenu, QAction, QWidget, QShortcut)
from PyQt5.QtGui import QKeySequence

logger = logging.getLogger(__name__)

class HistoryDialog(QDialog):
    """Browsing history viewer and manager with fast filtering and search capabilities."""
    
    def __init__(self, window: Any, parent: Optional[QWidget] = None) -> None:
        """Initialize history dialog.
        
        Args:
            window: Parent MainWindow reference containing history data
            parent: Parent widget
        """
        super().__init__(parent or window)
        self.window = window
        self.setWindowTitle("📜 Browsing History")
        self.setMinimumSize(520, 420)
        
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize history dialog UI components."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search history...")
        self.search_input.setClearButtonEnabled(True)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.setAlternatingRowColors(True)
        layout.addWidget(self.history_list)
        
        # Initial population
        self._populate_history()
        self.search_input.textChanged.connect(self._populate_history)
        
        # Double click to navigate
        self.history_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # Context menu for deleting item
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self._show_context_menu)
        
        # Delete key shortcut
        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self)
        self.delete_shortcut.activated.connect(self._delete_selected_item)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        self.clear_btn = QPushButton("🗑️ Clear History")
        self.clear_btn.clicked.connect(self._clear_history_action)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def _populate_history(self, filter_text: str = "") -> None:
        """Populate history list with optional fast case-insensitive filter.
        
        Args:
            filter_text: Search query string to filter URLs
        """
        self.history_list.clear()
        history_items: List[str] = getattr(self.window, 'history', [])
        
        filter_lower = filter_text.strip().lower()
        if filter_lower:
            filtered = [u for u in history_items if filter_lower in u.lower()]
        else:
            filtered = history_items
            
        # Display most recent entries first, capped at 150 for responsive rendering
        for i, url in enumerate(reversed(filtered[-150:]), 1):
            item = QListWidgetItem(f"{i}. {url}")
            item.setData(Qt.UserRole, url)
            self.history_list.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Navigate to selected URL and close dialog."""
        url = item.data(Qt.UserRole)
        if url and hasattr(self.window, 'navigate_to'):
            self.window.navigate_to(url)
            self.accept()

    def _show_context_menu(self, pos: QPoint) -> None:
        """Show context menu for selected history item."""
        item = self.history_list.itemAt(pos)
        if not item:
            return
            
        menu = QMenu(self)
        delete_action = QAction("🗑️ Remove from History", self)
        url = item.data(Qt.UserRole)
        delete_action.triggered.connect(lambda: self._delete_url(url))
        menu.addAction(delete_action)
        menu.exec_(self.history_list.mapToGlobal(pos))

    def _delete_selected_item(self) -> None:
        """Delete currently selected history item."""
        item = self.history_list.currentItem()
        if item:
            url = item.data(Qt.UserRole)
            self._delete_url(url)

    def _delete_url(self, url: str) -> None:
        """Delete specific URL from history and update storage.
        
        Args:
            url: URL string to remove
        """
        if hasattr(self.window, 'history'):
            self.window.history = [h for h in self.window.history if h != url]
            if hasattr(self.window, '_save_history'):
                self.window._save_history()
            self._populate_history(self.search_input.text())
            if hasattr(self.window, 'log_action'):
                self.window.log_action(f"🗑️ Removed from history: {url[:50]}...")

    def _clear_history_action(self) -> None:
        """Prompt confirmation and clear entire browsing history."""
        if QMessageBox.question(
            self, 
            "Clear History", 
            "Are you sure you want to clear all browsing history?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            if hasattr(self.window, 'history'):
                self.window.history.clear()
            if hasattr(self.window, '_save_history'):
                self.window._save_history()
            self.history_list.clear()
            if hasattr(self.window, 'log_action'):
                self.window.log_action("🗑️ Browsing history cleared")
            if hasattr(self.window, 'show_toast'):
                self.window.show_toast("Browsing history cleared")
