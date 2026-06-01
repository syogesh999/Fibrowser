#!/usr/bin/env python3
"""
Fibrowser Pro package entry point.
Launches the main window and handles global exceptions.
"""

import sys
import logging
import traceback
# pyrefly: ignore [missing-import]
from PyQt5.QtWidgets import QApplication, QMessageBox, QStyle

from fibrowser.config import APP_NAME, APP_VERSION, get_icon
from fibrowser.ui.window import Window

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def handle_unhandled_exception(exc_type, exc_value, exc_tb):
    """Global exception handler to prevent silent crashes
    
    Args:
        exc_type: Exception type
        exc_value: Exception value
        exc_tb: Exception traceback
    """
    tb_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.error(f"Unhandled exception:\n{tb_text}")
    try:
        print(tb_text)
    except Exception:
        pass
    try:
        QMessageBox.critical(None, "🔥 Unhandled Exception", 
            f"An unexpected error occurred:\n\n{tb_text}")
    except Exception:
        pass

def main():
    """Application main entry point"""
    # Set up exception handler
    sys.excepthook = handle_unhandled_exception
    
    # Create and run application
    try:
        app = QApplication(sys.argv)
        
        # Configure application
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setApplicationDisplayName(f"{APP_NAME} v{APP_VERSION}")
        
        # Set icon
        try:
            app.setWindowIcon(get_icon("favicon.png", QStyle.SP_ComputerIcon))
        except Exception:
            pass
        
        # Create and show main window
        window = Window()
        window.show()
        
        logger.info(f"{APP_NAME} v{APP_VERSION} started successfully")
        return app.exec_()
        
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        print(f"Failed to start application: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
