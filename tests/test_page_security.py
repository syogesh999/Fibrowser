import unittest
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QUrl
from fibrowser.core.page import BrowserPage

class MockWindow:
    def __init__(self, ssl_return_value=False):
        self.ssl_return_value = ssl_return_value
        self.ssl_handled_calls = 0

    def handle_ssl_error(self, cert_error):
        self.ssl_handled_calls += 1
        return self.ssl_return_value

class MockCertError:
    def __init__(self, host="example.com", error_desc="Certificate expired"):
        self._url = QUrl(f"https://{host}")
        self._desc = error_desc
        self.ignored = False

    def url(self):
        return self._url

    def errorDescription(self):
        return self._desc

    def ignoreCertificateError(self):
        self.ignored = True

class TestPageSecurity(unittest.TestCase):
    """Test suite for SSL certificate error handling and page security (HIGH-004)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_certificate_error_rejected_by_default(self):
        page = BrowserPage(window=None)
        mock_err = MockCertError()
        result = page.certificateError(mock_err)
        self.assertFalse(result)
        self.assertFalse(mock_err.ignored)

    def test_certificate_error_rejected_by_window(self):
        mock_win = MockWindow(ssl_return_value=False)
        page = BrowserPage(window=mock_win)
        mock_err = MockCertError()
        result = page.certificateError(mock_err)
        self.assertFalse(result)
        self.assertFalse(mock_err.ignored)
        self.assertEqual(mock_win.ssl_handled_calls, 1)

    def test_certificate_error_accepted_by_window(self):
        mock_win = MockWindow(ssl_return_value=True)
        page = BrowserPage(window=mock_win)
        mock_err = MockCertError()
        result = page.certificateError(mock_err)
        self.assertTrue(result)
        self.assertTrue(mock_err.ignored)
        self.assertEqual(mock_win.ssl_handled_calls, 1)

if __name__ == '__main__':
    unittest.main()
