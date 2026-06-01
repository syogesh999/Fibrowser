import logging
from typing import Optional
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineProfile

logger = logging.getLogger(__name__)

class BrowserPage(QWebEnginePage):
    """Custom QWebEnginePage with improved error handling and certificate management"""
    
    def __init__(self, profile: Optional[QWebEngineProfile] = None, window = None):
        """Initialize custom browser page
        
        Args:
            profile: QWebEngineProfile instance (optional)
            window: Parent window for error handling
        """
        if isinstance(profile, QWebEngineProfile):
            super().__init__(profile)
        else:
            super().__init__()
        self.window = window
        self.fullScreenRequested.connect(self.handle_fullscreen_request)

    def certificateError(self, certificateError) -> bool:
        """Handle SSL/TLS certificate errors
        
        Args:
            certificateError: Certificate error object
            
        Returns:
            True if error should be ignored, False otherwise
        """
        try:
            accepted = False
            if self.window and hasattr(self.window, 'handle_ssl_error'):
                accepted = self.window.handle_ssl_error(certificateError)
            if accepted:
                certificateError.ignoreCertificateError()
                return True
        except Exception as e:
            logger.error(f"Certificate error handler failed: {str(e)}")
        return False

    def handle_fullscreen_request(self, request) -> None:
        """Handle HTML5 fullscreen requests from webpages"""
        try:
            if self.window and hasattr(self.window, 'handle_html5_fullscreen'):
                self.window.handle_html5_fullscreen(request)
            else:
                request.reject()
        except Exception as e:
            logger.error(f"Fullscreen request handling failed: {str(e)}")
            request.reject()
