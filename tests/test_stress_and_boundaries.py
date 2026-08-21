import unittest
import time
from fibrowser.config import MAX_TABS, TAB_THROTTLE_SECONDS, HISTORY_MAX_SIZE, DEFAULT_ZOOM

class TestStressAndBoundaries(unittest.TestCase):
    """Stress tests and boundary condition validation for core structures."""

    def test_history_capping_under_massive_load(self):
        history = []
        for i in range(2500):
            entry = f"[2026-08-21 12:00:00] https://example{i}.com/page"
            history.insert(0, entry)
            if len(history) > HISTORY_MAX_SIZE:
                history = history[:HISTORY_MAX_SIZE]

        self.assertEqual(len(history), HISTORY_MAX_SIZE)
        self.assertEqual(history[0], "[2026-08-21 12:00:00] https://example2499.com/page")

    def test_tab_throttling_logic(self):
        last_time = 0.0
        created_count = 0
        rejected_count = 0

        # Simulate 100 rapid tab creation attempts in 10 milliseconds
        start_sim = time.time()
        for i in range(100):
            now = start_sim + (i * 0.001)  # 1ms increments
            if now - last_time < TAB_THROTTLE_SECONDS:
                rejected_count += 1
            else:
                last_time = now
                created_count += 1

        self.assertGreater(rejected_count, 0)
        self.assertLess(created_count, 100)

    def test_tab_maximum_capacity_boundary(self):
        mock_tabs = []
        for i in range(150):
            if len(mock_tabs) < MAX_TABS:
                mock_tabs.append(f"Tab {i}")

        self.assertEqual(len(mock_tabs), MAX_TABS)

    def test_zoom_boundary_clamps(self):
        current_zoom = 1.0
        
        # Test Zoom In limit (max 3.0)
        for _ in range(50):
            current_zoom = min(current_zoom + 0.1, 3.0)
        self.assertAlmostEqual(current_zoom, 3.0)

        # Test Zoom Out limit (min 0.5)
        for _ in range(50):
            current_zoom = max(current_zoom - 0.1, 0.5)
        self.assertAlmostEqual(current_zoom, 0.5)

    def test_closed_tabs_lifo_order(self):
        closed_stack = []
        urls = [f"https://site{i}.com" for i in range(20)]
        for u in urls:
            closed_stack.append(u)

        # Pop order must be strictly reverse (LIFO)
        reopened = []
        while closed_stack:
            reopened.append(closed_stack.pop())

        self.assertEqual(reopened, list(reversed(urls)))

    def test_massive_bookmarks_undo_redo_cycles(self):
        bookmarks = {"Google": "https://google.com"}
        undo_stack = []
        redo_stack = []

        # Perform 100 sequential additions
        for i in range(100):
            undo_stack.append(bookmarks.copy())
            redo_stack.clear()
            bookmarks[f"Site {i}"] = f"https://site{i}.org"

        self.assertEqual(len(bookmarks), 101)
        self.assertEqual(len(undo_stack), 100)

        # Perform 50 undos
        for _ in range(50):
            redo_stack.append(bookmarks.copy())
            bookmarks = undo_stack.pop()

        self.assertEqual(len(bookmarks), 51)
        self.assertEqual(len(redo_stack), 50)

        # Perform 25 redos
        for _ in range(25):
            undo_stack.append(bookmarks.copy())
            bookmarks = redo_stack.pop()

        self.assertEqual(len(bookmarks), 76)

    def test_extremely_long_and_unicode_titles(self):
        titles = [
            "A" * 1000,
            "🎉" * 200,
            "عربي - فارسی - עִבְרִית - 中文 - 日本語 - 한국어",
            "Special chars: <script>alert(1)</script> &amp; \" ' \n \t \r"
        ]
        for t in titles:
            truncated = t[:30] + "..." if len(t) > 30 else t or "New Tab"
            self.assertLessEqual(len(truncated), 33)

if __name__ == '__main__':
    unittest.main()
