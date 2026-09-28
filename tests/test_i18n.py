"""The two languages have to stay the same shape as each other.

A missing key shows an English string inside a Chinese sentence; a parameter
that exists in one language and not the other prints a literal "{power}" on
screen in front of someone who cannot type a correction.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import i18n


PARAM = re.compile(r"\{(\w+)\}")


class LanguageParity(unittest.TestCase):
    def test_same_keys(self):
        english = set(i18n.STRINGS["en"])
        chinese = set(i18n.STRINGS["zh"])
        self.assertEqual(english - chinese, set(), "missing from zh")
        self.assertEqual(chinese - english, set(), "missing from en")

    def test_same_parameters(self):
        for key, english in i18n.STRINGS["en"].items():
            chinese = i18n.STRINGS["zh"][key]
            self.assertEqual(set(PARAM.findall(english)),
                             set(PARAM.findall(chinese)),
                             f"parameters differ for {key}")

    def test_nothing_is_left_in_english(self):
        """Every Chinese string should contain Chinese, with known exceptions."""
        # Product names, protocol words and single letters stay as they are.
        allowed = {
            "creds.client_id", "creds.client_secret", "pill.no_data",
            "pill.battery",  # an icon and a number, nothing to translate
            "board.speak", "board.backspace", "board.pause", "board.resume",
            "board.exit", "nav.phrases", "nav.api_settings",
        }
        han = re.compile(r"[一-鿿]")
        for key, chinese in i18n.STRINGS["zh"].items():
            if key in allowed or key.startswith("cell."):
                continue
            self.assertTrue(han.search(chinese), f"{key} has no Chinese text")


class Cells(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_known_token_translates(self):
        i18n.set_language("zh")
        self.assertEqual(i18n.cell("YES"), "是")

    def test_unknown_token_is_returned_as_typed(self):
        """A caregiver's own phrase has no translation and must survive intact."""
        i18n.set_language("zh")
        self.assertEqual(i18n.cell("GRANDMA MARIA"), "GRANDMA MARIA")
        self.assertEqual(i18n.cell("A"), "A")

    def test_every_default_phrase_has_a_translation(self):
        from scanning_board_setupandconfig import DEFAULT_PHRASES_LIST, BOARD_2_ALPHA

        tokens = list(DEFAULT_PHRASES_LIST)
        for row in BOARD_2_ALPHA:
            tokens.extend(row)

        missing = [tok for tok in tokens
                   if len(tok) > 1 and tok not in ("QU",)
                   and ("cell." + tok) not in i18n.STRINGS["zh"]]
        self.assertEqual(missing, [], "no Chinese for these board tokens")


class Formatting(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_parameters_are_substituted(self):
        self.assertIn("60", i18n.t("pill.contact", percent=60))

    def test_missing_parameter_does_not_raise(self):
        """A bad call must not take the board down mid-sentence."""
        self.assertIsInstance(i18n.t("pill.contact"), str)

    def test_unknown_key_returns_itself(self):
        self.assertEqual(i18n.t("nope.not.here"), "nope.not.here")


if __name__ == "__main__":
    unittest.main()
