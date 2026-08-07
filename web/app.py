"""Flask control panel for the LED matrix.

Publishes user actions to a local Mosquitto broker on localhost:1883.
The companion mqtt_listener.py runs on the Pi and acts on the messages.
"""

import fcntl
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
import paho.mqtt.client as mqtt

MQTT_HOST = "localhost"
MQTT_PORT = 1883

REPO_ROOT = Path(__file__).resolve().parent.parent

TOPIC_MODE = "dorm/display/mode"
TOPIC_BRIGHTNESS = "dorm/display/brightness"
TOPIC_SCHEDULE = "dorm/display/schedule"
TOPIC_STATUS = "dorm/display/status"
BRIGHTNESS_FILE = Path("/tmp/led-display-brightness.txt")
DEFAULT_BRIGHTNESS = 60
SCHEDULE_FILE = REPO_ROOT / "schedule.json"
DEFAULT_SCHEDULE = {"enabled": False, "start": "23:00", "end": "07:00"}
LOCK_FILE = Path("/tmp/led-web.lock")

_instance_lock = None

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
    "off",
}


def acquire_instance_lock():
    global _instance_lock
    lock_file = LOCK_FILE.open("w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("[led-web] already running; exiting", file=sys.stderr)
        sys.exit(1)
    lock_file.write(str(os.getpid()))
    lock_file.flush()
    _instance_lock = lock_file


acquire_instance_lock()

app = Flask(__name__)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="led-web")
client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=30)
client.loop_start()


def publish(topic, payload, retain=True):
    info = client.publish(topic, payload, qos=1, retain=retain)
    return info.rc == mqtt.MQTT_ERR_SUCCESS


def clamp_brightness(value, default=DEFAULT_BRIGHTNESS):
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        n = default
    return max(0, min(100, n))


def read_brightness():
    try:
        return clamp_brightness(BRIGHTNESS_FILE.read_text())
    except OSError:
        return DEFAULT_BRIGHTNESS


def write_brightness(value):
    try:
        BRIGHTNESS_FILE.write_text(str(clamp_brightness(value)))
        BRIGHTNESS_FILE.chmod(0o666)
        return True
    except OSError as exc:
        app.logger.warning("Could not write brightness cache %s: %s", BRIGHTNESS_FILE, exc)
        return False


def parse_hhmm(value):
    """"23:30" -> 1410 minutes past midnight. None if unparseable."""
    try:
        hours, minutes = str(value).strip().split(":")
        hours, minutes = int(hours), int(minutes)
    except (AttributeError, ValueError):
        return None
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    return hours * 60 + minutes


def read_schedule():
    try:
        data = json.loads(SCHEDULE_FILE.read_text())
    except (OSError, ValueError):
        return dict(DEFAULT_SCHEDULE)
    if not isinstance(data, dict):
        return dict(DEFAULT_SCHEDULE)
    start = data.get("start", DEFAULT_SCHEDULE["start"])
    end = data.get("end", DEFAULT_SCHEDULE["end"])
    if parse_hhmm(start) is None or parse_hhmm(end) is None:
        return dict(DEFAULT_SCHEDULE)
    return {"enabled": bool(data.get("enabled")), "start": start, "end": end}


def write_schedule(schedule):
    try:
        SCHEDULE_FILE.write_text(json.dumps(schedule))
        return True
    except OSError as exc:
        app.logger.warning("Could not write schedule %s: %s", SCHEDULE_FILE, exc)
        return False


def in_downtime(schedule, now=None):
    """True when local time is inside the window. Windows may wrap midnight."""
    if not schedule.get("enabled"):
        return False
    start = parse_hhmm(schedule.get("start"))
    end = parse_hhmm(schedule.get("end"))
    if start is None or end is None or start == end:
        return False
    now = now or datetime.now()
    minute_of_day = now.hour * 60 + now.minute
    if start < end:
        return start <= minute_of_day < end
    return minute_of_day >= start or minute_of_day < end


@app.route("/")
def index():
    schedule = read_schedule()
    return render_template(
        "index.html",
        initial_brightness=read_brightness(),
        schedule=schedule,
        downtime_now=in_downtime(schedule),
    )


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/worker.js")
def worker():
    return send_from_directory(REPO_ROOT, "worker.js")


@app.route("/scripts/<path:filename>")
def scripts(filename):
    return send_from_directory(REPO_ROOT / "scripts", filename)


@app.route("/fonts/<path:filename>")
def fonts(filename):
    return send_from_directory(REPO_ROOT / "fonts", filename)


@app.route("/mode", methods=["POST"])
def set_mode():
    data = request.get_json(silent=True) or request.form
    mode = (data.get("mode") or "").strip().lower()
    if mode not in ALLOWED_MODES:
        return jsonify(ok=False, error=f"unknown mode: {mode}"), 400
    ok = publish(TOPIC_MODE, mode)
    return jsonify(ok=ok, mode=mode)


@app.route("/brightness", methods=["GET", "POST"])
def set_brightness():
    if request.method == "GET":
        return jsonify(ok=True, value=read_brightness())

    data = request.get_json(silent=True) or request.form
    try:
        value = int(data.get("value"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="value must be an integer 0-100"), 400
    if not 0 <= value <= 100:
        return jsonify(ok=False, error="value must be 0-100"), 400
    ok = publish(TOPIC_BRIGHTNESS, str(value))
    cached = False
    if ok:
        cached = write_brightness(value)
    return jsonify(ok=ok, value=value, cached=cached)


@app.route("/schedule", methods=["GET", "POST"])
def set_schedule():
    if request.method == "GET":
        schedule = read_schedule()
        return jsonify(ok=True, schedule=schedule, active=in_downtime(schedule))

    data = request.get_json(silent=True) or request.form
    current = read_schedule()
    start = (data.get("start") or current["start"]).strip()
    end = (data.get("end") or current["end"]).strip()
    if parse_hhmm(start) is None or parse_hhmm(end) is None:
        return jsonify(ok=False, error="times must be HH:MM (24-hour)"), 400
    if start == end:
        return jsonify(ok=False, error="start and end must differ"), 400

    enabled = data.get("enabled", current["enabled"])
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() in {"1", "true", "on", "yes"}
    schedule = {"enabled": bool(enabled), "start": start, "end": end}

    ok = publish(TOPIC_SCHEDULE, json.dumps(schedule))
    saved = False
    if ok:
        saved = write_schedule(schedule)
    return jsonify(ok=ok, schedule=schedule, saved=saved, active=in_downtime(schedule))


@app.route("/status", methods=["POST"])
def set_status():
    data = request.get_json(silent=True) or request.form
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify(ok=False, error="text is required"), 400
    ok = publish(TOPIC_STATUS, text)
    return jsonify(ok=ok, text=text)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
