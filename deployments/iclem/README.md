# Local Jabra satellite setup

This branch stores the tested deployment overlay for Linux Voice Assistant
1.1.15, built from the pinned upstream container digest in Dockerfile. Upstream
application source is unchanged; patch_followup.py applies the follow-up
assistant routing fix and wake-word confidence logging during the image build.

## Contents

- compose.yaml: satellite and Jabra Speak 510 peripheral controller.
- jabra-mute/: bidirectional hardware mute and LED state controller, with tests.
- patch_followup.py and test_followup.py: assistant routing fix and regression tests.
- spikes/: USB test scripts and results used to verify the 510 behavior.

LED policy: solid green idle/thinking/speaking, flashing green while listening
(including follow-ups), red while muted. Mute always takes priority.

## Local configuration

Copy .env.example to .env and supply the host network address, network
interface and Jabra serial. The serial is available from the device's sysfs
uevent file. Runtime configuration, custom models and audio are in data/.
Both data/ and .env are ignored; they must be backed up separately.

```
cp .env.example .env
# Edit .env locally and provision data/ for the satellite.
docker compose up -d --build
python -m unittest discover -s jabra-mute -v
docker exec -i ha-jabra-satellite /app/.venv/bin/python - < test_followup.py
```

The follow-up tests must run against the patched 1.1.15 image, not the fork's
newer upstream main source. See jabra-mute/README.md for device permissions,
USB reconnect behavior and hardware verification details.

On the existing host the previous deployment path is a symlink to this
version-controlled directory. Runtime data stays local and is not published.

## Publication scope

Only source, tests, deployment templates and documentation are committed.
No HA tokens, API keys, runtime preferences, model binaries, recorded audio,
conversation logs, local environment values or device serials are included.
