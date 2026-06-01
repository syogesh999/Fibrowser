from PyQt5.QtCore import Qt, QSize, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QPushButton, QWidget, QHBoxLayout, QLabel
from fibrowser.config import THEMES

class AnimatedButton(QPushButton):
    """Button with smooth hover animation and modern styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(36, 36)  # Prevent toolbar layout shift on hover
        
        # Animation for icon size
        self._size_animation = QPropertyAnimation(self, b"iconSize")
        self._size_animation.setDuration(200)
        self._size_animation.setEasingCurve(QEasingCurve.OutBack)
        self.setIconSize(QSize(24, 24))
        
    def enterEvent(self, event):
        """Handle mouse enter event"""
        self._size_animation.setStartValue(self.iconSize())
        self._size_animation.setEndValue(QSize(28, 28))
        self._size_animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Handle mouse leave event"""
        self._size_animation.setStartValue(self.iconSize())
        self._size_animation.setEndValue(QSize(24, 24))
        self._size_animation.start()
        super().leaveEvent(event)

class ToastNotification(QWidget):
    """Sleek overlay toast notification that fades in and out at the bottom-right"""
    
    def __init__(self, text: str, parent: QWidget, duration_ms: int = 3000):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        self.label = QLabel(text)
        self.label.setStyleSheet("color: white; font-weight: 500; font-size: 12px; background: transparent;")
        layout.addWidget(self.label)
        
        # Determine theme accent color
        accent = "#3b82f6"
        if hasattr(parent, 'current_theme') and parent.current_theme in THEMES:
            accent = THEMES[parent.current_theme].accent
            
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(30, 30, 30, 0.85);
                border: 1px solid {accent};
                border-radius: 8px;
            }}
        """)
        
        self.adjustSize()
        self.reposition()
        
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(300)
        
        self.show_toast(duration_ms)
        
    def reposition(self):
        parent = self.parentWidget()
        if parent:
            p_geom = parent.geometry()
            # Position at bottom-right corner of parent window
            x = p_geom.width() - self.width() - 20
            y = p_geom.height() - self.height() - 50
            # Map parent local position to global coordinates
            global_pos = parent.mapToGlobal(QPoint(x, y))
            self.move(global_pos)
            
    def show_toast(self, duration_ms: int):
        self.setWindowOpacity(0.0)
        self.show()
        
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
        
        QTimer.singleShot(duration_ms, self.fade_out)
        
    def fade_out(self):
        try:
            self.anim.stop()
            self.anim.setStartValue(self.windowOpacity())
            self.anim.setEndValue(0.0)
            self.anim.finished.connect(self.close)
            self.anim.start()
        except Exception:
            self.close()
