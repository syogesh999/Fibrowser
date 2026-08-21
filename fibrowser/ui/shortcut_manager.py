import logging
from typing import Dict, Callable, Optional, Tuple, Any
from PyQt5.QtWidgets import QWidget, QShortcut
from PyQt5.QtGui import QKeySequence

logger = logging.getLogger(__name__)

class ShortcutManager:
    """Centralized manager for registering, organizing, and managing keyboard shortcuts."""
    
    def __init__(self, parent_widget: QWidget) -> None:
        """Initialize ShortcutManager for a parent widget.
        
        Args:
            parent_widget: Target QWidget (typically MainWindow) to bind shortcuts
        """
        self.parent_widget = parent_widget
        # Mapping: action_name -> (sequence_str, QShortcut, callback, description)
        self.shortcuts: Dict[str, Tuple[str, QShortcut, Callable, str]] = {}
        
    def register(self, name: str, sequence_str: str, callback: Callable, 
                 description: str = "", override: bool = True) -> Optional[QShortcut]:
        """Register a keyboard shortcut with conflict checking.
        
        Args:
            name: Identifier name for the shortcut action
            sequence_str: Key combination string (e.g. "Ctrl+T", "F5")
            callback: Function to invoke when shortcut triggered
            description: Human-readable action description
            override: Whether to override if shortcut name already registered
            
        Returns:
            Created QShortcut object or None if registration skipped
        """
        if name in self.shortcuts and not override:
            logger.warning(f"Shortcut '{name}' is already registered and override is False.")
            return None
            
        # Check for sequence conflict among existing shortcuts
        for existing_name, (existing_seq, _, _, _) in self.shortcuts.items():
            if existing_name != name and existing_seq.lower() == sequence_str.lower():
                logger.debug(f"Shortcut sequence '{sequence_str}' for '{name}' collides with '{existing_name}'")

        shortcut = QShortcut(QKeySequence(sequence_str), self.parent_widget)
        shortcut.activated.connect(callback)
        self.shortcuts[name] = (sequence_str, shortcut, callback, description)
        return shortcut

    def get_shortcut(self, name: str) -> Optional[QShortcut]:
        """Retrieve QShortcut instance by action name."""
        if name in self.shortcuts:
            return self.shortcuts[name][1]
        return None

    def get_sequence(self, name: str) -> Optional[str]:
        """Retrieve the key sequence string for an action."""
        if name in self.shortcuts:
            return self.shortcuts[name][0]
        return None

    def update_sequence(self, name: str, new_sequence_str: str) -> bool:
        """Update the key sequence for an existing registered shortcut.
        
        Args:
            name: Identifier name of the shortcut
            new_sequence_str: New key sequence string
            
        Returns:
            True if updated successfully, False otherwise
        """
        if name not in self.shortcuts:
            return False
        _, old_shortcut, callback, desc = self.shortcuts[name]
        old_shortcut.setKey(QKeySequence(new_sequence_str))
        self.shortcuts[name] = (new_sequence_str, old_shortcut, callback, desc)
        return True

    def clear(self) -> None:
        """Clear and disconnect all registered shortcuts."""
        for _, shortcut, _, _ in self.shortcuts.values():
            try:
                shortcut.setEnabled(False)
                shortcut.deleteLater()
            except Exception:
                pass
        self.shortcuts.clear()
