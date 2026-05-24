"""MQTT listener that runs on the Raspberry Pi.

Subscribes to dorm/display/# and reacts:
  - mode       -> kill current display script and launch the new one
  - brightness -> write to web/brightness.txt (a shared config file)
  - status     -> write to status.txt at the repo root

Run with sudo so the rpi-rgb-led-matrix scripts can access the GPIO.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

import paho.mqtt.client as mqtt

MQTT_HOST = "localhost"
MQTT_PORT = 1883
TOPIC_ROOT = "dorm/display/#"

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
STATUS_FILE = REPO_ROOT / "status.txt"
BRIGHTNESS_FILE = Path(__file__).resolve().parent / "brightness.txt"

ALLOWED_MODES = {
    "basket",
    "carousel",
    "hello",
    "jaylen",
    "justin",
    "justinwu",
    "matthew",
    "pixel",
    "rainbow",
    "shapes",
    "weather",
}

PYTHON_BIN = sys.executable or "python3"

_current_proc: subprocess.Popen | None = None


def stop_current():
    global _current_proc
    if _current_proc is None:
        return
    if _current_proc.poll() is None:
        try:
            os.killpg(os.getpgid(_current_proc.pid), signal.SIGTERM)
            _current_proc.wait(timeout=3)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(os.getpgid(_current_proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
    _current_proc = None


def launch_mode(mode: str):
    global _current_proc
    stop_current()
    if mode == "off":
        print("[listener] display off")
        return
    script = SCRIPTS_DIR / f"{mode}.py"
    if not script.exists():
        print(f"[listener] script not found: {script}")
        return
    env = os.environ.copy()
    try:
        env["LED_BRIGHTNESS"] = BRIGHTNESS_FILE.read_text().strip()
    except FileNotFoundError:
        pass
    print(f"[listener] launching {script}")
    _current_proc = subprocess.Popen(
        [PYTHON_BIN, str(script)],
        cwd=str(REPO_ROOT),
        env=env,
        start_new_session=True,
    )


def write_brightness(value: str):
    try:
        n = int(value)
    except ValueError:
        print(f"[listener] bad brightness: {value!r}")
        return
    n = max(0, min(100, n))
    BRIGHTNESS_FILE.write_text(str(n))
    print(f"[listener] brightness -> {n}")


def write_status(text: str):
    STATUS_FILE.write_text(text)
    print(f"[listener] status -> {text!r}")


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[listener] connected ({reason_code}), subscribing to {TOPIC_ROOT}")
    client.subscribe(TOPIC_ROOT, qos=1)


def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode("utf-8", errors="replace").strip()
    print(f"[listener] {topic} = {payload!r}")
    if topic.endswith("/mode"):
        mode = payload.lower()
        if mode in ALLOWED_MODES or mode == "off":
            launch_mode(mode)
        else:
            print(f"[listener] ignoring unknown mode: {mode}")
    elif topic.endswith("/brightness"):
        write_brightness(payload)
    elif topic.endswith("/status"):
        write_status(payload)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="led-listener")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[listener] shutting down")
    finally:
        stop_current()
        client.disconnect()


if __name__ == "__main__":
    main()
