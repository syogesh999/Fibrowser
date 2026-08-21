import logging
from typing import Optional, Any
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineProfile

logger = logging.getLogger(__name__)

class BrowserPage(QWebEnginePage):
    """Custom QWebEnginePage with improved error handling, fullscreen control, and certificate management."""
    
    def __init__(self, profile: Optional[QWebEngineProfile] = None, window: Optional[Any] = None) -> None:
        """Initialize custom browser page.
        
        Args:
            profile: QWebEngineProfile instance (optional)
            window: Parent window for error and fullscreen delegation
        """
        if isinstance(profile, QWebEngineProfile):
            super().__init__(profile)
        else:
            super().__init__()
        self.window = window
        self.fullScreenRequested.connect(self.handle_fullscreen_request)

    def certificateError(self, certificateError: Any) -> bool:
        """Handle SSL/TLS certificate errors with detailed logging and user prompt delegation.
        
        Args:
            certificateError: Certificate error object from QtWebEngine
            
        Returns:
            True if error should be ignored and navigation proceeds, False otherwise
        """
        try:
            error_host = certificateError.url().host() if hasattr(certificateError, 'url') else "Unknown host"
            error_desc = certificateError.errorDescription() if hasattr(certificateError, 'errorDescription') else "Unknown SSL error"
            logger.warning(f"SSL certificate error encountered on {error_host}: {error_desc}")
            
            accepted = False
            if self.window and hasattr(self.window, 'handle_ssl_error'):
                res = self.window.handle_ssl_error(certificateError)
                accepted = bool(res)
                
            if accepted:
                certificateError.ignoreCertificateError()
                logger.info(f"SSL certificate error ignored by user for host: {error_host}")
                return True
        except Exception as e:
            logger.error(f"Certificate error handler failed: {str(e)}")
        return False

    def handle_fullscreen_request(self, request: Any) -> None:
        """Handle HTML5 fullscreen requests from webpages.
        
        Args:
            request: QWebEngineFullScreenRequest object
        """
        try:
            if self.window and hasattr(self.window, 'handle_html5_fullscreen'):
                self.window.handle_html5_fullscreen(request)
            else:
                request.reject()
        except Exception as e:
            logger.error(f"Fullscreen request handling failed: {str(e)}")
            try:
                request.reject()
            except Exception:
                pass
