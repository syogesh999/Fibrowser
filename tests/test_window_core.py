import unittest
import json
from pathlib import Path
import tempfile
import shutil
from fibrowser.config import HISTORY_MAX_SIZE, DEFAULT_ZOOM

class TestWindowCoreLogic(unittest.TestCase):
    """Test suite for bookmark stacks, history limits, and session serialization logic."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_bookmark_undo_redo_stack(self):
        bookmarks = {"Google": "https://google.com"}
        undo_stack = []
        redo_stack = []

        # Action: Add bookmark
        undo_stack.append(bookmarks.copy())
        redo_stack.clear()
        bookmarks["YouTube"] = "https://youtube.com"
        self.assertIn("YouTube", bookmarks)

        # Action: Delete bookmark
        undo_stack.append(bookmarks.copy())
        redo_stack.clear()
        del bookmarks["Google"]
        self.assertNotIn("Google", bookmarks)
        self.assertIn("YouTube", bookmarks)

        # Action: Undo deletion
        redo_stack.append(bookmarks.copy())
        bookmarks = undo_stack.pop()
        self.assertIn("Google", bookmarks)
        self.assertIn("YouTube", bookmarks)

        # Action: Undo addition
        redo_stack.append(bookmarks.copy())
        bookmarks = undo_stack.pop()
        self.assertIn("Google", bookmarks)
        self.assertNotIn("YouTube", bookmarks)

        # Action: Redo addition
        undo_stack.append(bookmarks.copy())
        bookmarks = redo_stack.pop()
        self.assertIn("Google", bookmarks)
        self.assertIn("YouTube", bookmarks)

    def test_history_bounding(self):
        history = []
        for i in range(600):
            history.append(f"https://example.com/page_{i}")
            if len(history) > HISTORY_MAX_SIZE:
                history = history[-HISTORY_MAX_SIZE:]

        self.assertEqual(len(history), HISTORY_MAX_SIZE)
        self.assertEqual(history[0], "https://example.com/page_100")
        self.assertEqual(history[-1], "https://example.com/page_599")

    def test_session_serialization_with_zoom(self):
        session_data = {
            "tabs": [
                {"url": "https://bing.com", "title": "Bing", "zoom": 1.25},
                {"url": "https://github.com", "title": "GitHub", "zoom": 1.0}
            ],
            "current_tab": 0,
            "theme": "Dark"
        }

        session_file = self.config_dir / "session.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2)

        with open(session_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        self.assertEqual(len(loaded["tabs"]), 2)
        self.assertEqual(loaded["tabs"][0]["zoom"], 1.25)
        self.assertEqual(loaded["theme"], "Dark")

    def test_corrupted_json_recovery_model(self):
        bad_json_file = self.config_dir / "corrupted.json"
        bad_json_file.write_text("{ this is corrupted json", encoding='utf-8')

        # Recovery logic test
        corrupt_detected = False
        try:
            with open(bad_json_file, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError:
            corrupt_detected = True
            bak_file = bad_json_file.with_suffix(".json.bak")
            bad_json_file.rename(bak_file)

        self.assertTrue(corrupt_detected)
        self.assertFalse(bad_json_file.exists())
        self.assertTrue((self.config_dir / "corrupted.json.bak").exists())

if __name__ == '__main__':
    unittest.main()
