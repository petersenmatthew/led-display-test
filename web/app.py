"""Flask control panel for the LED matrix.

Publishes user actions to a local Mosquitto broker on localhost:1883.
The companion mqtt_listener.py runs on the Pi and acts on the messages.
"""

from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
import paho.mqtt.client as mqtt

MQTT_HOST = "localhost"
MQTT_PORT = 1883

REPO_ROOT = Path(__file__).resolve().parent.parent

TOPIC_MODE = "dorm/display/mode"
TOPIC_BRIGHTNESS = "dorm/display/brightness"
TOPIC_STATUS = "dorm/display/status"
BRIGHTNESS_FILE = Path(__file__).resolve().parent / "brightness.txt"
DEFAULT_BRIGHTNESS = 60

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
    "off",
}

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
        return True
    except OSError as exc:
        app.logger.warning("Could not write brightness cache %s: %s", BRIGHTNESS_FILE, exc)
        return False


@app.route("/")
def index():
    return render_template("index.html", initial_brightness=read_brightness())


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
