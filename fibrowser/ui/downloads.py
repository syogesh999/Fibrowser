import os
import logging
from typing import List
from PyQt5.QtCore import Qt, QUrl, QDateTime
from PyQt5.QtGui import QIcon, QFont, QDesktopServices
from PyQt5.QtWebEngineWidgets import QWebEngineDownloadItem
from PyQt5.QtWidgets import (QWidget, QDialog, QHBoxLayout, QVBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QListWidget, QListWidgetItem,
                             QStyle, QApplication, QMessageBox)

logger = logging.getLogger(__name__)

class DownloadItemWidget(QWidget):
    """Custom widget for displaying download progress with action buttons and real-time speed"""
    
    def __init__(self, download_item: QWebEngineDownloadItem, parent=None):
        """Initialize download widget
        
        Args:
            download_item: QWebEngineDownloadItem object
            parent: Parent widget
        """
        super().__init__(parent)
        self.download = download_item
        self.start_time: QDateTime = QDateTime.currentDateTime()
        self.window = parent.parent() if hasattr(parent, 'parent') else None
        
        # Real-time speed track variables
        self.last_bytes = 0
        self.last_time = QDateTime.currentDateTime()
        
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        self.setLayout(layout)
        
        # File icon
        self.icon = QLabel()
        icon_pixmap = QApplication.style().standardIcon(
            QStyle.SP_FileIcon
        ).pixmap(24, 24)
        self.icon.setPixmap(icon_pixmap)
        layout.addWidget(self.icon)
        
        # Filename
        self.filename = QLabel(os.path.basename(download_item.path()))
        self.filename.setMinimumWidth(150)
        layout.addWidget(self.filename, 1)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setMinimumWidth(150)
        layout.addWidget(self.progress, 2)
        
        # Speed label
        self.speed_label = QLabel("0 KB/s")
        self.speed_label.setMinimumWidth(80)
        layout.addWidget(self.speed_label)
        
        # Status label
        self.status_label = QLabel("Downloading...")
        self.status_label.setMinimumWidth(80)
        layout.addWidget(self.status_label)
        
        # Folder button (Show in Folder) - hidden until complete
        self.folder_btn = QPushButton("📁")
        self.folder_btn.setToolTip("Show in Folder")
        self.folder_btn.setFlat(True)
        self.folder_btn.setMaximumWidth(28)
        self.folder_btn.setCursor(Qt.PointingHandCursor)
        self.folder_btn.setVisible(False)
        self.folder_btn.clicked.connect(self.show_in_folder)
        layout.addWidget(self.folder_btn)
        
        # Open button (Open File) - hidden until complete
        self.open_btn = QPushButton("👁️")
        self.open_btn.setToolTip("Open File")
        self.open_btn.setFlat(True)
        self.open_btn.setMaximumWidth(28)
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.setVisible(False)
        self.open_btn.clicked.connect(self.open_file)
        layout.addWidget(self.open_btn)
        
        # Cancel button
        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setToolTip("Cancel Download")
        self.cancel_btn.setFlat(True)
        self.cancel_btn.setMaximumWidth(28)
        self.cancel_btn.setStyleSheet("font-weight: bold; color: #d9534f;")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_download)
        layout.addWidget(self.cancel_btn)
        
        # Connect signals
        self.download.downloadProgress.connect(self.update_progress)
        self.download.stateChanged.connect(self.update_state)
        
    def show_in_folder(self) -> None:
        """Open the folder containing the downloaded file"""
        path = self.download.path()
        if os.path.exists(path):
            folder = os.path.dirname(path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            QMessageBox.warning(self, "File Not Found", "The downloaded file could not be found.")

    def open_file(self) -> None:
        """Open the downloaded file directly"""
        path = self.download.path()
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "File Not Found", "The downloaded file could not be found.")
        
    def update_progress(self, bytes_received: int, bytes_total: int) -> None:
        """Update download progress
        
        Args:
            bytes_received: Bytes downloaded
            bytes_total: Total bytes to download
        """
        if bytes_total > 0:
            percent = int((bytes_received / bytes_total) * 100)
            self.progress.setValue(percent)
            
            # Calculate instantaneous speed (every 500ms minimum)
            try:
                now = QDateTime.currentDateTime()
                elapsed_ms = self.last_time.msecsTo(now)
                
                # Check if at least 500ms has elapsed since last tick, or it's the start
                if elapsed_ms >= 500 or self.last_bytes == 0:
                    bytes_diff = bytes_received - self.last_bytes
                    
                    if elapsed_ms > 0:
                        speed = bytes_diff / elapsed_ms  # KB/s
                    else:
                        speed = 0.0
                        
                    self.last_bytes = bytes_received
                    self.last_time = now
                    
                    # Update speed label
                    if speed >= 1024:
                        self.speed_label.setText(f"{speed/1024:.1f} MB/s")
                    else:
                        self.speed_label.setText(f"{speed:.1f} KB/s")
                        
                    # Calculate ETA
                    if speed > 0:
                        remaining_bytes = bytes_total - bytes_received
                        remaining_seconds = remaining_bytes / (speed * 1024)
                        if remaining_seconds > 60:
                            eta = f"{int(remaining_seconds/60)}m {int(remaining_seconds%60)}s"
                        else:
                            eta = f"{int(remaining_seconds)}s"
                        self.status_label.setText(f"ETA: {eta}")
                    else:
                        self.status_label.setText("Calculating...")
            except Exception as e:
                logger.debug(f"Speed calculation error: {e}")
                self.speed_label.setText("--")
                
    def update_state(self, state: QWebEngineDownloadItem.DownloadState) -> None:
        """Update download state
        
        Args:
            state: Download state enum
        """
        if state == QWebEngineDownloadItem.DownloadCompleted:
            self.progress.setValue(100)
            self.speed_label.setText("Completed")
            self.status_label.setText("✓ Done")
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setVisible(False)
            self.folder_btn.setVisible(True)
            self.open_btn.setVisible(True)
            # Show toast notification in parent main window if possible
            main_win = self.window
            if not main_win and hasattr(self.parent(), 'parent') and self.parent().parent():
                main_win = self.parent().parent()
            if main_win and hasattr(main_win, 'show_toast'):
                main_win.show_toast(f"📥 Download Completed:\n{os.path.basename(self.download.path())}")
        elif state == QWebEngineDownloadItem.DownloadCancelled:
            self.status_label.setText("✗ Cancelled")
            self.speed_label.setText("Cancelled")
            self.cancel_btn.setEnabled(False)
            self.folder_btn.setVisible(False)
            self.open_btn.setVisible(False)
        elif state == QWebEngineDownloadItem.DownloadInterrupted:
            self.status_label.setText("✗ Interrupted")
            self.cancel_btn.setEnabled(False)
            self.folder_btn.setVisible(False)
            self.open_btn.setVisible(False)

    def cancel_download(self) -> None:
        """Cancel the active download"""
        if self.download.state() == QWebEngineDownloadItem.DownloadInProgress:
            self.download.cancel()
            self.cancel_btn.setEnabled(False)
            self.speed_label.setText("Cancelled")
            self.status_label.setText("✗ Cancelled")

