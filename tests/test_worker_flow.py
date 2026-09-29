"""The connection sequence, driven by a stub Cortex. No headset, no network.

This exists because of a bug that shipped: `create_session_done` was bound to a
lambda, and python-dispatch keeps listeners WEAKLY, so the lambda was collected
before Cortex could ever call it. The app authorized, connected, reported
"Approved. Connecting…" — and then sat there forever, because the callback that
subscribes to the data streams never ran. Nothing in the unit tests or the
rendered screens could see it; only a real headset could.
"""
import os
import sys
import types
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pydispatch import Dispatcher  # noqa: E402
from PyQt6.QtCore import QCoreApplication  # noqa: E402

_app = QCoreApplication.instance() or QCoreApplication([])

import scanning_board_setupandconfig as sb  # noqa: E402


class StubCortex(Dispatcher):
    """Emits what the real client emits, in the order it emits it."""

    _events_ = ['inform_error', 'create_session_done', 'new_data_labels',
                'new_com_data', 'new_fe_data', 'new_dev_data', 'new_eq_data',
                'headset_list_done', 'sub_failure', 'access_pending',
                'access_granted', 'access_rejected']

    def __init__(self, client_id, client_secret, *a, **k):
        self.client_id = client_id
        self.client_secret = client_secret
        self.headset_id = ''
        self.subscribed = []
        self.loaded_profile = None

    def set_wanted_headset(self, headset_id):
        self.headset_id = headset_id

    def sub_request(self, streams):
        self.subscribed = list(streams)
        # Cortex answers a subscription with the column names, and only then
        # does data start.
        self.emit('new_data_labels',
                  data={'streamName': 'dev', 'labels': ['AF3', 'T7', 'Pz', 'T8', 'AF4']})
        self.emit('new_data_labels',
                  data={'streamName': 'eq', 'labels': ['AF3', 'T7', 'Pz', 'T8', 'AF4']})

    def setup_profile(self, name, status):
        self.loaded_profile = (name, status)

    def query_headset(self):
        self.emit('headset_list_done', data=[
            {'id': 'INSIGHT2-A3D2F1C0', 'status': 'connected',
             'connectedBy': 'dongle'}])

    def retry_access(self):
        self.emit('access_granted', data='')

    def open(self):
        """The real one blocks here running the websocket."""
        self.emit('access_granted', data='')
        self.query_headset()

    # -- things the test does on the app's behalf ------------------------
    def create_session(self):
        self.emit('create_session_done', data='session-1')

    def send_dev(self, values):
        self.emit('new_dev_data', data={'signal': 2, 'batteryPercent': 80,
                                        'dev': values})

    def send_eq(self, values):
        self.emit('new_eq_data', data={'batteryPercent': 80, 'overall': 4,
                                       'sampleRateQuality': 1, 'eq': values})


def run_worker(config):
    """Start the real worker against the stub, and collect what it emits."""
    sb.load_config = lambda: dict(config)

    module = types.ModuleType("cortex")
    module.Cortex = StubCortex
    sys.modules["cortex"] = module

    worker = sb.EmotivCortexWorker()
    seen = {"headsets": [], "contact": [], "eeg": [], "status": [],
            "access": [], "battery": []}
    worker.headsets_signal.connect(lambda h: seen["headsets"].append(h))
    worker.contact_quality_signal.connect(lambda m: seen["contact"].append(m))
    worker.eeg_quality_signal.connect(lambda m: seen["eeg"].append(m))
    worker.status_signal.connect(lambda c, p: seen["status"].append(c))
    worker.access_state_signal.connect(lambda s, d: seen["access"].append(s))
    worker.device_diagnostics_signal.connect(
        lambda b, s: seen["battery"].append(b))
    worker.run()
    return worker, seen


KEYS = {"cortex_client_id": "an-id", "cortex_client_secret": "a-secret",
        "profile_name": "Giovani"}


class ConnectionSequence(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("cortex", None)

    def test_session_callback_survives(self):
        """The regression: the session event has to reach the worker.

        A listener that python-dispatch has already collected leaves the app
        connected and silent, which is exactly what the user saw.
        """
        worker, seen = run_worker(KEYS)
        worker.cortex.set_wanted_headset("INSIGHT2-A3D2F1C0")
        worker.cortex.create_session()

        self.assertTrue(worker.cortex.subscribed,
                        "create_session_done never reached the worker, so nothing "
                        "was ever subscribed")

    def test_it_subscribes_to_quality_and_commands(self):
        worker, seen = run_worker(KEYS)
        worker.cortex.create_session()
        self.assertIn("dev", worker.cortex.subscribed)
        self.assertIn("eq", worker.cortex.subscribed)
        self.assertIn("com", worker.cortex.subscribed)

    def test_the_trained_profile_is_loaded(self):
        worker, seen = run_worker(KEYS)
        worker.cortex.create_session()
        self.assertEqual(worker.cortex.loaded_profile, ("Giovani", "load"))

    def test_quality_reaches_the_interface(self):
        worker, seen = run_worker(KEYS)
        worker.cortex.create_session()
        worker.cortex.send_dev([4, 4, 0, 4, 3])
        worker.cortex.send_eq([4, 3, 2, 4, 4])

        self.assertEqual(seen["contact"][-1],
                         {"AF3": 4, "T7": 4, "Pz": 0, "T8": 4, "AF4": 3})
        self.assertEqual(seen["eeg"][-1],
                         {"AF3": 4, "T7": 3, "Pz": 2, "T8": 4, "AF4": 4})
        self.assertEqual(seen["battery"][-1], 80)
        self.assertIn("status.live", seen["status"])

    def test_the_headset_list_reaches_the_interface(self):
        worker, seen = run_worker(KEYS)
        self.assertEqual(seen["headsets"][-1][0]["id"], "INSIGHT2-A3D2F1C0")

    def test_no_keys_asks_for_keys_instead_of_connecting(self):
        worker, seen = run_worker({"cortex_client_id": "", "cortex_client_secret": ""})
        self.assertEqual(seen["access"], ["credentials"])
        self.assertIsNone(worker.cortex)

    def test_mn8_is_not_subscribed_to_facial(self):
        worker, seen = run_worker(KEYS)
        worker.cortex.set_wanted_headset("MN8-B4091A22")
        worker.cortex.create_session()
        self.assertNotIn("fac", worker.cortex.subscribed)


class NoWeakListeners(unittest.TestCase):
    def test_pydispatch_really_does_drop_lambdas(self):
        """Why the rule below exists, demonstrated rather than asserted."""
        import gc

        class D(Dispatcher):
            _events_ = ['thing']

        fired = []
        d = D()
        d.bind(thing=lambda *a, **k: fired.append(1))
        gc.collect()
        d.emit('thing', data=1)
        self.assertEqual(fired, [], "python-dispatch now keeps lambdas alive; the "
                                    "rule below can be relaxed")

    def test_every_cortex_listener_is_a_bound_method(self):
        with open(os.path.join(ROOT, "scanning_board_setupandconfig.py"),
                  encoding="utf-8") as f:
            source = f.read()

        for line in source.splitlines():
            stripped = line.strip()
            if not stripped.startswith("cortex.bind("):
                continue
            self.assertNotIn("lambda", stripped,
                             f"weakly-held listener would never fire: {stripped}")
            target = stripped.split("=", 1)[1].rstrip(")").strip()
            self.assertTrue(target.startswith("self."),
                            f"listener must be a bound method: {stripped}")


if __name__ == "__main__":
    unittest.main()
