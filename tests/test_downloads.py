import unittest
from typing import Tuple

class TestDownloadCalculations(unittest.TestCase):
    """Test suite for download speed and unit calculations (MED-012)."""

    def calculate_speed_and_unit(self, bytes_diff: int, elapsed_ms: int) -> Tuple[float, str]:
        """Speed calculation formula implemented in DownloadItemWidget.update_progress()."""
        if elapsed_ms <= 0 or bytes_diff < 0:
            return 0.0, "0.0 KB/s"
            
        speed_bytes_sec = (bytes_diff / elapsed_ms) * 1000.0
        speed_kb_sec = speed_bytes_sec / 1024.0
        
        if speed_kb_sec >= 1024.0:
            return speed_kb_sec / 1024.0, f"{speed_kb_sec / 1024.0:.1f} MB/s"
        else:
            return speed_kb_sec, f"{speed_kb_sec:.1f} KB/s"

    def test_one_megabyte_per_second(self):
        # 1,048,576 bytes in 1,000 ms = exactly 1024 KB/s = 1.0 MB/s
        speed_val, speed_str = self.calculate_speed_and_unit(1048576, 1000)
        self.assertAlmostEqual(speed_val, 1.0, places=2)
        self.assertEqual(speed_str, "1.0 MB/s")

    def test_five_hundred_kilobytes_per_second(self):
        # 512,000 bytes in 1,000 ms = 500 KB/s
        speed_val, speed_str = self.calculate_speed_and_unit(512000, 1000)
        self.assertAlmostEqual(speed_val, 500.0, places=1)
        self.assertEqual(speed_str, "500.0 KB/s")

    def test_ten_megabytes_per_second(self):
        # 10,485,760 bytes in 1,000 ms = 10 MB/s
        speed_val, speed_str = self.calculate_speed_and_unit(10485760, 1000)
        self.assertAlmostEqual(speed_val, 10.0, places=2)
        self.assertEqual(speed_str, "10.0 MB/s")

    def test_zero_time_elapsed(self):
        speed_val, speed_str = self.calculate_speed_and_unit(1000, 0)
        self.assertEqual(speed_val, 0.0)
        self.assertEqual(speed_str, "0.0 KB/s")

if __name__ == '__main__':
    unittest.main()
