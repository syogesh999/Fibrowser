import unittest
import sys
from PyQt5.QtWidgets import QApplication, QWidget
from fibrowser.ui.shortcut_manager import ShortcutManager

class TestShortcutManager(unittest.TestCase):
    """Test suite for keyboard shortcut manager."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.widget = QWidget()
        self.mgr = ShortcutManager(self.widget)

    def tearDown(self):
        self.mgr.clear()
        self.widget.deleteLater()

    def test_register_and_get_shortcut(self):
        called = []
        def callback():
            called.append(True)

        sc = self.mgr.register("test_action", "Ctrl+T", callback, "Test action description")
        self.assertIsNotNone(sc)
        self.assertEqual(self.mgr.get_sequence("test_action"), "Ctrl+T")
        self.assertEqual(self.mgr.get_shortcut("test_action"), sc)

    def test_update_sequence(self):
        self.mgr.register("test_action", "Ctrl+T", lambda: None)
        success = self.mgr.update_sequence("test_action", "Ctrl+N")
        self.assertTrue(success)
        self.assertEqual(self.mgr.get_sequence("test_action"), "Ctrl+N")

    def test_clear_shortcuts(self):
        self.mgr.register("act1", "Ctrl+1", lambda: None)
        self.mgr.register("act2", "Ctrl+2", lambda: None)
        self.assertEqual(len(self.mgr.shortcuts), 2)
        self.mgr.clear()
        self.assertEqual(len(self.mgr.shortcuts), 0)

if __name__ == '__main__':
    unittest.main()
