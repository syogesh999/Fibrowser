import unittest
import os
from installer import DEFAULT_INSTALL_DIR, create_windows_shortcut
from uninstall import UninstallerDialog
from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

class TestInstallerUninstaller(unittest.TestCase):
    """Test suite for installer options, uninstaller confirmation, and shortcut parameters."""

    def test_default_installation_directory(self):
        self.assertIn("Fibrowser Pro", DEFAULT_INSTALL_DIR)
        self.assertTrue(os.path.isabs(DEFAULT_INSTALL_DIR))

    def test_uninstaller_user_data_checkbox_defaults_to_false(self):
        dialog = UninstallerDialog()
        self.assertFalse(dialog.user_data_cb.isChecked())
        dialog.close()

    def test_shortcut_creation_with_valid_parameters(self):
        # Target test file
        target = os.path.abspath(__file__)
        shortcut_dir = os.path.dirname(target)
        shortcut_path = os.path.join(shortcut_dir, "test_temp_shortcut.lnk")
        
        # Test creation
        success = create_windows_shortcut(
            target_path=target,
            shortcut_path=shortcut_path,
            icon_path=None,
            description="Unit test shortcut"
        )
        if success and os.path.exists(shortcut_path):
            os.remove(shortcut_path)

if __name__ == '__main__':
    unittest.main()
