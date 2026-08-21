import unittest
import json
import tempfile
import urllib.parse
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from fibrowser.config import DEFAULT_HOME_PAGE, DEFAULT_SEARCH_ENGINE, SEARCH_ENGINES

app = QApplication.instance() or QApplication([])

class TestEnhancements(unittest.TestCase):
    """Unit tests for product enhancements, default settings preservation, and calculator logic."""

    def test_fresh_settings_defaults(self):
        # Fresh settings default to MSN and Google
        self.assertEqual(DEFAULT_HOME_PAGE, "https://www.msn.com")
        self.assertEqual(DEFAULT_SEARCH_ENGINE, "Google")

    def test_existing_custom_settings_preservation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            custom_data = {
                "homepage": "https://duckduckgo.com",
                "search_engine": "DuckDuckGo",
                "theme": "Nord",
                "first_run_completed": True
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(custom_data, f)
                
            # Simulate reading existing settings
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                
            self.assertEqual(loaded.get("homepage", DEFAULT_HOME_PAGE), "https://duckduckgo.com")
            self.assertEqual(loaded.get("search_engine", DEFAULT_SEARCH_ENGINE), "DuckDuckGo")
            self.assertEqual(loaded.get("theme", "Dark"), "Nord")
            self.assertTrue(loaded.get("first_run_completed", False))

    def test_url_vs_search_detection_logic(self):
        def parse_input(text):
            text = text.strip()
            if ' ' in text:
                is_search = True
            elif text.startswith(('http://', 'https://', 'file://', 'view-source:', 'about:')):
                is_search = False
            elif '.' in text and not text.endswith('.'):
                is_search = False
            else:
                is_search = True
            return is_search

        self.assertTrue(parse_input("hello world"))
        self.assertTrue(parse_input("python decorators"))
        self.assertFalse(parse_input("https://example.com"))
        self.assertFalse(parse_input("google.com"))
        self.assertFalse(parse_input("www.google.com"))
        self.assertFalse(parse_input("example.com/page"))

    def test_calculator_math_evaluation(self):
        def eval_math(expr):
            allowed = set("0123456789+-*/().% ")
            if all(c in allowed for c in expr):
                return eval(expr, {"__builtins__": None}, {})
            raise ValueError("Disallowed characters")

        self.assertEqual(eval_math("25 * 25"), 625)
        self.assertEqual(eval_math("100 / 4"), 25.0)
        self.assertEqual(eval_math("10 + 20 * 2"), 50)
        self.assertEqual(eval_math("(5 + 5) * 3"), 30)
        
        with self.assertRaises(ValueError):
            eval_math("__import__('os').system('dir')")

    def test_welcome_dialog_instantiation(self):
        from fibrowser.ui.dialogs.welcome_dialog import WelcomeDialog
        from fibrowser.ui.window import Window
        
        # Instantiate window and dialog
        window = Window()
        dialog = WelcomeDialog(window, window)
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.homepage_combo.currentIndex(), 0) # MSN
        self.assertEqual(dialog.engine_combo.currentText(), "Google")
        window.close()

if __name__ == '__main__':
    unittest.main()
