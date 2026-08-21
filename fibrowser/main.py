#!/usr/bin/env python3
"""
Fibrowser Pro package entry point.
Launches the main application window, configures logging levels, and catches unhandled exceptions.
"""

import os
import sys
import logging
import traceback
from typing import Any
from PyQt5.QtWidgets import QApplication, QMessageBox, QStyle

from fibrowser.config import APP_NAME, APP_VERSION, get_icon
from fibrowser.ui.window import Window

# Configure logging dynamically from environment
log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def handle_unhandled_exception(exc_type: Any, exc_value: Any, exc_tb: Any) -> None:
    """Global exception handler to prevent silent crashes and record stack traces.
    
    Args:
        exc_type: Exception type
        exc_value: Exception value
        exc_tb: Exception traceback object
    """
    tb_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.error(f"Unhandled exception:\n{tb_text}")
    try:
        print(tb_text, file=sys.stderr)
    except Exception:
        pass
    try:
        QMessageBox.critical(
            None, 
            "🔥 Unhandled Exception", 
            f"An unexpected error occurred:\n\n{tb_text}"
        )
    except Exception:
        pass

def main() -> int:
    """Application main entry point function.
    
    Returns:
        Exit code integer
    """
    # Set up global exception handler
    sys.excepthook = handle_unhandled_exception
    
    try:
        app = QApplication(sys.argv)
        
        # Configure application metadata
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setApplicationDisplayName(f"{APP_NAME} v{APP_VERSION}")
        
        # Set application default window icon
        try:
            app.setWindowIcon(get_icon("favicon.png", QStyle.SP_ComputerIcon))
        except Exception:
            pass
        
        # Create and show main browser window
        window = Window()
        window.show()
        
        logger.info(f"{APP_NAME} v{APP_VERSION} started successfully")
        return app.exec_()
        
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        print(f"Failed to start application: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
