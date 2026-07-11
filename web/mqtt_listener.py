"""MQTT listener that runs on the Raspberry Pi.

Subscribes to dorm/display/# and reacts:
  - mode       -> kill current display script and launch the new one
  - brightness -> write to /tmp/led-display-brightness.txt
  - status     -> write to status.txt at the repo root

Run with sudo so the rpi-rgb-led-matrix scripts can access the GPIO.
"""

from __future__ import annotations

import fcntl
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
BRIGHTNESS_FILE = Path("/tmp/led-display-brightness.txt")
DEFAULT_BRIGHTNESS = 60
LOCK_FILE = Path("/tmp/led-listener.lock")

ALLOWED_MODES = {
    "basket",
    "carousel",
    "fireplace",
    "github_contributions",
    "hello",
    "jaylen",
    "justin",
    "justinwu",
    "matthew",
    "pixel",
    "rainbow",
    "shapes",
    "spotify",
    "weather",
}

PYTHON_BIN = sys.executable or "python3"

_current_proc: subprocess.Popen | None = None
_current_mode: str = "off"
_last_non_off_mode: str | None = None
_restore_on_brightness: bool = False
_instance_lock = None


def acquire_instance_lock():
    global _instance_lock
    lock_file = LOCK_FILE.open("w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("[listener] already running; exiting", file=sys.stderr)
        sys.exit(1)
    lock_file.write(str(os.getpid()))
    lock_file.flush()
    _instance_lock = lock_file


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


def read_brightness() -> int:
    try:
        value = int(BRIGHTNESS_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        value = DEFAULT_BRIGHTNESS
    return max(0, min(100, value))


def launch_mode(mode: str):
    global _current_proc, _current_mode, _last_non_off_mode, _restore_on_brightness
    stop_current()
    if mode == "off":
        _current_mode = "off"
        _restore_on_brightness = False
        print("[listener] display off")
        return

    brightness = read_brightness()
    _last_non_off_mode = mode
    if brightness == 0:
        _current_mode = "off"
        _restore_on_brightness = True
        print(f"[listener] brightness is 0, keeping {mode} off")
        return

    script = SCRIPTS_DIR / f"{mode}.py"
    if not script.exists():
        print(f"[listener] script not found: {script}")
        return
    env = os.environ.copy()
    env["LED_BRIGHTNESS"] = str(brightness)
    env["LED_BRIGHTNESS_FILE"] = str(BRIGHTNESS_FILE)
    print(f"[listener] launching {script}")
    _current_proc = subprocess.Popen(
        [PYTHON_BIN, str(script)],
        cwd=str(REPO_ROOT),
        env=env,
        start_new_session=True,
    )
    _current_mode = mode
    _restore_on_brightness = False


def write_brightness(value: str):
    global _current_mode, _restore_on_brightness
    try:
        n = int(value)
    except ValueError:
        print(f"[listener] bad brightness: {value!r}")
        return
    n = max(0, min(100, n))
    BRIGHTNESS_FILE.write_text(str(n))
    try:
        BRIGHTNESS_FILE.chmod(0o666)
    except OSError as exc:
        print(f"[listener] could not update brightness file permissions: {exc}")
    print(f"[listener] brightness -> {n}")
    if n == 0:
        if _current_mode != "off":
            stop_current()
            _current_mode = "off"
            _restore_on_brightness = True
            print("[listener] display off")
    elif _current_mode == "off" and _restore_on_brightness and _last_non_off_mode:
        launch_mode(_last_non_off_mode)


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
    acquire_instance_lock()
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
