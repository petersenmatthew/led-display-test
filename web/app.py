"""Flask control panel for the LED matrix.

Publishes user actions to a local Mosquitto broker on localhost:1883.
The companion mqtt_listener.py runs on the Pi and acts on the messages.
"""

from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt

MQTT_HOST = "localhost"
MQTT_PORT = 1883

TOPIC_MODE = "dorm/display/mode"
TOPIC_BRIGHTNESS = "dorm/display/brightness"
TOPIC_STATUS = "dorm/display/status"

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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/mode", methods=["POST"])
def set_mode():
    data = request.get_json(silent=True) or request.form
    mode = (data.get("mode") or "").strip().lower()
    if mode not in ALLOWED_MODES:
        return jsonify(ok=False, error=f"unknown mode: {mode}"), 400
    ok = publish(TOPIC_MODE, mode)
    return jsonify(ok=ok, mode=mode)


@app.route("/brightness", methods=["POST"])
def set_brightness():
    data = request.get_json(silent=True) or request.form
    try:
        value = int(data.get("value"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="value must be an integer 0-100"), 400
    if not 0 <= value <= 100:
        return jsonify(ok=False, error="value must be 0-100"), 400
    ok = publish(TOPIC_BRIGHTNESS, str(value))
    return jsonify(ok=ok, value=value)


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
