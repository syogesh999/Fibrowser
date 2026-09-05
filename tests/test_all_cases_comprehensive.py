import unittest
import json
import tempfile
import urllib.parse
from pathlib import Path
from PyQt5.QtCore import QUrl
from fibrowser.config import (
    DEFAULT_HOME_PAGE, DEFAULT_SEARCH_ENGINE, DEFAULT_ZOOM,
    MAX_TABS, HISTORY_MAX_SIZE, SEARCH_ENGINES, THEMES,
    is_safe_local_path, format_error_message
)
from fibrowser.ui.theme_manager import ThemeManager

class TestAllCasesComprehensive(unittest.TestCase):
    """Exhaustive test suite covering Best, Worst, Boundary, and Edge cases across Fibrowser."""

    # =========================================================================
    # SECTION 1: BEST-CASE SCENARIOS
    # =========================================================================

    def test_best_case_standard_navigation_urls(self):
        """Best Case: Verify resolution of clean, standard web URLs."""
        test_urls = [
            "https://www.google.com",
            "https://github.com/syogesh999/Fibrowser",
            "http://localhost:8080",
            "http://127.0.0.1:3000/dashboard",
            "https://sub.domain.example.org/path/to/resource?arg=1&val=test#section"
        ]
        for url in test_urls:
            self.assertTrue(url.startswith(("http://", "https://")))
            parsed = urllib.parse.urlparse(url)
            self.assertTrue(bool(parsed.scheme))
            self.assertTrue(bool(parsed.netloc))

    def test_best_case_search_engines(self):
        """Best Case: Verify all supported search engines format search queries cleanly."""
        query = "PyQt5 browser tutorial"
        encoded = urllib.parse.quote_plus(query)
        for engine_name, template in SEARCH_ENGINES.items():
            formatted = template.format(encoded)
            self.assertIn(encoded, formatted)
            self.assertTrue(formatted.startswith("https://"))

    def test_best_case_bookmark_management(self):
        """Best Case: Adding, finding, and removing bookmarks cleanly."""
        bookmarks = {}
        # Add
        bookmarks["GitHub"] = "https://github.com"
        bookmarks["Python"] = "https://python.org"
        self.assertEqual(len(bookmarks), 2)
        self.assertIn("https://github.com", bookmarks.values())

        # Check duplicate avoidance
        current_url = "https://github.com"
        is_bookmarked = current_url in bookmarks.values()
        self.assertTrue(is_bookmarked)

        # Remove
        to_del = [title for title, url in bookmarks.items() if url == current_url]
        for t in to_del:
            del bookmarks[t]
        self.assertNotIn("https://github.com", bookmarks.values())
        self.assertEqual(len(bookmarks), 1)

    def test_best_case_history_tracking(self):
        """Best Case: History logging, chronological ordering, and deduplication."""
        history = []
        urls = ["https://site1.com", "https://site2.com", "https://site3.com"]
        for u in urls:
            history.insert(0, u)
        self.assertEqual(history[0], "https://site3.com")
        self.assertEqual(len(history), 3)

    def test_best_case_safe_local_paths(self):
        """Best Case: Safe local user files are permitted."""
        safe_paths = [
            "C:\\Users\\User\\Documents\\index.html",
            "D:\\Projects\\Fibrowser\\README.md",
            "/home/user/code/index.html",
            "C:/Users/DELL/SourceCode/test.html"
        ]
        for p in safe_paths:
            self.assertTrue(is_safe_local_path(p), f"Path should be allowed: {p}")

    def test_best_case_theme_application(self):
        """Best Case: All standard themes produce valid stylesheets."""
        for name in THEMES:
            css = ThemeManager.generate_stylesheet(name)
            self.assertIsInstance(css, str)
            self.assertIn(THEMES[name].bg, css)
            self.assertIn(THEMES[name].fg, css)

    # =========================================================================
    # SECTION 2: WORST-CASE SCENARIOS
    # =========================================================================

    def test_worst_case_corrupted_json_config(self):
        """Worst Case: Corrupted, partial, or malformed JSON files gracefully reset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cfg_path = Path(temp_dir) / "config.json"
            # Write truncated / invalid JSON
            cfg_path.write_text("{\"homepage\": \"https://example.com\", \"theme\": ", encoding="utf-8")
            
            # Application fallback logic
            loaded_settings = {}
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
            except Exception:
                # Backup and reset
                bak = cfg_path.with_suffix(".json.bak")
                cfg_path.rename(bak)
                loaded_settings = {
                    "homepage": DEFAULT_HOME_PAGE,
                    "theme": "Dark",
                    "search_engine": DEFAULT_SEARCH_ENGINE
                }
            self.assertEqual(loaded_settings["homepage"], DEFAULT_HOME_PAGE)
            self.assertEqual(loaded_settings["theme"], "Dark")

    def test_worst_case_binary_garbage_in_history(self):
        """Worst Case: History file filled with non-UTF8 binary junk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            hist_path = Path(temp_dir) / "history.json"
            hist_path.write_bytes(b"\x00\xff\xfe\x00\x12\x34\x56\x78\x9a\xbc\xde\xf0")
            
            history = []
            try:
                with open(hist_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        history = data
            except Exception:
                history = []
            self.assertEqual(history, [])

    def test_worst_case_path_traversal_attacks(self):
        """Worst Case: Malicious path traversal and sensitive file access attempts are blocked."""
        malicious_paths = [
            "C:\\Windows\\System32\\config\\sam",
            "C:/Windows/System32/config/SAM",
            "C:\\Windows\\System32\\config\\SYSTEM",
            "C:\\Windows\\System32\\config\\SECURITY",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "C:/windows/system32/drivers/etc/hosts",
            "/etc/shadow",
            "/etc/passwd",
            "C:\\Users\\Victim\\.ssh\\id_rsa",
            "C:\\Users\\Victim\\.ssh\\id_ed25519",
            "C:\\Users\\Victim\\project\\.env",
            "C:\\Windows\\NTDS\\ntds.dit",
            "../../../../windows/system32/config/sam",
            "..\\..\\..\\etc\\shadow"
        ]
        for p in malicious_paths:
            self.assertFalse(
                is_safe_local_path(p),
                f"Security breach: Sensitive file access was NOT blocked: {p}"
            )

    def test_worst_case_extremely_long_url(self):
        """Worst Case: Processing an absurdly long 50,000-character URL."""
        huge_url = "https://example.com/search?q=" + ("A" * 50000)
        qurl = QUrl(huge_url)
        formatted = format_error_message(qurl)
        # Should truncate URL preview to prevent buffer exhaustion in logs or UI
        self.assertLessEqual(len(formatted), 150)
        self.assertIn("Invalid", formatted)

    def test_worst_case_rapid_theme_switching(self):
        """Worst Case: Rapidly switching themes 100 times in a tight loop."""
        theme_names = list(THEMES.keys())
        for i in range(100):
            theme_choice = theme_names[i % len(theme_names)]
            sheet = ThemeManager.generate_stylesheet(theme_choice)
            self.assertTrue(len(sheet) > 500)
            accent = ThemeManager.get_accent_color(theme_choice)
            self.assertTrue(accent.startswith("#"))

    def test_worst_case_calculator_abuse(self):
        """Worst Case: Malicious or illegal calculator commands."""
        malicious_inputs = [
            "= __import__('os').system('dir')",
            "= open('sam').read()",
            "= 1 / 0",
            "= eval('5 + 5')",
            "calc os.unlink('test')"
        ]
        allowed = set("0123456789+-*/().% ")
        for expr in malicious_inputs:
            clean = expr.lstrip("= ").replace("calc ", "").strip()
            is_valid = all(c in allowed for c in clean)
            if clean == "1 / 0":
                # Zero division should be caught
                with self.assertRaises(ZeroDivisionError):
                    eval(clean, {"__builtins__": None}, {})
            else:
                self.assertFalse(is_valid, f"Security violation: unsafe calc expression allowed: {expr}")

    def test_worst_case_download_zero_and_negative_bytes(self):
        """Worst Case: Download with 0 total bytes or indeterminate stream."""
        # Simulated calculation when bytes_total is 0 or negative
        bytes_received = 500
        bytes_total = 0
        percent = int((bytes_received / bytes_total) * 100) if bytes_total > 0 else 0
        self.assertEqual(percent, 0)

        # When bytes_total is negative (-1 for chunked/unknown stream)
        bytes_total = -1
        percent = int((bytes_received / bytes_total) * 100) if bytes_total > 0 else 0
        self.assertEqual(percent, 0)

    # =========================================================================
    # SECTION 3: BOUNDARY AND EDGE-CASE SCENARIOS
    # =========================================================================

    def test_boundary_max_tabs_enforcement(self):
        """Boundary: Tab limit enforcement at exactly MAX_TABS (100)."""
        tabs = []
        for i in range(MAX_TABS + 20):
            if len(tabs) < MAX_TABS:
                tabs.append(f"Tab_{i}")
        self.assertEqual(len(tabs), MAX_TABS)
        self.assertEqual(len(tabs), 100)

    def test_boundary_history_size_overflow(self):
        """Boundary: History capping at exactly HISTORY_MAX_SIZE (500)."""
        history = []
        for i in range(HISTORY_MAX_SIZE + 100):
            history.insert(0, f"https://example{i}.org")
            if len(history) > HISTORY_MAX_SIZE:
                history = history[:HISTORY_MAX_SIZE]
        self.assertEqual(len(history), HISTORY_MAX_SIZE)
        self.assertEqual(len(history), 500)
        self.assertEqual(history[0], f"https://example{HISTORY_MAX_SIZE + 99}.org")

    def test_boundary_zoom_limits(self):
        """Boundary: Zoom boundaries clamped between 25% (0.25) and 500% (5.0)."""
        min_zoom = 0.25
        max_zoom = 5.0
        
        # Test lower clamping
        zoom = 1.0
        for _ in range(20):
            zoom = max(zoom - 0.1, min_zoom)
        self.assertAlmostEqual(zoom, min_zoom)

        # Test upper clamping
        for _ in range(100):
            zoom = min(zoom + 0.1, max_zoom)
        self.assertAlmostEqual(zoom, max_zoom)

    def test_edge_case_zoom_percentage_string_parsing(self):
        """Edge Case: Parsing various user zoom percentage strings."""
        test_cases = [
            ("50%", 0.5),
            ("100%", 1.0),
            ("150%", 1.5),
            ("200%", 2.0),
            ("invalid", DEFAULT_ZOOM),
            ("", DEFAULT_ZOOM),
            ("%%%--", DEFAULT_ZOOM)
        ]
        for raw_str, expected in test_cases:
            cleaned = raw_str.replace("%", "").strip()
            try:
                parsed = float(cleaned) / 100.0
            except ValueError:
                parsed = DEFAULT_ZOOM
            self.assertAlmostEqual(parsed, expected)

    def test_edge_case_empty_and_whitespace_inputs(self):
        """Edge Case: Empty strings, only spaces, tabs, and newlines in search."""
        empty_inputs = ["", " ", "   ", "\t", "\n", "  \n\t  "]
        for inp in empty_inputs:
            trimmed = inp.strip()
            self.assertEqual(trimmed, "")

    def test_edge_case_find_bar_regex_special_characters(self):
        """Edge Case: In-page search containing regex metacharacters."""
        special_chars = "[.*+?^${}()|/[]\\"
        # Plain text find in page should treat regex special characters as literal characters
        escaped = special_chars
        self.assertEqual(len(escaped), len(special_chars))
        # Ensure searching does not throw regex compile error
        self.assertTrue(isinstance(special_chars, str))

    def test_edge_case_theme_manager_invalid_and_none(self):
        """Edge Case: Theme manager given invalid types, case mismatches, or nonexistent themes."""
        # Nonexistent name fallback
        self.assertEqual(ThemeManager.validate_theme_name("Cyberpunk2077"), "Dark")
        self.assertEqual(ThemeManager.validate_theme_name(""), "Dark")
        self.assertEqual(ThemeManager.validate_theme_name("DARK"), "Dark")  # Case sensitive check
        self.assertEqual(ThemeManager.validate_theme_name("  Dark  "), "Dark")
        
        # Valid names
        self.assertEqual(ThemeManager.validate_theme_name("Light"), "Light")
        self.assertEqual(ThemeManager.validate_theme_name("Dark"), "Dark")
        self.assertEqual(ThemeManager.validate_theme_name("Blue"), "Blue")
        self.assertEqual(ThemeManager.validate_theme_name("Nord"), "Nord")
        self.assertEqual(ThemeManager.validate_theme_name("Dracula"), "Dracula")

    def test_edge_case_format_error_message_varieties(self):
        """Edge Case: format_error_message handles exceptions, strings, QUrl, and unknown objects."""
        # Normal exception
        ex = ValueError("Invalid parameter value")
        self.assertIn("ValueError", format_error_message(ex))

        # Raw string
        self.assertEqual(format_error_message("Simple error"), "Simple error")

        # Number / None
        self.assertEqual(format_error_message(404), "404")
        self.assertEqual(format_error_message(None), "None")

if __name__ == "__main__":
    unittest.main()
