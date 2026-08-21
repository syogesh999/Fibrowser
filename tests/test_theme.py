import unittest
from fibrowser.ui.theme_manager import ThemeManager
from fibrowser.config import THEMES

class TestThemeManager(unittest.TestCase):
    """Test suite for ThemeManager operations and stylesheet generation."""

    def test_validate_theme_name(self):
        # Valid themes
        self.assertEqual(ThemeManager.validate_theme_name("Dark"), "Dark")
        self.assertEqual(ThemeManager.validate_theme_name("Light"), "Light")
        self.assertEqual(ThemeManager.validate_theme_name("Nord"), "Nord")
        
        # Invalid theme fallback (HIGH-005)
        self.assertEqual(ThemeManager.validate_theme_name("NonExistentTheme"), "Dark")
        self.assertEqual(ThemeManager.validate_theme_name(""), "Dark")

    def test_get_accent_color(self):
        self.assertEqual(ThemeManager.get_accent_color("Dark"), THEMES["Dark"].accent)
        self.assertEqual(ThemeManager.get_accent_color("Light"), THEMES["Light"].accent)
        # Invalid returns Dark's accent
        self.assertEqual(ThemeManager.get_accent_color("Invalid"), THEMES["Dark"].accent)

    def test_generate_stylesheet(self):
        css = ThemeManager.generate_stylesheet("Dark")
        self.assertIsInstance(css, str)
        self.assertIn("QMainWindow", css)
        self.assertIn("QTabBar::tab", css)
        self.assertIn("QLineEdit", css)
        self.assertIn(THEMES["Dark"].bg, css)
        self.assertIn(THEMES["Dark"].accent, css)

if __name__ == '__main__':
    unittest.main()
