"""MQTT listener that runs on the Raspberry Pi.

Subscribes to dorm/display/# and reacts:
  - mode       -> kill current display script and launch the new one
  - brightness -> write to /tmp/led-display-brightness.txt
  - schedule   -> nightly downtime window (display forced off while asleep)
  - status     -> write to status.txt at the repo root

Run with sudo so the rpi-rgb-led-matrix scripts can access the GPIO.
"""

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt

MQTT_HOST = "localhost"
MQTT_PORT = 1883
TOPIC_ROOT = "dorm/display/#"

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
STATUS_FILE = REPO_ROOT / "status.txt"
SCHEDULE_FILE = REPO_ROOT / "schedule.json"
BRIGHTNESS_FILE = Path("/tmp/led-display-brightness.txt")
DEFAULT_BRIGHTNESS = 60
LOCK_FILE = Path("/tmp/led-listener.lock")
SCHEDULE_TICK_SECONDS = 15

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

_schedule: dict = {"enabled": False, "start": "23:00", "end": "07:00"}
_downtime_active: bool = False
_resume_after_downtime: bool = False

# MQTT callbacks run on the network thread while the schedule ticks on the main
# thread; both start and stop display processes, so serialise them.
_state_lock = threading.Lock()


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


def parse_hhmm(value) -> int | None:
    """"23:30" -> 1410 minutes past midnight. None if unparseable."""
    try:
        hours, minutes = str(value).strip().split(":")
        hours, minutes = int(hours), int(minutes)
    except (AttributeError, ValueError):
        return None
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    return hours * 60 + minutes


def in_downtime(now: datetime | None = None) -> bool:
    """True when local wall-clock time falls inside the downtime window.

    Windows that wrap past midnight (start > end, e.g. 23:00 -> 07:00) are the
    normal case, so both orderings are handled.
    """
    if not _schedule.get("enabled"):
        return False
    start = parse_hhmm(_schedule.get("start"))
    end = parse_hhmm(_schedule.get("end"))
    if start is None or end is None or start == end:
        return False
    now = now or datetime.now()
    minute_of_day = now.hour * 60 + now.minute
    if start < end:
        return start <= minute_of_day < end
    return minute_of_day >= start or minute_of_day < end


def load_schedule():
    global _schedule
    try:
        data = json.loads(SCHEDULE_FILE.read_text())
    except (OSError, ValueError):
        return
    apply_schedule_settings(data, source="disk")


def apply_schedule_settings(data, source: str = "mqtt"):
    global _schedule
    if not isinstance(data, dict):
        print(f"[listener] bad schedule payload from {source}: {data!r}")
        return
    start = data.get("start", _schedule["start"])
    end = data.get("end", _schedule["end"])
    if parse_hhmm(start) is None or parse_hhmm(end) is None:
        print(f"[listener] bad schedule times from {source}: {start!r} -> {end!r}")
        return
    _schedule = {"enabled": bool(data.get("enabled")), "start": start, "end": end}
    state = "on" if _schedule["enabled"] else "off"
    print(f"[listener] schedule ({source}) {state}: {_schedule['start']} -> {_schedule['end']}")
    apply_schedule()


def apply_schedule():
    """Force the display off inside the window, restore it on the way out."""
    global _current_mode, _downtime_active, _resume_after_downtime
    active = in_downtime()
    if active == _downtime_active:
        return
    _downtime_active = active
    if active:
        # Remember whether anything was actually showing, so an intentional
        # "off" isn't woken back up at the end of the window.
        _resume_after_downtime = _current_mode != "off" or _restore_on_brightness
        stop_current()
        _current_mode = "off"
        print(f"[listener] downtime started ({_schedule['start']} -> {_schedule['end']}), display off")
    else:
        print("[listener] downtime ended")
        if _resume_after_downtime and _last_non_off_mode:
            launch_mode(_last_non_off_mode)
        _resume_after_downtime = False


def launch_mode(mode: str):
    global _current_proc, _current_mode, _last_non_off_mode, _restore_on_brightness
    global _resume_after_downtime
    stop_current()
    if mode == "off":
        _current_mode = "off"
        _restore_on_brightness = False
        _resume_after_downtime = False
        print("[listener] display off")
        return

    brightness = read_brightness()
    _last_non_off_mode = mode
    if _downtime_active:
        # Picking a mode mid-downtime queues it for when the window ends.
        _current_mode = "off"
        _resume_after_downtime = True
        print(f"[listener] downtime active, holding {mode}")
        return

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
    with _state_lock:
        if topic.endswith("/mode"):
            mode = payload.lower()
            if mode in ALLOWED_MODES or mode == "off":
                launch_mode(mode)
            else:
                print(f"[listener] ignoring unknown mode: {mode}")
        elif topic.endswith("/brightness"):
            write_brightness(payload)
        elif topic.endswith("/schedule"):
            try:
                apply_schedule_settings(json.loads(payload))
            except ValueError:
                print(f"[listener] bad schedule JSON: {payload!r}")
        elif topic.endswith("/status"):
            write_status(payload)


def main():
    acquire_instance_lock()
    load_schedule()
    apply_schedule()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="led-listener")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    try:
        while True:
            with _state_lock:
                apply_schedule()
            time.sleep(SCHEDULE_TICK_SECONDS)
    except KeyboardInterrupt:
        print("\n[listener] shutting down")
    finally:
        stop_current()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
