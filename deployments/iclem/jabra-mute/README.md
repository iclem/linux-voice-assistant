# Jabra Speak 510 mute controller

Deployed as `ha-jabra-mute` alongside `ha-jabra-satellite` in the parent compose
file. No audio recording or inference is used by the controller.

## Behavior

- Satellite snapshots and `muted` events set hardware mute via HID report
  `03 05 00` (active call + mute), `03 09 00` (active call + ring /
  flashing green while listening), or `03 01 00` (solid green otherwise).
- Active-call mode keeps mute-button reporting available. Idle is solid green;
  wake-word detection and listening flash green. Recognized speech, thinking,
  speaking, completion, errors and disconnection return to solid green.
  Hardware mute always takes priority and stays red.
- The mute button sends relative bit `0x10` in report 3. Each rising pulse
  toggles state and sends satellite `mute_mic` or `unmute_mic`; the satellite
  updates Home Assistant's existing mute switch and plays its normal sound.
- Idle, pipeline and playback events do not change microphone mute.
- Satellite connection loss preserves hardware mute. Physical presses made
  while disconnected are retained and sent when the connection returns.
- Stopping the controller preserves mute if currently muted, or restores idle
  if unmuted. It does not unmute a microphone during shutdown.

## Deployment

The satellite peripheral API is enabled only on `127.0.0.1:6055`.
The controller reuses the satellite image's Python/websockets runtime, mounts
only its source and the Jabra hidraw device, uses a read-only filesystem, and
has all Linux capabilities dropped. Root is used to access the root-only
hidraw device. Its startup verifies USB ID 0b0e:0422 and device serial.
Both the controller and satellite use restart: unless-stopped, so they
start after a host reboot unless explicitly stopped beforehand.

Run from `deployments/iclem`:

```
docker compose up -d --no-build
docker compose logs -f jabra-mute
python -m unittest discover -s jabra-mute -v
```

USB unplug/replug may require recreating the controller because Docker device
mounts refer to the original node. If the hidraw number changes, update the
compose device mapping and JABRA_HID_PATH. The identity check prevents commands
from being sent to another device by mistake.

## Verification (2026-10-11)

- Six unit tests cover 510 button decoding, duplicate press suppression,
  unrelated events, reconnection state, output reports, shutdown, listening
  transitions and mute priority.
- Live satellite command test: unmuted audio had nonzero levels; mute produced
  16,000/16,000 zero samples; unmute restored nonzero audio. Initial state was
  restored after the test.
- User's two touch-button presses at 13:28:46 and 13:28:51 UTC generated
  `03 13 00`, sent mute/unmute to the satellite, and produced its mute sound.
- Final satellite snapshot: muted=false, ha_connected=true.

The 410's peripheral approach was adapted for the 510. Its bit 0x08 decoder
and all-zero audio fallback were not copied; the 510 uses bit 0x10.
