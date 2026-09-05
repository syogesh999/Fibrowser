"""
Fibrowser Pro Package
A feature-rich desktop web browser built with PyQt5 and PyQtWebEngine.
"""

__version__ = "2.1.0"
__author__ = "Development Team"
__all__ = ["Window", "Tab", "config"]

from fibrowser import config
from fibrowser.ui.window import Window
from fibrowser.ui.tab import Tab
