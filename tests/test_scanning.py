"""Row/column scanning, and getting back out of a row chosen by mistake.

Selecting the wrong row used to trap the person in it: the only ways out were
to sit through every cell, or to select something wrong on purpose and delete
it afterwards. Neither is acceptable when a selection costs several seconds of
sustained effort.
"""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication  # noqa: E402

import i18n  # noqa: E402
import scanning_board_setupandconfig as sb  # noqa: E402

_app = QApplication.instance() or QApplication([])


def board():
    """A board with no Cortex behind it and no settings file to disturb."""
    sb.BCICommunicationBoard.start_cortex_worker = lambda self: None
    sb.BCICommunicationBoard.check_credentials_on_launch = lambda self: None
    sb.save_config = lambda patch: None
    w = sb.BCICommunicationBoard()
    w.page_container.setCurrentIndex(sb.PAGE_BOARD)
    return w


class Cancel(unittest.TestCase):
    def setUp(self):
        self.w = board()
        self.w.active_row = 3
        self.w.scanning_state = self.w.SCAN_ROWS

    def tearDown(self):
        # Never call close() here: the app's closeEvent ends the process with
        # os._exit, which would take the test runner with it.
        self.w.timer.stop()
        self.w.cooldown_ticker.stop()
        self.w.hide()

    def test_cancel_is_the_last_thing_the_sweep_offers(self):
        self.w.trigger_select_event()                 # lock the row
        self.assertEqual(self.w.scanning_state, self.w.SCAN_COLS)

        # Sweep the whole row: every cell, then CANCEL, then back to the start.
        seen = [self.w.active_col]
        for _ in range(self.w.cancel_index() + 1):
            self.w.advance_scanner()
            seen.append(self.w.active_col)

        self.assertEqual(seen[:-1], list(range(self.w.cancel_index() + 1)))
        self.assertEqual(seen[-1], 0, "the sweep must wrap round")
        self.assertIn(self.w.cancel_index(), seen, "CANCEL was never offered")

    def test_selecting_cancel_returns_to_row_scanning(self):
        self.w.trigger_select_event()
        self.w.active_col = self.w.cancel_index()
        self.w.trigger_select_event()

        self.assertEqual(self.w.scanning_state, self.w.SCAN_ROWS)
        self.assertEqual(self.w.cooldown_phase_key, "phase.cancelled")

    def test_cancelling_stays_on_the_same_row(self):
        """The row actually wanted is usually next to the one that was hit."""
        self.w.trigger_select_event()
        self.w.active_col = self.w.cancel_index()
        self.w.trigger_select_event()
        self.assertEqual(self.w.active_row, 3)

    def test_cancelling_says_nothing(self):
        before = self.w.composed_text
        self.w.trigger_select_event()
        self.w.active_col = self.w.cancel_index()
        self.w.trigger_select_event()
        self.assertEqual(self.w.composed_text, before)

    def test_cancelling_pauses_like_any_selection(self):
        """Whatever triggered the cancel is probably still being held."""
        self.w.trigger_select_event()
        self.w.active_col = self.w.cancel_index()
        self.w.trigger_select_event()
        self.assertTrue(self.w.in_cooldown)

    def test_a_normal_selection_still_works(self):
        self.w.trigger_select_event()
        self.w.active_col = 0
        expected = i18n.cell(self.w.current_matrix[3][0])
        self.w.trigger_select_event()

        self.assertIn(expected.strip(), self.w.composed_text)
        self.assertEqual(self.w.scanning_state, self.w.SCAN_ROWS)

    def test_the_cell_is_only_there_while_a_row_is_locked(self):
        self.assertTrue(self.w.cancel_cell.isHidden())
        self.w.trigger_select_event()
        self.assertFalse(self.w.cancel_cell.isHidden())
        self.w.active_col = self.w.cancel_index()
        self.w.trigger_select_event()
        self.assertTrue(self.w.cancel_cell.isHidden())

    def test_a_carer_can_click_it(self):
        self.w.trigger_select_event()
        self.w.cancel_cell.clicked.emit()
        self.assertEqual(self.w.scanning_state, self.w.SCAN_ROWS)

    def test_flipping_the_board_clears_the_locked_row(self):
        """The phrase board has a different width; a stale column would point
        at a cell that is not there."""
        self.w.trigger_select_event()
        self.w.process_selection("FLIP OVER")
        self.assertEqual(self.w.scanning_state, self.w.SCAN_ROWS)
        self.assertEqual(self.w.active_col, 0)

    def test_cancel_is_named_in_both_languages(self):
        self.assertEqual(i18n.STRINGS["en"]["cell.CANCEL"], "CANCEL")
        self.assertIn("cell.CANCEL", i18n.STRINGS["zh"])
        self.assertIn("phase.cancelled", i18n.STRINGS["zh"])


if __name__ == "__main__":
    unittest.main()
