"""The headset table and the layout that is built from Cortex's own channel names.

The bug these tests exist to prevent: the app used to assume five sensors named
AF3/T7/Pz/T8/AF4, so an EPOC X showed five of its fourteen electrodes and an MN8
showed five electrodes it does not have.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import devices


class Describe(unittest.TestCase):
    def test_insight(self):
        info = devices.describe("INSIGHT2-A3D2F1C0")
        self.assertEqual(len(info["channels"]), 5)
        self.assertTrue(info["has_facial"])

    def test_epoc_x(self):
        info = devices.describe("EPOCX-3B29D471")
        self.assertEqual(len(info["channels"]), 14)
        self.assertIn("O1", info["channels"])
        self.assertTrue(info["has_facial"])

    def test_mn8_has_two_channels_and_no_facial(self):
        """MN8 has no `fac` stream at all — this is the one capability that
        cannot be discovered by trying, because asking for it fails."""
        info = devices.describe("MN8-B4091A22")
        self.assertEqual(info["channels"], ["T7", "T8"])
        self.assertFalse(info["has_facial"])
        self.assertNotIn("fac", devices.streams_for("MN8-B4091A22"))

    def test_longest_prefix_wins(self):
        self.assertEqual(devices.describe("INSIGHT2-1")["prefix"], "INSIGHT2")
        self.assertEqual(devices.describe("EPOCX-1")["prefix"], "EPOCX")
        self.assertEqual(devices.describe("EPOCPLUS-1")["prefix"], "EPOCPLUS")
        self.assertEqual(devices.describe("FLEX2-1")["prefix"], "FLEX2")

    def test_unknown_headset_is_not_crippled(self):
        info = devices.describe("SOMETHINGNEW-0001")
        self.assertFalse(info["known"])
        self.assertEqual(info["channels"], [])
        self.assertIn("fac", devices.streams_for("SOMETHINGNEW-0001"))

    def test_quality_streams_are_always_requested(self):
        for headset in ("INSIGHT-1", "EPOCX-1", "MN8-1"):
            streams = devices.streams_for(headset)
            self.assertIn("dev", streams)   # contact quality
            self.assertIn("eq", streams)    # EEG quality
            self.assertIn("com", streams)   # mental commands

    def test_facial_can_be_declined_by_the_user(self):
        self.assertNotIn("fac", devices.streams_for("EPOCX-1", want_facial=False))


class Layout(unittest.TestCase):
    def test_every_channel_is_placed(self):
        for channels in (devices.INSIGHT_CHANNELS, devices.EPOC_CHANNELS,
                         devices.MN8_CHANNELS):
            placed = devices.layout_for(channels)
            self.assertEqual(len(placed), len(channels))

    def test_positions_stay_inside_the_head(self):
        for name, x, y in devices.layout_for(devices.EPOC_CHANNELS):
            self.assertLessEqual(abs(x), 1.0, name)
            self.assertLessEqual(abs(y), 1.0, name)

    def test_left_and_right_are_not_mirrored(self):
        placed = dict((name, (x, y)) for name, x, y in
                      devices.layout_for(devices.EPOC_CHANNELS))
        self.assertLess(placed["T7"][0], 0)      # T7 is on the left
        self.assertGreater(placed["T8"][0], 0)   # T8 on the right
        self.assertLess(placed["AF3"][1], 0)     # AF3 towards the front
        self.assertGreater(placed["O1"][1], 0)   # O1 towards the back

    def test_unknown_channel_names_are_still_drawn(self):
        placed = devices.layout_for(["T7", "MADE_UP_1", "MADE_UP_2"])
        self.assertEqual(len(placed), 3)

    def test_empty_is_empty(self):
        self.assertEqual(devices.layout_for([]), [])
        self.assertEqual(devices.layout_for(None), [])


class Quality(unittest.TestCase):
    def test_percent_counts_usable_sensors(self):
        # Cortex grades 0-4; 3 and 4 are usable, which is where the map turns
        # a node green.
        self.assertEqual(devices.quality_percent([4, 4, 4, 4]), 100)
        self.assertEqual(devices.quality_percent([4, 4, 0, 0]), 50)
        self.assertEqual(devices.quality_percent([2, 2]), 0)

    def test_percent_without_data(self):
        self.assertEqual(devices.quality_percent([]), 0)
        self.assertEqual(devices.quality_percent(None), 0)

    def test_weak_sensors_are_named(self):
        weak = devices.weak_sensors({"AF3": 4, "T7": 1, "Pz": 4, "T8": 0})
        self.assertEqual(weak, ["T7", "T8"])


if __name__ == "__main__":
    unittest.main()
