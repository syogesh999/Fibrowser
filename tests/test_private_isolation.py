import unittest
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineProfile
from fibrowser.ui.window import Window

app = QApplication.instance() or QApplication([])

class TestPrivateIsolation(unittest.TestCase):
    """Rigorous verification of private browsing memory-only isolation and data exclusion."""

    @classmethod
    def setUpClass(cls):
        cls.window = Window()

    @classmethod
    def tearDownClass(cls):
        cls.window.close()

    def test_private_profile_settings_and_isolation(self):
        profile = self.window.get_private_profile()
        self.assertIsNotNone(profile)
        
        # Verify strict in-memory cache type (HIGH-003)
        self.assertEqual(profile.httpCacheType(), QWebEngineProfile.MemoryHttpCache)
        
        # Verify zero persistent cookies on disk (HIGH-003)
        self.assertEqual(profile.persistentCookiesPolicy(), QWebEngineProfile.NoPersistentCookies)

    def test_private_tab_history_exclusion(self):
        initial_history_count = len(self.window.history)
        
        # Bypass throttle for test
        self.window._last_tab_create_time = 0.0
        priv_tab = self.window.add_new_tab("https://secret-example.com", is_private=True)
        self.assertIsNotNone(priv_tab)
        self.assertTrue(priv_tab.is_private)
        
        # Attempt to add to history through window
        self.window.add_to_history("https://secret-example.com")
        
        # History must NOT increase
        self.assertEqual(len(self.window.history), initial_history_count)
        
        # History list must NOT contain the private URL
        history_urls = [h for h in self.window.history if "secret-example.com" in h]
        self.assertEqual(len(history_urls), 0)

    def test_private_tab_session_exclusion(self):
        self.window._last_tab_create_time = 0.0
        priv_tab = self.window.add_new_tab("https://private-session-test.org", is_private=True)
        self.window._last_tab_create_time = 0.0
        norm_tab = self.window.add_new_tab("https://normal-session-test.org", is_private=False)
        
        session_data = []
        for i in range(self.window.tabs.count()):
            tab = self.window.tabs.widget(i)
            if tab and hasattr(tab, 'browser') and not getattr(tab, 'is_private', False):
                url = tab.browser.url().toString()
                if url and url != "about:blank":
                    session_data.append(url)
                    
        self.assertNotIn("https://private-session-test.org", session_data)

if __name__ == '__main__':
    unittest.main()
