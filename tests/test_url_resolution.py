import unittest
import urllib.parse
from fibrowser.config import (
    SEARCH_ENGINES, DEFAULT_SEARCH_ENGINE, is_safe_local_path, format_error_message
)

class TestURLAndSearchResolution(unittest.TestCase):
    """Deep edge-case and boundary testing for URL resolution, search engines, and calculator."""

    def _resolve_input(self, text, current_engine="Google"):
        raw_text = text.strip()
        if not raw_text:
            return None, "empty"
            
        # Math calculation
        math_expr = None
        if raw_text.startswith("calc "):
            math_expr = raw_text[5:].strip()
        elif raw_text.startswith("= "):
            math_expr = raw_text[2:].strip()
        elif raw_text.startswith("=") and len(raw_text) > 1:
            math_expr = raw_text[1:].strip()
            
        if math_expr:
            try:
                allowed = set("0123456789+-*/().% ")
                if all(c in allowed for c in math_expr):
                    result = eval(math_expr, {"__builtins__": None}, {})
                    return result, "calculator"
                return None, "calc_disallowed"
            except ZeroDivisionError:
                return "ZeroDivisionError", "calc_error"
            except Exception as e:
                return str(e), "calc_error"

        # Commands
        cmd_lower = raw_text.lower()
        if cmd_lower in ("open settings", "settings"):
            return "settings", "command"
        elif cmd_lower in ("open downloads", "downloads"):
            return "downloads", "command"
        elif cmd_lower in ("open history", "history"):
            return "history", "command"
        elif cmd_lower in ("open bookmarks", "bookmarks"):
            return "bookmarks", "command"

        # URL vs Search
        is_search = False
        if ' ' in raw_text:
            is_search = True
        elif raw_text.startswith(('http://', 'https://', 'file://', 'view-source:', 'about:')):
            is_search = False
        elif '.' in raw_text and not raw_text.endswith('.'):
            is_search = False
        else:
            is_search = True
            
        if is_search:
            encoded_query = urllib.parse.quote_plus(raw_text)
            engine_template = SEARCH_ENGINES.get(current_engine, SEARCH_ENGINES["Google"])
            return engine_template.format(encoded_query), "search"
        else:
            if not raw_text.startswith(('http://', 'https://', 'file://', 'view-source:', 'about:')):
                raw_text = 'https://' + raw_text
            return raw_text, "url"

    def test_empty_and_whitespace_inputs(self):
        val, kind = self._resolve_input("")
        self.assertEqual(kind, "empty")
        val, kind = self._resolve_input("     ")
        self.assertEqual(kind, "empty")

    def test_search_queries_with_special_characters(self):
        query = "c++ & python #1 ? query=true"
        val, kind = self._resolve_input(query, "Google")
        self.assertEqual(kind, "search")
        self.assertTrue(val.startswith("https://www.google.com/search?q="))
        self.assertIn("c%2B%2B", val)
        self.assertIn("%26", val)
        self.assertIn("%231", val)

    def test_search_engines_switching(self):
        for engine, template in SEARCH_ENGINES.items():
            val, kind = self._resolve_input("test query", engine)
            self.assertEqual(kind, "search")
            expected_prefix = template.split("{}")[0]
            self.assertTrue(val.startswith(expected_prefix))

    def test_unicode_and_emoji_searches(self):
        val, kind = self._resolve_input("погода в москве 🚀 東京", "Google")
        self.assertEqual(kind, "search")
        self.assertIn("https://www.google.com/search?q=", val)

    def test_extreme_length_url_and_query(self):
        long_query = "word " * 2000
        val, kind = self._resolve_input(long_query, "Google")
        self.assertEqual(kind, "search")
        self.assertGreater(len(val), 5000)

    def test_standard_and_complex_urls(self):
        urls = [
            ("msn.com", "https://msn.com"),
            ("google.com/search?q=hello", "https://google.com/search?q=hello"),
            ("https://sub.domain.org:8080/path/to/page#anchor", "https://sub.domain.org:8080/path/to/page#anchor"),
            ("http://127.0.0.1:5000/api", "http://127.0.0.1:5000/api"),
            ("view-source:https://example.com", "view-source:https://example.com"),
            ("about:blank", "about:blank")
        ]
        for inp, expected in urls:
            val, kind = self._resolve_input(inp)
            self.assertEqual(kind, "url")
            self.assertEqual(val, expected)

    def test_calculator_standard_operations(self):
        cases = [
            ("calc 2 + 2", 4),
            ("= 100 - 35", 65),
            ("= 12 * 12", 144),
            ("calc 100 / 8", 12.5),
            ("= (10 + 5) * 3", 45),
            ("= 10 % 3", 1),
            ("= 2.5 * 4", 10.0),
            ("= -15 + 20", 5)
        ]
        for expr, expected in cases:
            val, kind = self._resolve_input(expr)
            self.assertEqual(kind, "calculator")
            self.assertEqual(val, expected)

    def test_calculator_edge_cases_and_security(self):
        # Divide by zero
        val, kind = self._resolve_input("= 10 / 0")
        self.assertEqual(kind, "calc_error")
        self.assertEqual(val, "ZeroDivisionError")

        # Disallowed strings & code injection attempts
        malicious = [
            "= __import__('os').system('calc')",
            "calc eval('1+1')",
            "= open('secret.txt')",
            "calc os.listdir('.')"
        ]
        for m in malicious:
            val, kind = self._resolve_input(m)
            self.assertEqual(kind, "calc_disallowed")

    def test_quick_commands_case_insensitivity(self):
        commands = [
            ("open settings", "settings"),
            ("SETTINGS", "settings"),
            ("Open Downloads", "downloads"),
            ("DOWNLOADS", "downloads"),
            ("open history", "history"),
            ("HISTORY", "history"),
            ("open bookmarks", "bookmarks"),
            ("BOOKMARKS", "bookmarks")
        ]
        for cmd, expected in commands:
            val, kind = self._resolve_input(cmd)
            self.assertEqual(kind, "command")
            self.assertEqual(val, expected)

    def test_path_traversal_protection(self):
        sensitive_paths = [
            "C:\\Windows\\System32\\config\\SAM",
            "C:/Windows/System32/config/SYSTEM",
            "C:\\Windows\\System32\\config\\SECURITY",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "/etc/passwd",
            "/etc/shadow",
            "C:\\Users\\User\\.ssh\\id_rsa",
            "C:\\Users\\User\\.ssh\\id_ed25519",
            "C:\\Users\\User\\project\\.env",
            "C:\\Windows\\NTDS\\ntds.dit"
        ]
        for p in sensitive_paths:
            self.assertFalse(is_safe_local_path(p), f"Path should be blocked: {p}")

        safe_paths = [
            "C:\\Users\\User\\Downloads\\sample.html",
            "C:/Users/User/Documents/report.pdf",
            "D:\\workspace\\project\\index.html",
            "C:\\temp\\test.txt"
        ]
        for p in safe_paths:
            self.assertTrue(is_safe_local_path(p), f"Path should be allowed: {p}")

if __name__ == '__main__':
    unittest.main()
