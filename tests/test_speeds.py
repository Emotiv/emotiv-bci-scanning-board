"""The scan speeds: the table itself, and that every one of them is reachable.

The slowest step matters more than the fast ones. Someone who needs four
seconds to produce a clench is not slower at deciding — they are slower at
signalling, and a board that has moved on before they can answer is unusable
rather than merely brisk.
"""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import i18n  # noqa: E402
import scanning_board_setupandconfig as sb  # noqa: E402


class SpeedTable(unittest.TestCase):
    def test_one_label_per_interval(self):
        self.assertEqual(len(sb.SCAN_INTERVALS), len(sb.SPEED_KEYS))

    def test_slowest_first_and_strictly_ordered(self):
        self.assertEqual(sb.SCAN_INTERVALS, sorted(sb.SCAN_INTERVALS, reverse=True))
        self.assertEqual(len(set(sb.SCAN_INTERVALS)), len(sb.SCAN_INTERVALS))

    def test_there_is_a_step_slower_than_the_old_slowest(self):
        # 2000 ms used to be as slow as the board went.
        self.assertLess(2000, sb.SCAN_INTERVALS[0])

    def test_default_is_in_range_and_is_not_an_extreme(self):
        self.assertTrue(0 < sb.DEFAULT_SPEED_INDEX < len(sb.SCAN_INTERVALS) - 1)

    def test_every_speed_is_named_in_both_languages(self):
        for key in sb.SPEED_KEYS:
            for language in i18n.LANGUAGES:
                self.assertIn(key, i18n.STRINGS[language], f"{key} missing from {language}")

    def test_the_names_are_distinct(self):
        """Two speeds that read the same are two speeds nobody can choose."""
        for language in i18n.LANGUAGES:
            names = [i18n.STRINGS[language][key] for key in sb.SPEED_KEYS]
            self.assertEqual(len(set(names)), len(names), f"duplicate name in {language}")


if __name__ == "__main__":
    unittest.main()
