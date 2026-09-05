import unittest
import re
from typing import Tuple
from fibrowser.config import THEMES, Theme
from fibrowser.ui.theme_manager import ThemeManager

def parse_hex_color(hex_str: str) -> Tuple[int, int, int]:
    """Parse #RRGGBB or #RGB string into (r, g, b) integers in range 0-255."""
    hex_str = hex_str.strip().lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    if len(hex_str) != 6:
        raise ValueError(f"Invalid hex color: {hex_str}")
    return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))

def relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance using standard sRGB formula (WCAG 2.1)."""
    def channel_linear(c: int) -> float:
        val = c / 255.0
        return val / 12.92 if val <= 0.03928 else ((val + 0.055) / 1.055) ** 2.4

    r_lin = channel_linear(r)
    g_lin = channel_linear(g)
    b_lin = channel_linear(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin

def contrast_ratio(hex_color1: str, hex_color2: str) -> float:
    """Calculate WCAG contrast ratio between two hex color codes."""
    r1, g1, b1 = parse_hex_color(hex_color1)
    r2, g2, b2 = parse_hex_color(hex_color2)
    l1 = relative_luminance(r1, g1, b1)
    l2 = relative_luminance(r2, g2, b2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class TestThemeVisibilityAndContrast(unittest.TestCase):
    """Test suite ensuring high visibility, contrast, and comprehensive theme rules."""

    def test_all_defined_themes_exist(self):
        """Verify all expected themes are defined in THEMES."""
        expected = ["Light", "Dark", "Blue", "Nord", "Dracula"]
        for name in expected:
            self.assertIn(name, THEMES, f"Expected theme '{name}' not found in THEMES")
            theme = THEMES[name]
            self.assertEqual(theme.name, name)
            self.assertTrue(theme.bg.startswith("#"))
            self.assertTrue(theme.fg.startswith("#"))
            self.assertTrue(theme.accent.startswith("#"))

    def test_stylesheet_generation_all_themes(self):
        """Verify stylesheets can be generated for all themes without error."""
        for name in THEMES:
            stylesheet = ThemeManager.generate_stylesheet(name)
            self.assertIsInstance(stylesheet, str)
            self.assertGreater(len(stylesheet), 500)
            self.assertIn(THEMES[name].bg, stylesheet)
            self.assertIn(THEMES[name].fg, stylesheet)
            self.assertIn(THEMES[name].accent, stylesheet)

    def test_labels_have_explicit_theme_color(self):
        """Verify QLabel, QFormLayout QLabel, and welcomeSubtitle have explicit color rules."""
        for name in THEMES:
            stylesheet = ThemeManager.generate_stylesheet(name)
            theme = THEMES[name]
            # Global QWidget color
            self.assertIn(f"color: {theme.fg};", stylesheet)
            # QLabel specific rule
            self.assertIn("QLabel {", stylesheet)
            # Form layout label rule
            self.assertIn("QFormLayout QLabel {", stylesheet)
            # Welcome subtitle accent rule
            self.assertIn("QLabel#welcomeSubtitle {", stylesheet)
            self.assertIn(f"color: {theme.accent};", stylesheet)

    def test_checkboxes_and_radio_buttons_styled(self):
        """Verify QCheckBox and QRadioButton have indicator and text color rules."""
        for name in THEMES:
            stylesheet = ThemeManager.generate_stylesheet(name)
            self.assertIn("QCheckBox, QRadioButton {", stylesheet)
            self.assertIn("QCheckBox::indicator", stylesheet)
            self.assertIn("QRadioButton::indicator", stylesheet)

    def test_groupbox_and_statusbar_labels_styled(self):
        """Verify QGroupBox and QStatusBar QLabel have high-contrast text rules."""
        for name in THEMES:
            stylesheet = ThemeManager.generate_stylesheet(name)
            self.assertIn("QGroupBox {", stylesheet)
            self.assertIn("QStatusBar QLabel {", stylesheet)

    def test_list_widget_alternate_rows_styled(self):
        """Verify QListWidget alternate rows have explicit alternate-background-color."""
        for name in THEMES:
            stylesheet = ThemeManager.generate_stylesheet(name)
            theme = THEMES[name]
            self.assertIn(f"alternate-background-color: {theme.tab_bg};", stylesheet)
            self.assertIn("QListWidget::item:alternate {", stylesheet)
            self.assertIn(f"background-color: {theme.tab_bg};", stylesheet)

    def test_find_bar_container_styled(self):
        """Verify QWidget#find_bar has container background and label rules."""
        for name in THEMES:
            stylesheet = ThemeManager.generate_stylesheet(name)
            theme = THEMES[name]
            self.assertIn("QWidget#find_bar {", stylesheet)
            self.assertIn(f"background-color: {theme.tab_bg};", stylesheet)
            self.assertIn("QWidget#find_bar QLabel {", stylesheet)
            self.assertIn("QWidget#find_bar QLineEdit {", stylesheet)

    def test_message_box_text_styled(self):
        """Verify QMessageBox and QMessageBox QLabel are styled to prevent unreadable text."""
        for name in THEMES:
            stylesheet = ThemeManager.generate_stylesheet(name)
            self.assertIn("QMessageBox {", stylesheet)
            self.assertIn("QMessageBox QLabel {", stylesheet)

    def test_wcag_contrast_text_against_background(self):
        """Verify text foreground has at least 4.5:1 contrast against main background."""
        for name, theme in THEMES.items():
            ratio = contrast_ratio(theme.bg, theme.fg)
            self.assertGreaterEqual(
                ratio, 4.5,
                f"Theme '{name}' fails WCAG AA text contrast: bg={theme.bg}, fg={theme.fg}, ratio={ratio:.2f}:1"
            )

    def test_wcag_contrast_text_against_tab_background(self):
        """Verify text foreground has at least 4.5:1 contrast against tab/panel background."""
        for name, theme in THEMES.items():
            ratio = contrast_ratio(theme.tab_bg, theme.fg)
            self.assertGreaterEqual(
                ratio, 4.5,
                f"Theme '{name}' fails tab background contrast: tab_bg={theme.tab_bg}, fg={theme.fg}, ratio={ratio:.2f}:1"
            )

    def test_wcag_contrast_alternate_rows(self):
        """Verify text foreground has high contrast against alternating row background."""
        for name, theme in THEMES.items():
            # Alternating row uses theme.tab_bg
            ratio = contrast_ratio(theme.tab_bg, theme.fg)
            self.assertGreaterEqual(
                ratio, 4.5,
                f"Theme '{name}' alternate row contrast too low: tab_bg={theme.tab_bg}, fg={theme.fg}, ratio={ratio:.2f}:1"
            )

    def test_accent_contrast_against_background(self):
        """Verify accent color is distinct with at least 3.0:1 contrast against background."""
        for name, theme in THEMES.items():
            ratio = contrast_ratio(theme.bg, theme.accent)
            self.assertGreaterEqual(
                ratio, 3.0,
                f"Theme '{name}' accent contrast too low against background: bg={theme.bg}, accent={theme.accent}, ratio={ratio:.2f}:1"
            )

    def test_theme_manager_fallback(self):
        """Verify ThemeManager gracefully falls back to 'Dark' for unknown or malformed theme names."""
        self.assertEqual(ThemeManager.validate_theme_name("Invalid"), "Dark")
        self.assertEqual(ThemeManager.validate_theme_name(""), "Dark")
        self.assertEqual(ThemeManager.validate_theme_name("NonExistentTheme"), "Dark")
        self.assertEqual(ThemeManager.validate_theme_name("Light"), "Light")
        self.assertEqual(ThemeManager.validate_theme_name("Nord"), "Nord")

    def test_theme_manager_accent_lookup(self):
        """Verify ThemeManager.get_accent_color returns valid hex for all valid and invalid inputs."""
        for name in THEMES:
            accent = ThemeManager.get_accent_color(name)
            self.assertEqual(accent, THEMES[name].accent)
            self.assertTrue(accent.startswith("#"))
        # Fallback accent
        fallback_accent = ThemeManager.get_accent_color("Unknown")
        self.assertEqual(fallback_accent, THEMES["Dark"].accent)

if __name__ == "__main__":
    unittest.main()
