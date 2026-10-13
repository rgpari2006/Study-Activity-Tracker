import time
import unittest
from unittest.mock import MagicMock
from app.session import SessionManager, SessionState


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.mock_camera = MagicMock()
        self.sm = SessionManager(self.mock_camera)

    def test_initial_state(self):
        self.assertEqual(self.sm.state, SessionState.STOPPED)
        state = self.sm.get_state()
        self.assertEqual(state["session_state"], "stopped")
        self.assertEqual(state["elapsed_sec"], 0.0)

    def test_start_and_timer(self):
        self.sm.start(planned_duration_sec=1500)
        self.assertEqual(self.sm.state, SessionState.RUNNING)
        self.mock_camera.start.assert_called_once()

        time.sleep(0.1)
        elapsed = self.sm.elapsed_sec()
        self.assertGreaterEqual(elapsed, 0.09)

        state = self.sm.get_state()
        self.assertEqual(state["session_state"], "running")
        self.assertEqual(state["planned_duration_sec"], 1500)

    def test_pause_and_resume(self):
        self.sm.start(planned_duration_sec=60)
        time.sleep(0.1)
        self.sm.pause()
        self.assertEqual(self.sm.state, SessionState.PAUSED)

        paused_elapsed = self.sm.elapsed_sec()
        time.sleep(0.1)
        # Timer should be frozen while paused
        self.assertAlmostEqual(self.sm.elapsed_sec(), paused_elapsed, delta=0.03)

        self.sm.resume()
        self.assertEqual(self.sm.state, SessionState.RUNNING)
        time.sleep(0.1)
        self.assertGreater(self.sm.elapsed_sec(), paused_elapsed)

    def test_stop(self):
        self.sm.start(planned_duration_sec=60)
        self.sm.stop()
        self.assertEqual(self.sm.state, SessionState.STOPPED)
        self.mock_camera.stop.assert_called_once()
        self.assertEqual(self.sm.elapsed_sec(), 0.0)

    def test_invalid_transitions(self):
        with self.assertRaises(ValueError):
            self.sm.pause()  # Cannot pause when stopped
        with self.assertRaises(ValueError):
            self.sm.resume()  # Cannot resume when stopped
        with self.assertRaises(ValueError):
            self.sm.stop()  # Cannot stop when stopped


if __name__ == "__main__":
    unittest.main()
