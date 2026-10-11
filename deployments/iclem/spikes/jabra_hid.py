"""Temporary Speak 510 test of LVA Speak 410 HID states; no HA connection.
Run with only the Jabra hidraw device and Pulse audio exposed. Always resets
report 03 to idle on exit. Logs HID packets and audio levels, never stores audio.
"""

import os
import signal
import sys
import time

sys.argv.append("jabra-hid-spike")
import numpy as np
import soundcard as sc


def stop(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, stop)
fd = os.open("/dev/hidraw0", os.O_RDWR | os.O_NONBLOCK)
start = time.monotonic()


def report(value):
    packet = bytes([3, value, 0])
    written = os.write(fd, packet)
    print(f'{time.monotonic()-start:.1f}s WRITE {packet.hex(" ")} bytes={written}', flush=True)


def observe(recorder, seconds):
    deadline = time.monotonic() + seconds
    last = 0
    while time.monotonic() < deadline:
        samples = recorder.record(4096)
        now = time.monotonic() - start
        if now - last >= 1:
            print(f"{now:.1f}s AUDIO rms={np.sqrt(np.mean(samples*samples)):.7f} zeros={np.sum(samples==0)}/{samples.size}", flush=True)
            last = now
        while True:
            try:
                packet = os.read(fd, 4096)
            except BlockingIOError:
                break
            if not packet:
                break
            print(f'{now:.1f}s HID {packet.hex(" ")}', flush=True)


try:
    with sc.default_microphone().recorder(samplerate=16000, channels=1, blocksize=1024) as recorder:
        for name, value, duration in [("idle", 0, 3), ("active call / green", 1, 6), ("active call + mute / red", 5, 10), ("active call: button test", 1, 100)]:
            print("STAGE", name, flush=True)
            report(value)
            observe(recorder, duration)
except KeyboardInterrupt:
    print("Interrupted", flush=True)
finally:
    try:
        report(0)
        print("RESTORED idle", flush=True)
    finally:
        os.close(fd)
