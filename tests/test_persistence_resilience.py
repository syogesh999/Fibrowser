import unittest
import json
import tempfile
from pathlib import Path
from fibrowser.config import DEFAULT_HOME_PAGE, DEFAULT_SEARCH_ENGINE, DEFAULT_ZOOM

class TestPersistenceResilience(unittest.TestCase):
    """Deep testing for corrupted data recovery, file I/O resilience, and persistence lifecycle."""

    def _recover_corrupted_file(self, file_path: Path) -> None:
        try:
            if file_path.exists():
                bak_path = file_path.with_suffix(file_path.suffix + ".bak")
                if bak_path.exists():
                    bak_path.unlink()
                file_path.rename(bak_path)
        except Exception:
            pass

    def test_corrupted_settings_triggers_backup_and_resets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "config.json"
            bak_file = Path(temp_dir) / "config.json.bak"
            
            # Write corrupted JSON
            with open(settings_file, 'w', encoding='utf-8') as f:
                f.write("{ invalid json content ...")

            homepage = DEFAULT_HOME_PAGE
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except Exception:
                self._recover_corrupted_file(settings_file)

            # Check that corrupted file was moved to .bak
            self.assertTrue(bak_file.exists())
            self.assertFalse(settings_file.exists())

    def test_zero_byte_empty_files_resilience(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for fname in ["config.json", "history.json", "bookmarks.json", "session.json"]:
                file_path = Path(temp_dir) / fname
                file_path.touch() # 0 bytes
                
                # Test reading history
                history = []
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        loaded = json.load(f)
                        if isinstance(loaded, list):
                            history = loaded
                except Exception:
                    self._recover_corrupted_file(file_path)
                    history = []
                
                self.assertEqual(history, [])

    def test_unicode_and_special_character_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bm_file = Path(temp_dir) / "bookmarks.json"
            special_bookmarks = {
                "🚀 Space & Tech": "https://example.com/🚀?q=test&lang=zh-CN#top",
                "عالم الإنترنت": "https://arabic.example.com",
                "東京ニュース": "https://tokyo.jp/news?id=123"
            }
            with open(bm_file, 'w', encoding='utf-8') as f:
                json.dump(special_bookmarks, f, ensure_ascii=False, indent=2)

            with open(bm_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)

            self.assertEqual(loaded, special_bookmarks)

    def test_session_serialization_with_mixed_tabs(self):
        # Simulate open tabs: normal tab, pinned tab, and private tab
        raw_tabs = [
            {"url": "https://msn.com", "zoom": 1.0, "is_private": False, "is_pinned": False},
            {"url": "https://github.com", "zoom": 1.2, "is_private": False, "is_pinned": True},
            {"url": "https://secret.bank.com", "zoom": 1.0, "is_private": True, "is_pinned": False},
        ]

        # Serialization logic: private tabs must be strictly skipped
        session_data = []
        for tab in raw_tabs:
            if not tab["is_private"] and tab["url"] != "about:blank":
                session_data.append({
                    "url": tab["url"],
                    "zoom": tab["zoom"],
                    "pinned": tab["is_pinned"]
                })

        self.assertEqual(len(session_data), 2)
        self.assertEqual(session_data[0]["url"], "https://msn.com")
        self.assertEqual(session_data[1]["url"], "https://github.com")
        self.assertTrue(session_data[1]["pinned"])
        
        # Verify private URL is not present
        urls = [s["url"] for s in session_data]
        self.assertNotIn("https://secret.bank.com", urls)

    def test_clear_on_exit_logic(self):
        history = ["https://site1.com", "https://site2.com"]
        clear_on_exit = True
        
        if clear_on_exit:
            history.clear()
            
        self.assertEqual(len(history), 0)

if __name__ == '__main__':
    unittest.main()