class DownloadManager(QDialog):
    """Enhanced download manager window with better UI and features"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 Downloads")
        self.setMinimumSize(750, 450)
        self.setWindowIcon(QApplication.style().standardIcon(
            QStyle.SP_DialogSaveButton
        ))
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.setLayout(layout)
        
        # Header with stats
        header_layout = QHBoxLayout()
        header = QLabel("<b>📥 Downloads</b>")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(header)
        
        self.stats_label = QLabel("0 active • 0 completed")
        header_layout.addStretch()
        header_layout.addWidget(self.stats_label)
        layout.addLayout(header_layout)
        
        # Download list
        self.download_list = QListWidget()
        self.download_list.setAlternatingRowColors(True)
        self.download_list.setSpacing(2)
        layout.addWidget(self.download_list)
        
        # Button layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.clear_btn = QPushButton("🗑️ Clear Completed")
        self.clear_btn.clicked.connect(self.clear_completed)
        btn_layout.addWidget(self.clear_btn)
        
        self.pause_all_btn = QPushButton("⏸️ Pause All")
        self.pause_all_btn.setVisible(False)
        btn_layout.addWidget(self.pause_all_btn)
        
        btn_layout.addStretch()
        
        self.close_btn = QPushButton("✕ Close")
        self.close_btn.clicked.connect(self.hide)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        self.downloads: List[DownloadItemWidget] = []
        
    def add_download(self, download_item: QWebEngineDownloadItem) -> None:
        """Add a new download to the manager
        
        Args:
            download_item: QWebEngineDownloadItem object
        """
        item = QListWidgetItem(self.download_list)
        widget = DownloadItemWidget(download_item, self)
        item.setSizeHint(widget.sizeHint())
        self.download_list.addItem(item)
        self.download_list.setItemWidget(item, widget)
        self.downloads.append(widget)
        self.update_stats()
        
    def clear_completed(self) -> None:
        """Remove completed downloads from the list and clean up memory"""
        for i in range(self.download_list.count() - 1, -1, -1):
            item = self.download_list.item(i)
            widget = self.download_list.itemWidget(item)
            if widget and widget.download.state() == QWebEngineDownloadItem.DownloadCompleted:
                # Disconnect signals to prevent leaks
                try:
                    widget.download.downloadProgress.disconnect(widget.update_progress)
                    widget.download.stateChanged.disconnect(widget.update_state)
                except Exception:
                    pass
                self.download_list.takeItem(i)
                if widget in self.downloads:
                    self.downloads.remove(widget)
                widget.deleteLater()
        self.update_stats()
        
    def update_stats(self) -> None:
        """Update download statistics display"""
        active = sum(1 for w in self.downloads if w.download.state() == QWebEngineDownloadItem.DownloadInProgress)
        completed = sum(1 for w in self.downloads if w.download.state() == QWebEngineDownloadItem.DownloadCompleted)
        self.stats_label.setText(f"{active} active • {completed} completed")
