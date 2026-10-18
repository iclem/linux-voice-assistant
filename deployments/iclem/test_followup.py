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
            mute_sound="mute.flac",
            unmute_sound="unmute.flac",
        )
        satellite._pipeline_active = False
        satellite._continue_conversation = False
        satellite._conversation_wake_word_phrase = ""
        satellite._followup_generation = 0
        satellite._is_streaming_audio = False
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

    def test_mute_cancels_streaming_and_allows_next_wake_word(self):
        satellite = self.make_satellite()
        satellite._pipeline_active = True
        satellite._is_streaming_audio = True
        satellite._continue_conversation = True
        satellite._set_muted(True)
        self.assertFalse(satellite._pipeline_active)
        self.assertFalse(satellite._is_streaming_audio)
        self.assertFalse(satellite._continue_conversation)
        requests = [call.args[0][0] for call in satellite.send_messages.call_args_list]
        self.assertTrue(any(isinstance(request, VoiceAssistantRequest) and not request.start for request in requests))
        satellite._set_muted(False)
        satellite.send_messages.reset_mock()
        satellite.wakeup(SimpleNamespace(wake_word="hey_luna"))
        self.assertTrue(satellite._pipeline_active)
        self.assertEqual(satellite.state.tts_player.play.call_args.args[0], "wake.flac")
        satellite.state.tts_player.play.call_args.kwargs["done_callback"]()
        request = satellite.send_messages.call_args.args[0][0]
        self.assertTrue(request.start)
        self.assertEqual(request.wake_word_phrase, "hey_luna")

    def test_mute_invalidates_pending_followup_even_after_unmute(self):
        satellite = self.make_satellite()
        satellite._continue_conversation = True
        with patch("linux_voice_assistant.satellite.threading.Timer") as timer:
            satellite._tts_finished()
            callback = timer.call_args.args[1]
            satellite._set_muted(True)
            satellite._set_muted(False)
            satellite.send_messages.reset_mock()
            callback()
        satellite.send_messages.assert_not_called()
        self.assertFalse(satellite._pipeline_active)

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
