# Jabra Speak 510 HID spike

Tested 2026-10-11 on USB 0b0e:0422, serial [device serial omitted].
The script runs independently of LVA and does not change its configuration.

## Results

- Report `03 01 00` (off-hook / active call) enables the green indication;
  user confirmed seeing three green LEDs after the first run. Audio continues.
- Report `03 05 00` (off-hook + mute) silences microphone audio: repeated
  4096-sample blocks contained only zeros. The same report is the red LED
  state in the upstream 410 controller; physical red color was not explicitly
  confirmed by the user in this spike.
- Returning to `03 01 00` restores nonzero microphone audio.
- In active-call state, each physical mute press emitted `03 13 00`, then
  `03 03 00`. First press silenced audio, second restored it.
- The device descriptor assigns Phone Mute to input bit 4 (`0x10`), a relative
  pulse. The upstream 410 script uses input bit 3 (`0x08`); copying its decoder
  would miss mute presses on this 510 (and interpret them as flash).
- `03 00 00` is sent in finally on normal exit or SIGTERM to restore idle.
  Both stopped runs logged successful restoration. ALSA capture remains on.

## Potential integration

Adapt the 410 peripheral controller for 510 decoding. Track mute toggles from
`0x10` rising pulses. Send satellite `mute_mic` / `unmute_mic` through its
peripheral WebSocket and reflect satellite mute as HID `03 05 00`. Keep
active-call state while button reporting is needed. Test satellite startup,
unmute, reconnect and LED policy before making this persistent. Avoid treating
an isolated all-zero audio block as a mute event: earlier idle recording had
intermittent zeros without a confirmed button press.

Upstream reference:
https://github.com/OHF-Voice/linux-voice-assistant/blob/main/examples/Jabra%20Speak%20410/main.py

The spike stores no audio, only USB packets and numeric audio levels.

## LED pattern spike (2026-10-11)

The permanent mute controller was paused during these tests, then restarted.
Satellite mute was false before testing and remained false afterward.

- `03 09 00` (off-hook + ring): user confirmed flashing green; pressing mute
  gave red, then unmute returned to flashing green. Both presses emitted
  `03 13 00`, then `03 03 00`. Audio became all-zero while muted and returned
  after unmute. This is a usable listening indication while keeping buttons.
- `03 11 00` (off-hook + hold): user reported green still; no distinct visual
  indication was confirmed. Both button presses were received; audio briefly
  became all-zero while muted and recovered on unmute.
- `jabra_patterns.py` accepts PATTERN_NAME/PATTERN_VALUE, runs for at most
  90 seconds, and restores active-call/unmuted in finally. Use only from an
  unmuted state; stop the permanent controller before testing and restart it
  afterward. It does not send satellite commands or save audio.

Suggested future policy: solid green idle, flashing green listening, red mute.
The permanent controller still uses its original solid-green/red policy.
