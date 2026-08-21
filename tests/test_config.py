import unittest
import os
from PyQt5.QtCore import QUrl
from fibrowser.config import (
    THEMES, SEARCH_ENGINES, DEFAULT_HOME_PAGE, MAX_TABS,
    HISTORY_MAX_SIZE, is_safe_local_path, format_error_message
)

class TestConfigAndUtils(unittest.TestCase):
    """Test suite for config constants, path security, and error formatting."""

    def test_default_constants(self):
        self.assertEqual(DEFAULT_HOME_PAGE, "https://www.bing.com")
        self.assertGreater(MAX_TABS, 0)
        self.assertEqual(HISTORY_MAX_SIZE, 500)
        self.assertIn("Google", SEARCH_ENGINES)
        self.assertIn("Bing", SEARCH_ENGINES)

    def test_themes_definition(self):
        self.assertIn("Dark", THEMES)
        self.assertIn("Light", THEMES)
        self.assertIn("Nord", THEMES)
        self.assertIn("Dracula", THEMES)
        self.assertIn("Blue", THEMES)
        
        dark_theme = THEMES["Dark"]
        self.assertEqual(dark_theme.name, "Dark")
        self.assertTrue(dark_theme.bg.startswith("#"))
        self.assertTrue(dark_theme.accent.startswith("#"))

    def test_is_safe_local_path(self):
        # Safe paths
        self.assertTrue(is_safe_local_path("C:\\Users\\User\\Documents\\page.html"))
        self.assertTrue(is_safe_local_path("C:/Users/User/Downloads/index.html"))
        self.assertTrue(is_safe_local_path("D:\\projects\\test.html"))
        
        # Unsafe sensitive system paths (CRIT-003)
        self.assertFalse(is_safe_local_path("C:\\Windows\\System32\\config\\SAM"))
        self.assertFalse(is_safe_local_path("C:/Windows/System32/config/SYSTEM"))
        self.assertFalse(is_safe_local_path("C:\\Windows\\System32\\drivers\\etc\\hosts"))
        self.assertFalse(is_safe_local_path("/etc/shadow"))
        self.assertFalse(is_safe_local_path("/etc/passwd"))
        self.assertFalse(is_safe_local_path("C:\\Users\\User\\.ssh\\id_rsa"))
        self.assertFalse(is_safe_local_path("C:\\Users\\User\\app\\.env"))

    def test_format_error_message(self):
        # Exception formatting
        err = ValueError("Invalid parameter value")
        msg = format_error_message(err)
        self.assertIn("ValueError", msg)
        self.assertIn("Invalid parameter value", msg)
        
        # QUrl formatting
        url = QUrl("https://example.com/test")
        url_msg = format_error_message(url)
        self.assertIn("https://example.com/test", url_msg)
        
        # String fallback
        self.assertEqual(format_error_message("Simple error"), "Simple error")

if __name__ == '__main__':
    unittest.main()
