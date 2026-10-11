"""Synchronize Speak 510 hardware mute with Linux Voice Assistant."""

import asyncio
import json
import logging
import os
import signal
from pathlib import Path

LOG = logging.getLogger("jabra-mute")


class MuteState:
    def __init__(self):
        self.muted = None
        self.pending = None
        self.button_down = False
        self.listening = False

    def button(self, packet):
        # The 510 descriptor assigns relative Phone Mute to bit 4 of report 3.
        # Vendor report 4 is ignored to avoid counting the same press twice.
        if len(packet) < 3 or packet[0] != 3:
            return False
        down = bool(packet[1] & 0x10)
        pressed = down and not self.button_down
        self.button_down = down
        if pressed:
            self.muted = not bool(self.muted)
            self.pending = self.muted
        return pressed

    def event(self, message):
        event, data = message.get("event"), message.get("data") or {}
        if event in ("wake_word_detected", "listening"):
            changed = not self.listening
            self.listening = True
            return changed
        if event in ("idle", "stt_text", "thinking", "tts_text", "tts_speaking", "tts_finished", "pipeline_error", "disconnected"):
            changed = self.listening
            self.listening = False
            return changed
        if event not in ("snapshot", "muted") or "muted" not in data:
            return False
        # Keep an offline physical press until the server acknowledges it.
        if self.pending is not None and bool(data["muted"]) != self.pending:
            return False
        self.muted = bool(data["muted"])
        self.pending = None
        self.listening = False
        return True


class Controller:
    def __init__(self, fd):
        self.fd = fd
        self.state = MuteState()
        self.ws = None
        self.last_output = None

    def apply(self, force=False):
        if self.state.muted is None:
            return
        value = 5 if self.state.muted else (9 if self.state.listening else 1)
        if force or value != self.last_output:
            packet = bytes([3, value, 0])
            if os.write(self.fd, packet) != len(packet):
                raise OSError("Incomplete HID write")
            self.last_output = value
            LOG.info("Hardware mute=%s listening=%s (HID %s)", self.state.muted, self.state.listening, packet.hex(" "))

    async def send_pending(self):
        if self.ws is None or self.state.pending is None:
            return
        command = "mute_mic" if self.state.pending else "unmute_mic"
        try:
            await self.ws.send(json.dumps({"command": command}))
            LOG.info("Sent satellite %s", command)
        except Exception as exc:
            LOG.warning("Mute command awaiting reconnection: %s", exc)

    async def buttons(self):
        while True:
            try:
                packet = os.read(self.fd, 64)
            except BlockingIOError:
                await asyncio.sleep(0.05)
                continue
            if not packet:
                raise OSError("Jabra HID device disconnected")
            if self.state.button(packet):
                LOG.info("Physical mute press: %s", packet.hex(" "))
                self.apply()
                await self.send_pending()

    async def satellite(self):
        from websockets.client import connect

        url = os.environ.get("LVA_WS_URL", "ws://127.0.0.1:6055")
        while True:
            try:
                async with connect(url, open_timeout=5) as ws:
                    # Snapshot comes first; wait for it before applying hardware state.
                    message = json.loads(await asyncio.wait_for(ws.recv(), 5))
                    if message.get("event") != "snapshot":
                        raise ValueError("Missing satellite snapshot")
                    self.ws = ws
                    self.state.event(message)
                    self.apply(force=True)
                    await self.send_pending()
                    LOG.info("Connected to satellite; mute=%s", self.state.muted)
                    async for raw in ws:
                        if self.state.event(json.loads(raw)):
                            self.apply()
            except (OSError, TimeoutError, ValueError) as exc:
                LOG.warning("Satellite unavailable; retaining hardware state: %s", exc)
            except Exception as exc:
                LOG.warning("Satellite connection ended; retaining hardware state: %s", exc)
            finally:
                self.ws = None
                self.state.listening = False
                self.apply()
            await asyncio.sleep(2)

    def shutdown(self):
        # Never unmute a muted microphone just because the controller stops.
        if self.state.muted is False:
            os.write(self.fd, bytes([3, 0, 0]))
            LOG.info("Restored idle; microphone remains unmuted")
        else:
            LOG.info("Leaving hardware mute state intact")


async def main():
    path = os.environ.get("JABRA_HID_PATH", "/dev/hidraw0")
    info = Path("/sys/class/hidraw/" + Path(path).name + "/device/uevent").read_text()
    serial = os.environ["JABRA_SERIAL"]
    if "HID_ID=0003:00000B0E:00000422" not in info or ("HID_UNIQ=" + serial + "\n") not in info:
        raise RuntimeError("HID path does not match the configured Jabra Speak 510")
    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    controller = Controller(fd)
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stopped.set)
    tasks = [asyncio.create_task(controller.buttons()), asyncio.create_task(controller.satellite()), asyncio.create_task(stopped.wait())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            controller.shutdown()
        finally:
            os.close(fd)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
