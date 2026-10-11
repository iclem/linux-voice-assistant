"""Check assistant routing across successive automatic follow-ups."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from aioesphomeapi.api_pb2 import VoiceAssistantRequest

from linux_voice_assistant.satellite import VoiceSatelliteProtocol


class FollowupTests(unittest.TestCase):
    def make_satellite(self):
        satellite = VoiceSatelliteProtocol.__new__(VoiceSatelliteProtocol)
        satellite.state = SimpleNamespace(
            muted=False,
            stop_word=SimpleNamespace(id="stop"),
            active_wake_words=set(),
            tts_player=Mock(),
            continue_conversation_delay=0.1,
            wakeup_sound="wake.flac",
            start_listening_sound="listen.flac",
            listen_during_wake_sound=False,
        )
        satellite._pipeline_active = False
        satellite._continue_conversation = False
        satellite._conversation_wake_word_phrase = ""
        satellite.send_messages = Mock()
        satellite._emit = Mock()
        satellite.duck = Mock()
        satellite.unduck = Mock()
        return satellite

    def test_followups_keep_selected_wake_word(self):
        for phrase in ("Okay Nabu", "hey_luna"):
            with self.subTest(phrase=phrase):
                satellite = self.make_satellite()
                satellite.wakeup(SimpleNamespace(wake_word=phrase))
                for _ in range(2):
                    satellite._continue_conversation = True
                    with patch("linux_voice_assistant.satellite.threading.Timer") as timer:
                        satellite._tts_finished()
                        callback = timer.call_args.args[1]
                        callback()
                    message = satellite.send_messages.call_args.args[0][0]
                    self.assertIsInstance(message, VoiceAssistantRequest)
                    self.assertTrue(message.start)
                    self.assertEqual(message.wake_word_phrase, phrase)

    def test_manual_listening_clears_previous_selection(self):
        satellite = self.make_satellite()
        satellite._conversation_wake_word_phrase = "Okay Nabu"
        satellite.start_listening()
        self.assertEqual(satellite._conversation_wake_word_phrase, "")

    def test_muted_followup_does_not_start(self):
        satellite = self.make_satellite()
        satellite._continue_conversation = True
        with patch("linux_voice_assistant.satellite.threading.Timer") as timer:
            satellite._tts_finished()
            satellite.state.muted = True
            satellite.send_messages.reset_mock()
            timer.call_args.args[1]()
        satellite.send_messages.assert_not_called()
        self.assertFalse(satellite._pipeline_active)


if __name__ == "__main__":
    unittest.main()
