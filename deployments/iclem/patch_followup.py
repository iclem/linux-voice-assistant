"""Preserve assistant selection on automatic follow-ups in LVA 1.1.15."""

from pathlib import Path

source = Path("/app/linux_voice_assistant/satellite.py")
text = source.read_text()
replacements = [
    (
        '        _LOGGER.debug("Detected wake word: %s", wake_word_phrase)\n',
        '        _LOGGER.info("Detected wake word: %s", wake_word_phrase)\n',
    ),
    (
        "        self._tts_url: Optional[str] = None\n",
        "        self._tts_url: Optional[str] = None\n" '        self._conversation_wake_word_phrase = ""\n',
    ),
    (
        "        wake_word_phrase = wake_word.wake_word  # type: ignore[union-attr]\n",
        "        wake_word_phrase = wake_word.wake_word  # type: ignore[union-attr]\n" "        self._conversation_wake_word_phrase = wake_word_phrase\n",
    ),
    (
        '        _LOGGER.debug("Button start_listening triggered")\n',
        '        self._conversation_wake_word_phrase = ""\n' '        _LOGGER.debug("Button start_listening triggered")\n',
    ),
    (
        "            def _start_continued_conversation() -> None:\n",
        "            wake_word_phrase = self._conversation_wake_word_phrase\n\n" "            def _start_continued_conversation() -> None:\n",
    ),
    (
        "                self.send_messages([VoiceAssistantRequest(start=True)])\n",
        "                self.send_messages([VoiceAssistantRequest(\n" "                    start=True, wake_word_phrase=wake_word_phrase\n" "                )])\n",
    ),
    (
        '                _LOGGER.debug("Continued conversation started")\n',
        '                _LOGGER.info("Continued conversation started with wake word: %s", wake_word_phrase)\n',
    ),
]
for old, new in replacements:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one patch location: {old!r}")
    text = text.replace(old, new)
compile(text, str(source), "exec")
source.write_text(text)

# Log the confidence used for a detection without recording microphone audio.
source = Path("/app/linux_voice_assistant/__main__.py")
text = source.read_text()
replacements = [
    (
        "                    for wake_word_index, wake_word in enumerate(wake_words):\n" "                        activated = False\n",
        "                    for wake_word_index, wake_word in enumerate(wake_words):\n" "                        activated = False\n" "                        wake_probability = 0.0\n",
    ),
    (
        "                                if wake_word.process_streaming(micro_input):\n",
        "                                probability = wake_word.process_streaming_prob(micro_input)\n"
        "                                wake_probability = max(wake_probability, probability or 0.0)\n"
        "                                if probability is not None and probability > threshold:\n",
    ),
    (
        "                                state.satellite.wakeup(wake_word)\n",
        "                                if isinstance(wake_word, MicroWakeWord) and not state.satellite._pipeline_active:\n"
        '                                    _LOGGER.info("Wake candidate: %s, confidence=%.3f, threshold=%.3f",\n'
        "                                                 wake_word.wake_word, wake_probability, threshold)\n"
        "                                state.satellite.wakeup(wake_word)\n",
    ),
]
for old, new in replacements:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one patch location: {old!r}")
    text = text.replace(old, new)
compile(text, str(source), "exec")
source.write_text(text)
