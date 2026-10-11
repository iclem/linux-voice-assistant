import unittest
from unittest.mock import patch

from controller import Controller, MuteState


class Tests(unittest.TestCase):
    def test_510_relative_press_not_410_flash(self):
        state = MuteState()
        state.event({"event": "snapshot", "data": {"muted": False}})
        self.assertFalse(state.button(bytes([3, 11, 0])))
        self.assertFalse(state.button(bytes([4, 19, 0])))
        self.assertTrue(state.button(bytes([3, 19, 0])))
        self.assertTrue(state.muted)
        self.assertFalse(state.button(bytes([3, 19, 0])))
        self.assertFalse(state.button(bytes([3, 3, 0])))
        self.assertTrue(state.button(bytes([3, 19, 0])))
        self.assertFalse(state.muted)

    def test_idle_and_pipeline_events_do_not_unmute(self):
        state = MuteState()
        state.event({"event": "muted", "data": {"muted": True}})
        for event in ("idle", "listening", "tts_finished", "disconnected"):
            state.event({"event": event})
            self.assertTrue(state.muted)
        self.assertTrue(state.event({"event": "muted", "data": {"muted": False}}))
        self.assertFalse(state.muted)

    def test_offline_press_survives_snapshot_until_acknowledged(self):
        state = MuteState()
        state.event({"event": "snapshot", "data": {"muted": False}})
        state.button(bytes([3, 19, 0]))
        self.assertFalse(state.event({"event": "snapshot", "data": {"muted": False}}))
        self.assertTrue(state.muted)
        self.assertTrue(state.pending)
        self.assertTrue(state.event({"event": "muted", "data": {"muted": True}}))
        self.assertIsNone(state.pending)

    def test_hid_reports_and_shutdown_preserve_mute(self):
        controller = Controller(123)
        with patch("controller.os.write", return_value=3) as write:
            controller.state.event({"event": "snapshot", "data": {"muted": True}})
            controller.apply()
            write.assert_called_once_with(123, bytes([3, 5, 0]))
            controller.shutdown()
            self.assertEqual(write.call_count, 1)
            controller.state.event({"event": "muted", "data": {"muted": False}})
            controller.apply()
            write.assert_called_with(123, bytes([3, 1, 0]))
            controller.shutdown()
            write.assert_called_with(123, bytes([3, 0, 0]))

    def test_listening_flashes_but_mute_always_wins(self):
        controller = Controller(123)
        with patch("controller.os.write", return_value=3) as write:
            controller.state.event({"event": "snapshot", "data": {"muted": False}})
            for event in ("wake_word_detected", "listening"):
                controller.state.event({"event": event})
                controller.apply()
                write.assert_called_with(123, bytes([3, 9, 0]))
            controller.state.event({"event": "muted", "data": {"muted": True}})
            controller.state.event({"event": "listening"})
            controller.apply()
            write.assert_called_with(123, bytes([3, 5, 0]))
            controller.state.event({"event": "idle"})
            controller.apply()
            write.assert_called_with(123, bytes([3, 5, 0]))

    def test_end_of_listening_and_reconnection_clear_flashing(self):
        state = MuteState()
        for event in ("idle", "stt_text", "thinking", "tts_speaking", "tts_finished", "pipeline_error", "disconnected"):
            state.event({"event": "listening"})
            state.event({"event": event})
            self.assertFalse(state.listening)
        state.event({"event": "listening"})
        state.event({"event": "snapshot", "data": {"muted": False}})
        self.assertFalse(state.listening)
        state.event({"event": "listening"})  # Current-state replay after snapshot.
        self.assertTrue(state.listening)


if __name__ == "__main__":
    unittest.main()
