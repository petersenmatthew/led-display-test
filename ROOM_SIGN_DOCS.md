# Room Sign System — Full Technical Reference

> A modular Raspberry Pi smart room sign with LED matrix display, live weather,
> class schedule, voice input, Claude AI responses, a web remote control, and a
> plug-in architecture designed for unlimited hardware expansion.
>
> Built by Justin & Matthew · Waterloo, ON

---

## Table of contents

1. [System overview](#1-system-overview)
2. [Hardware list](#2-hardware-list)
3. [Breadboard guidance](#3-breadboard-guidance)
4. [Folder structure](#4-folder-structure)
5. [Raspberry Pi OS setup](#5-raspberry-pi-os-setup)
6. [Wiring the LED matrix](#6-wiring-the-led-matrix)
7. [Core state bus](#7-core-state-bus)
8. [Input modules](#8-input-modules)
9. [Output modules](#9-output-modules)
10. [Voice + Claude pipeline](#10-voice--claude-pipeline)
11. [Web remote control](#11-web-remote-control)
12. [Main entry point](#12-main-entry-point)
13. [Schedule data format](#13-schedule-data-format)
14. [Multi-Pi sync](#14-multi-pi-sync)
15. [Adding new devices](#15-adding-new-devices)
16. [Future expansion modules](#16-future-expansion-modules)
17. [Auto-start on boot](#17-auto-start-on-boot)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. System overview

### Architecture

The Raspberry Pi is the central brain. Every device is a self-contained module
that reads from or writes to one shared state dictionary. Modules never talk to
each other directly — only through state.

```
 INPUTS                     CORE                      OUTPUTS
 ──────                  ──────────                   ───────
 Microphone   ──write──▶                  ──read──▶  LED matrix
 Weather API  ──write──▶  shared_state    ──read──▶  Speaker / TTS
 Schedule     ──write──▶  (state.py)      ──read──▶  HDMI monitor
 Web remote   ──write──▶                  ──read──▶  Receipt printer
 Thermal cam  ──write──▶                  ──read──▶  2nd LED sign
 Door sensor  ──write──▶
```

**The one rule:** no module imports another module. They only import `state`.
Adding a new device = write one new file + two lines in `main.py`. Zero changes
to anything else.

### Technology stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3 | Best library support for all hardware |
| LED driver | hzeller/rpi-rgb-led-matrix | Standard for HUB75 panels on Pi |
| Image drawing | Pillow (PIL) | Draw text/shapes onto the 64×32 canvas |
| Speech-to-text | OpenAI Whisper (local) | Runs entirely on Pi, no internet needed |
| AI responses | Anthropic Claude API | claude-sonnet-4-20250514 |
| Weather data | OpenWeatherMap API | Free tier, 1000 calls/day |
| Web server | Flask + Flask-SocketIO | Serves remote UI + real-time WebSocket |
| Real-time sync | WebSocket (Socket.IO) | Pi pushes state to browser instantly |

### How Python draws to the LED panel

```
1. Create blank 64×32 RGB image in memory   (Pillow: Image.new)
2. Draw text and colors onto it              (Pillow: ImageDraw)
3. Push image to LED hardware               (matrix.SetImage(img))
4. Repeat ~10x per second
```

### Display layout (64×32 pixels)

```
+------------------------------------------------+  y=0
|  18C Clouds          Hi J+M!                   |  row 1: weather + welcome
|  NOW  CS 246                                   |  row 2: current class
|  NXT  MATH 237                                 |  row 3: next class
|  Listening... / Claude reply scrolls here      |  row 4: voice/AI status
+------------------------------------------------+  y=31
  x=0                                          x=63
```

Each character in the default font is 6px wide x 8px tall. Row y positions:
`0, 9, 17, 25` — spaced 8-9px apart to avoid overlap.

---

## 2. Hardware list

### Phase 1 — build now

| Item | Notes | Cost |
|---|---|---|
| Raspberry Pi 4 (2GB+) | The main computer | ~$55 |
| microSD card 32GB+ | Stores OS and code | ~$10 |
| Official Pi 5V 3A USB-C power supply | Do not cheap out here | ~$10 |
| Waveshare 64x32 RGB LED matrix (HUB75) | The display panel | ~$25 |
| Adafruit RGB Matrix Bonnet | Cleanest HUB75 to Pi connection | ~$15 |
| 5V 4A barrel power supply | Powers LED panel — NOT from Pi USB | ~$10 |
| USB microphone | Any plug-and-play USB mic | ~$10 |
| USB speaker or 3.5mm speaker | For TTS audio output | ~$10 |
| Powered USB hub | If you need more than 4 USB ports | ~$15 |
| Jumper wires (male-female) | For GPIO connections | ~$5 |

### Phase 2 — future hardware

| Item | Connection | Notes |
|---|---|---|
| MLX90640 thermal camera | I2C to 4 GPIO pins | Person detection, occupancy |
| Pi Camera Module 3 | CSI ribbon cable | Outfit detection with Claude vision |
| Thermal receipt printer (Adafruit Mini) | USB serial /dev/ttyUSB0 | Schedule printouts |
| Reed switch or PIR sensor | 2-3 GPIO pins + resistor | Bathroom / door occupancy |
| 2nd LED matrix (same model) | HUB75 daisy-chain ribbon | Change chain_length=2, cols=128 |
| HDMI TV or monitor | Micro HDMI (already on Pi 4) | Full dashboard via Pygame or browser |
| Satellite Raspberry Pi | WiFi / LAN | Remote room display (see section 14) |

---

## 3. Breadboard guidance

Most devices plug in directly. You almost never need a breadboard.

| Device | Needs breadboard? |
|---|---|
| LED matrix | No — HUB75 ribbon cable to Bonnet |
| USB microphone | No — USB plug-and-play |
| Speaker | No — USB or 3.5mm jack |
| HDMI monitor | No — Micro HDMI port |
| Receipt printer | No — USB serial |
| Pi Camera Module | No — CSI ribbon cable |
| Thermal camera (MLX90640) | Mini 170-tie board helpful while prototyping |
| PIR / reed switch sensor | Mini 170-tie board helpful while prototyping |

**Size recommendation:** a mini 170-tie breadboard (~$3) is sufficient for the
two cases above. Once the wiring is confirmed, solder it to perfboard and
retire the breadboard.

---

## 4. Folder structure

```
room_sign/
|
+-- main.py                    <- boots every module; only file that imports modules
+-- schedule.json              <- class timetable (edit manually or sync script)
+-- requirements.txt           <- pip dependencies
|
+-- core/
|   +-- state.py               <- shared state bus (thread-safe dict)
|
+-- inputs/                    <- modules that WRITE to state
|   +-- weather_module.py
|   +-- schedule_module.py
|   +-- voice_module.py
|   +-- thermal_module.py      <- (future) thermal camera
|   +-- sensor_module.py       <- (future) door / PIR sensor
|   +-- camera_module.py       <- (future) outfit detection
|
+-- outputs/                   <- modules that READ from state
|   +-- led_module.py
|   +-- tts_module.py
|   +-- monitor_module.py      <- (future) HDMI display
|   +-- printer_module.py      <- (future) receipt printer
|
+-- web/
    +-- server.py              <- Flask-SocketIO server (port 5000)
    +-- templates/
        +-- remote.html        <- browser remote control UI
```

---

## 5. Raspberry Pi OS setup

### Flash the SD card

Use **Raspberry Pi Imager** (free download). Choose:
- OS: Raspberry Pi OS Lite 64-bit (no desktop needed)
- Enable SSH in Advanced Settings if running headless

### First boot

```bash
sudo apt update && sudo apt upgrade -y

# Core system tools
sudo apt install -y python3-pip python3-dev git ffmpeg espeak-ng

# Python libraries
pip3 install \
  Pillow \
  requests \
  anthropic \
  openai-whisper \
  sounddevice \
  scipy \
  flask \
  flask-socketio \
  eventlet \
  pyserial

# LED matrix library (build from source — one time only)
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix
make build-python PYTHON=$(which python3)
sudo make install-python PYTHON=$(which python3)
cd ..
```

### Disable audio PWM (required for LED matrix)

The LED library conflicts with the Pi's onboard audio PWM. Disable it:

```bash
echo "dtparam=audio=off" | sudo tee -a /boot/config.txt
sudo reboot
```

If using the Adafruit Bonnet, also solder the BOOT jumper on the bonnet itself.

### Verify mic is detected

```bash
arecord -l       # should list your USB mic as a capture device
aplay -l         # should list your speaker
```

### requirements.txt

```
Pillow
requests
anthropic
openai-whisper
sounddevice
scipy
flask
flask-socketio
eventlet
pyserial
RPi.GPIO
```

---

## 6. Wiring the LED matrix

### Using the Adafruit RGB Matrix Bonnet (recommended)

1. Press the Bonnet onto the Pi's 40-pin GPIO header
2. Run the HUB75 IDC ribbon from the Bonnet's output to the panel's **input** port
   (input = the port where the arrow points INTO the panel, not away from it)
3. Connect the panel's barrel connector to your dedicated 5V 4A supply
4. Connect the Pi's USB-C to its own separate power supply

**Never power the LED panel from the Pi's USB ports.** The panel draws up to 4A
at full brightness which will crash or damage the Pi.

### GPIO slowdown setting

Pi 4 almost always needs `gpio_slowdown=2`. If you see flickering or color
corruption, increase to `3` or `4`.

### Chaining a second panel

Run a second HUB75 ribbon from the **output** port of panel 1 into the **input**
port of panel 2. Then in led_module.py:

```python
options.chain_length = 2   # was 1
options.cols = 128          # was 64 (64 x 2 panels)
```

No other wiring changes needed.

---

## 7. Core state bus

**File:** `core/state.py`

The single source of truth for the entire system. Add new keys freely as new
modules are added. Existing modules are unaffected.

```python
# core/state.py

import threading

_lock  = threading.Lock()

_state = {
    # Weather
    "weather_display":         "Loading...",  # short string for LED: "18C Clouds"
    "weather_full":            "",            # full description for Claude context
    "weather_updated":         0,             # unix timestamp of last fetch

    # Schedule
    "current_class":           None,          # dict or None
    "next_class":              None,          # dict or None

    # Voice / LLM
    "is_listening":            False,
    "is_thinking":             False,
    "llm_response":            "",
    "llm_expires_at":          0,

    # Web remote control
    "custom_message":          "",
    "custom_message_expires":  0,
    "display_mode":            "normal",      # normal | weather | schedule | blank
    "brightness":              70,            # 0-100
    "print_trigger":           False,

    # Future: thermal camera
    "thermal_max_temp":        None,
    "person_detected":         False,

    # Future: door / bathroom sensor
    "bathroom_occupied":       False,

    # Future: outfit camera
    "outfit_check_trigger":    False,

    # System
    "system_error":            "",
}

def get(key):
    """Read a value. Safe to call from any thread."""
    with _lock:
        return _state.get(key)

def set(key, value):
    """Write a value. Safe to call from any thread."""
    with _lock:
        _state[key] = value

def get_all():
    """Full snapshot of state (used by web server)."""
    with _lock:
        return dict(_state)
```

---

## 8. Input modules

### `inputs/weather_module.py`

```python
import time, requests
from core import state

WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_KEY"
WEATHER_CITY    = "Waterloo,CA"
REFRESH_SECONDS = 600   # 10 minutes

def run():
    while True:
        try:
            r = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": WEATHER_CITY, "appid": WEATHER_API_KEY, "units": "metric"},
                timeout=5
            )
            d    = r.json()
            temp = round(d["main"]["temp"])
            cond = d["weather"][0]["main"]
            desc = d["weather"][0]["description"]
            hum  = d["main"]["humidity"]

            state.set("weather_display", f"{temp}C {cond}")
            state.set("weather_full",    f"{temp}C, {desc}, {hum}% humidity")
            state.set("weather_updated", time.time())
        except Exception as e:
            state.set("system_error", f"Weather: {e}")

        time.sleep(REFRESH_SECONDS)
```

### `inputs/schedule_module.py`

```python
import time, json
from datetime import datetime
from core import state

SCHEDULE_FILE = "schedule.json"

def _compute(classes):
    now = datetime.now().strftime("%H:%M")
    current = None
    nxt     = None
    for cls in classes:
        if cls["start"] <= now <= cls["end"]:
            current = cls
        elif now < cls["start"]:
            if nxt is None or cls["start"] < nxt["start"]:
                nxt = cls
    return current, nxt

def run():
    while True:
        try:
            with open(SCHEDULE_FILE) as f:
                classes = json.load(f)
            current, nxt = _compute(classes)
            state.set("current_class", current)
            state.set("next_class",    nxt)
        except Exception as e:
            state.set("system_error", f"Schedule: {e}")
        time.sleep(60)
```

---

## 9. Output modules

### `outputs/led_module.py`

```python
import time
from PIL import Image, ImageDraw, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from core import state

C_WEATHER  = (0,   220, 255)
C_WELCOME  = (180, 100, 255)
C_NOW      = (255, 140, 0)
C_NEXT     = (80,  160, 255)
C_RESPONSE = (255, 255, 255)
C_LISTEN   = (0,   255, 100)
C_THINK    = (255, 220, 0)
C_DIM      = (60,  60,  60)

font = ImageFont.load_default()

def _make_matrix():
    opts = RGBMatrixOptions()
    opts.rows                     = 32
    opts.cols                     = 64
    opts.chain_length             = 1
    opts.hardware_mapping         = "adafruit-hat"
    opts.brightness               = 70
    opts.gpio_slowdown            = 2
    opts.disable_hardware_pulsing = True
    return RGBMatrix(options=opts)

def _draw_frame(matrix):
    img  = Image.new("RGB", (64, 32))
    draw = ImageDraw.Draw(img)

    mode       = state.get("display_mode") or "normal"
    custom     = state.get("custom_message") or ""
    custom_exp = state.get("custom_message_expires") or 0

    if mode == "blank":
        pass

    elif custom and time.time() < custom_exp:
        draw.text((1, 12), custom[:12], font=font, fill=(255, 255, 100))

    elif mode == "weather":
        draw.text((1, 0),  state.get("weather_display") or "", font=font, fill=C_WEATHER)
        draw.text((1, 12), state.get("weather_full") or "",    font=font, fill=C_DIM)

    else:
        draw.text((1,  0), state.get("weather_display") or "", font=font, fill=C_WEATHER)
        draw.text((36, 0), "Hi J+M!",                          font=font, fill=C_WELCOME)

        cur = state.get("current_class")
        if cur:
            draw.text((1,  9), "NOW",       font=font, fill=C_NOW)
            draw.text((22, 9), cur["name"], font=font, fill=C_NOW)
        else:
            draw.text((1, 9), "No class",   font=font, fill=C_DIM)

        nxt = state.get("next_class")
        if nxt:
            draw.text((1,  17), "NXT",       font=font, fill=C_NEXT)
            draw.text((22, 17), nxt["name"], font=font, fill=C_NEXT)

        if state.get("is_listening"):
            draw.text((1, 25), "Listening...", font=font, fill=C_LISTEN)
        elif state.get("is_thinking"):
            draw.text((1, 25), "Thinking...",  font=font, fill=C_THINK)
        elif time.time() < (state.get("llm_expires_at") or 0):
            draw.text((1, 25), (state.get("llm_response") or "")[:12], font=font, fill=C_RESPONSE)

    matrix.brightness = state.get("brightness") or 70
    matrix.SetImage(img)

def run():
    matrix = _make_matrix()
    while True:
        _draw_frame(matrix)
        time.sleep(0.1)
```

### `outputs/tts_module.py`

```python
import subprocess, time
from core import state

_last_spoken = ""

def run():
    global _last_spoken
    while True:
        response = state.get("llm_response") or ""
        expires  = state.get("llm_expires_at") or 0
        if response and response != _last_spoken and time.time() < expires:
            subprocess.run(["espeak-ng", "-s", "150", "-v", "en", response])
            _last_spoken = response
        time.sleep(0.5)
```

---

## 10. Voice + Claude pipeline

### Full flow

```
Microphone (5 sec recording)
    | .wav file saved to /tmp/
Silence check — skip if amplitude below threshold
    |
Whisper (local STT, ~3 sec on Pi with tiny model)
    | text string
Claude API (claude-sonnet-4-20250514, max 80 tokens)
    | response string
state.set("llm_response")  ->  LED displays it for 10 sec
espeak-ng speaks it aloud
```

### `inputs/voice_module.py`

```python
import time, subprocess
import sounddevice as sd
import scipy.io.wavfile as wavfile
import numpy as np
import whisper
import anthropic
from core import state

ANTHROPIC_KEY  = "YOUR_ANTHROPIC_KEY"
RECORD_SECONDS = 5
SAMPLE_RATE    = 16000
SILENCE_THRESH = 500        # raise in noisy rooms
TEMP_FILE      = "/tmp/voice_input.wav"

print("Loading Whisper...")
whisper_model = whisper.load_model("tiny")   # or "base" for better accuracy
claude        = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

def record():
    state.set("is_listening", True)
    audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE),
                   samplerate=SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    state.set("is_listening", False)
    wavfile.write(TEMP_FILE, SAMPLE_RATE, audio)
    return TEMP_FILE

def is_silent(path):
    _, data = wavfile.read(path)
    return np.abs(data).mean() < SILENCE_THRESH

def transcribe(path):
    result = whisper_model.transcribe(path, language="en", fp16=False)
    return result["text"].strip()

def ask_claude(text):
    state.set("is_thinking", True)
    try:
        msg = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=80,
            system=(
                "Room sign assistant. Keep every answer under 15 words.\n"
                f"Weather: {state.get('weather_full')}\n"
                f"Current class: {state.get('current_class')}\n"
                f"Next class: {state.get('next_class')}"
            ),
            messages=[{"role": "user", "content": text}]
        )
        response = msg.content[0].text
    except Exception as e:
        response = "Sorry, couldn't connect."
    state.set("is_thinking", False)
    return response

def run():
    while True:
        try:
            path = record()
            if is_silent(path):
                time.sleep(0.3)
                continue
            text = transcribe(path)
            if len(text) < 4:
                continue
            response = ask_claude(text)
            state.set("llm_response",   response)
            state.set("llm_expires_at", time.time() + 10)
            subprocess.run(["espeak-ng", "-s", "150", "-v", "en", response])
            time.sleep(10)
            state.set("llm_response", "")
        except Exception as e:
            print(f"Voice error: {e}")
            time.sleep(2)
```

### Whisper model reference

| Model | Download size | Speed on Pi 4 | Use when |
|---|---|---|---|
| `tiny` | 75MB | ~3 sec | Starting out, clear speech |
| `base` | 145MB | ~6 sec | Accented or quieter speech |
| `small` | 465MB | ~15 sec | High accuracy needed |

---

## 11. Web remote control

A Flask-SocketIO server runs alongside `main.py`. It serves the remote control
webpage and maintains a persistent WebSocket tunnel for real-time sync.

### Why WebSocket

Regular HTTP polling: browser asks every N seconds — adds lag, wastes requests,
Pi cannot push updates.

WebSocket: permanent two-way tunnel — Pi pushes state the instant it changes,
browser commands arrive in ~2ms over local WiFi.

### Events reference

**Browser -> Pi (commands):**

| Event | Payload | Effect |
|---|---|---|
| `set_message` | `{text: string}` | Shows custom text on LED for 30s |
| `clear_message` | `{}` | Clears custom message immediately |
| `set_mode` | `{mode: string}` | Switches display mode |
| `set_brightness` | `{value: 0-100}` | Updates LED brightness |
| `trigger_print` | `{}` | Sets print_trigger=True in state |

**Pi -> Browser (state push):**

| Event | Payload | When |
|---|---|---|
| `state_update` | full state dict | On connect, every 1 sec, after every command |

### Display modes

| Mode | What shows on LED |
|---|---|
| `normal` | Weather + welcome + classes + AI responses |
| `weather` | Weather fullscreen |
| `schedule` | Class schedule fullscreen |
| `blank` | Black screen (useful at night) |

### `web/server.py`

```python
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading, time
from core import state

app      = Flask(__name__)
app.config["SECRET_KEY"] = "roomsign2024"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

@app.route("/")
def index():
    return render_template("remote.html")

@app.route("/state")
def get_state():
    return jsonify(state.get_all())

@socketio.on("connect")
def on_connect():
    emit("state_update", state.get_all())

@socketio.on("set_message")
def on_set_message(data):
    state.set("custom_message",         data.get("text", "")[:64])
    state.set("custom_message_expires", time.time() + 30)
    socketio.emit("state_update", state.get_all())

@socketio.on("set_brightness")
def on_set_brightness(data):
    state.set("brightness", max(0, min(100, int(data.get("value", 70)))))
    socketio.emit("state_update", state.get_all())

@socketio.on("set_mode")
def on_set_mode(data):
    state.set("display_mode", data.get("mode", "normal"))
    socketio.emit("state_update", state.get_all())

@socketio.on("trigger_print")
def on_trigger_print(data):
    state.set("print_trigger", True)
    socketio.emit("state_update", state.get_all())

@socketio.on("clear_message")
def on_clear_message(data):
    state.set("custom_message", "")
    socketio.emit("state_update", state.get_all())

def _broadcaster():
    while True:
        socketio.emit("state_update", state.get_all())
        time.sleep(1)

def run():
    threading.Thread(target=_broadcaster, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000)
```

### Accessing the remote

```bash
hostname -I   # get Pi's IP, e.g. 192.168.1.100

# Open on any device on the same WiFi:
# http://192.168.1.100:5000
```

---

## 12. Main entry point

**File:** `main.py`

The only file that imports modules. Adding a device = uncomment two lines here.

```python
import threading

# Inputs — write to state
from inputs import weather_module
from inputs import schedule_module
from inputs import voice_module
# from inputs import thermal_module
# from inputs import sensor_module
# from inputs import camera_module

# Outputs — read from state
from outputs import led_module
from outputs import tts_module
# from outputs import monitor_module
# from outputs import printer_module

# Web remote
from web import server as web_server

def start(module):
    t = threading.Thread(target=module.run, daemon=True)
    t.start()
    return t

if __name__ == "__main__":
    print("Starting room sign...")

    start(weather_module)
    start(schedule_module)
    start(voice_module)
    start(led_module)
    start(tts_module)
    start(web_server)

    print("All modules running. Open http://PI_IP:5000 for remote control.")
    print("Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down.")
```

---

## 13. Schedule data format

**File:** `schedule.json`

```json
[
  {
    "name":     "CS 246",
    "room":     "DC 1350",
    "start":    "14:30",
    "end":      "15:20",
    "datetime": "2026-05-13T14:30"
  },
  {
    "name":     "MATH 237",
    "room":     "MC 4058",
    "start":    "16:00",
    "end":      "17:20",
    "datetime": "2026-05-13T16:00"
  },
  {
    "name":     "PHYS 121",
    "room":     "PAC 1001",
    "start":    "09:30",
    "end":      "10:20",
    "datetime": "2026-05-13T09:30"
  }
]
```

Fields:
- `start` / `end` — 24h `HH:MM` strings, used for current/next class detection
- `datetime` — ISO 8601, used for sorting and future calendar sync
- `room` — displayed on LED and in Claude context

Update this file weekly, or write a Google Calendar sync script that rewrites
it automatically via a cron job.

---

## 14. Multi-Pi sync

### Option A — one Pi, powered USB hub (start here)

All devices plug into one Pi via a powered USB hub. No networking complexity.

```
Pi -> powered USB hub -> mic, speaker, printer, camera
Pi -> HUB75 Bonnet   -> LED panel
Pi -> Micro HDMI     -> TV / monitor
```

### Option B — primary Pi + satellite Pis over WiFi

Primary Pi runs `main.py` and `web/server.py`. Satellite Pis poll `/state` and
drive their local displays. Scales to multiple rooms.

**Satellite Pi — `satellite.py`:**

```python
import time, requests
from PIL import Image, ImageDraw, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions

PRIMARY_IP = "192.168.1.100"   # update to your primary Pi's IP
STATE_URL  = f"http://{PRIMARY_IP}:5000/state"
font       = ImageFont.load_default()

def fetch():
    try:
        return requests.get(STATE_URL, timeout=2).json()
    except Exception:
        return {}

def make_matrix():
    opts = RGBMatrixOptions()
    opts.rows = 32; opts.cols = 64
    opts.hardware_mapping = "adafruit-hat"
    opts.brightness = 70; opts.gpio_slowdown = 2
    return RGBMatrix(options=opts)

def draw(matrix, s):
    img  = Image.new("RGB", (64, 32))
    draw = ImageDraw.Draw(img)
    draw.text((1,  0), s.get("weather_display", ""),  font=font, fill=(0, 220, 255))
    draw.text((36, 0), "Hi J+M!",                     font=font, fill=(180, 100, 255))
    cur = s.get("current_class")
    if cur:
        draw.text((1,  9), "NOW",       font=font, fill=(255, 140, 0))
        draw.text((22, 9), cur["name"], font=font, fill=(255, 220, 150))
    nxt = s.get("next_class")
    if nxt:
        draw.text((1,  17), "NXT",       font=font, fill=(80, 160, 255))
        draw.text((22, 17), nxt["name"], font=font, fill=(150, 200, 255))
    matrix.SetImage(img)

if __name__ == "__main__":
    matrix = make_matrix()
    while True:
        draw(matrix, fetch())
        time.sleep(0.5)
```

---

## 15. Adding new devices

Every new device follows the same three-step pattern. No existing files change.

### Step 1 — add state keys in `core/state.py`

```python
# Example: adding a CO2 sensor
"co2_ppm":     None,
"air_quality":  "unknown",
```

### Step 2 — write the module

**Input module** (writes to state):

```python
# inputs/co2_module.py
import time
from core import state

def run():
    while True:
        try:
            ppm = read_co2_sensor()     # your sensor library here
            state.set("co2_ppm",    ppm)
            state.set("air_quality", "good" if ppm < 1000 else "poor")
        except Exception as e:
            state.set("system_error", f"CO2: {e}")
        time.sleep(10)
```

**Output module** (reads from state):

```python
# outputs/printer_module.py
import time, serial
from core import state

def run():
    try:
        printer = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)
    except Exception as e:
        state.set("system_error", f"Printer: {e}")
        return

    while True:
        if state.get("print_trigger"):
            cur = state.get("current_class")
            nxt = state.get("next_class")
            lines = [
                "=== ROOM SIGN ===",
                f"Weather: {state.get('weather_full')}",
                f"NOW:  {cur['name'] if cur else 'None'}",
                f"NEXT: {nxt['name'] if nxt else 'None'}",
                "=================\n"
            ]
            for line in lines:
                printer.write((line + "\n").encode())
                time.sleep(0.05)
            state.set("print_trigger", False)
        time.sleep(0.5)
```

### Step 3 — register in `main.py`

```python
from inputs import co2_module   # add this
start(co2_module)               # add this
```

That is the entire process. Nothing else changes.

---

## 16. Future expansion modules

### Bathroom / door occupancy sensor

Hardware: reed switch (~$2) or PIR sensor (~$3) wired to a GPIO pin.

```python
# inputs/sensor_module.py
import time
import RPi.GPIO as GPIO
from core import state

BATHROOM_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(BATHROOM_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def run():
    while True:
        state.set("bathroom_occupied", GPIO.input(BATHROOM_PIN) == GPIO.HIGH)
        time.sleep(0.5)
```

Add a colored corner dot to the LED display:

```python
# In led_module.py _draw_frame():
occupied = state.get("bathroom_occupied")
dot_color = (255, 60, 60) if occupied else (60, 255, 60)
draw.rectangle([(60, 0), (63, 3)], fill=dot_color)
```

### Outfit + weather camera

Hardware: Pi Camera Module 3 (CSI ribbon) or USB webcam.

```python
# inputs/camera_module.py
import base64, time
from picamera2 import Picamera2
import anthropic
from core import state

claude = anthropic.Anthropic(api_key="YOUR_KEY")

def capture_b64():
    cam = Picamera2()
    cam.start()
    cam.capture_file("/tmp/outfit.jpg")
    cam.close()
    with open("/tmp/outfit.jpg", "rb") as f:
        return base64.b64encode(f.read()).decode()

def check_outfit():
    img_b64 = capture_b64()
    msg = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=60,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg", "data": img_b64
            }},
            {"type": "text", "text":
                f"Is this outfit appropriate for {state.get('weather_full')}? "
                "Answer in under 12 words."}
        ]}]
    )
    return msg.content[0].text

def run():
    while True:
        if state.get("outfit_check_trigger"):
            result = check_outfit()
            state.set("llm_response",          result)
            state.set("llm_expires_at",         time.time() + 15)
            state.set("outfit_check_trigger",   False)
        time.sleep(1)
```

Trigger from voice ("check my outfit") or add a button to the web remote:

```javascript
// In remote.html
socket.emit("set_state_key", { key: "outfit_check_trigger", value: true });
```

### HDMI monitor / TV dashboard

Pi 4 has two Micro HDMI ports. Use Pygame for fullscreen display.

```python
# outputs/monitor_module.py
import pygame, time
from core import state

def run():
    pygame.init()
    screen  = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
    font_lg = pygame.font.SysFont("monospace", 80)
    font_sm = pygame.font.SysFont("monospace", 40)
    clock   = pygame.time.Clock()

    while True:
        screen.fill((10, 10, 10))

        weather = state.get("weather_display") or ""
        cur     = state.get("current_class")
        nxt     = state.get("next_class")

        screen.blit(font_lg.render(weather, True, (0, 220, 255)), (60, 60))

        if cur:
            screen.blit(font_lg.render(f"NOW  {cur['name']}", True, (255, 140, 0)), (60, 200))
            screen.blit(font_sm.render(cur["room"], True, (180, 120, 0)), (60, 300))
        if nxt:
            screen.blit(font_lg.render(f"NEXT {nxt['name']}", True, (80, 160, 255)), (60, 420))
            screen.blit(font_sm.render(f"Starts {nxt['start']}", True, (60, 120, 200)), (60, 520))

        llm = state.get("llm_response") or ""
        if llm:
            screen.blit(font_sm.render(llm, True, (255, 255, 255)), (60, 900))

        pygame.display.flip()
        clock.tick(10)
```

### Thermal camera (person detection)

Hardware: MLX90640 breakout board (~$40), connects over I2C.

```python
# inputs/thermal_module.py
import time
import board, busio
import adafruit_mlx90640
import numpy as np
from core import state

def run():
    i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
    mlx = adafruit_mlx90640.MLX90640(i2c)
    mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
    frame = [0] * 768

    while True:
        try:
            mlx.getFrame(frame)
            max_temp = max(frame)
            state.set("thermal_max_temp", round(max_temp, 1))
            state.set("person_detected",  max_temp > 30.0)
        except Exception as e:
            state.set("system_error", f"Thermal: {e}")
        time.sleep(0.5)
```

---

## 17. Auto-start on boot

```bash
sudo nano /etc/systemd/system/roomsign.service
```

```ini
[Unit]
Description=Room Sign System
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/room_sign/main.py
WorkingDirectory=/home/pi/room_sign
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable roomsign
sudo systemctl start roomsign

# Check status
sudo systemctl status roomsign

# Follow logs in real time
journalctl -u roomsign -f
```

---

## 18. Troubleshooting

### LED panel shows nothing
- Check barrel power (5V 4A) is connected to the panel, not the Pi USB
- Confirm HUB75 ribbon is in the **input** port (arrow pointing into panel)
- Run the test: `sudo python3 rpi-rgb-led-matrix/bindings/python/samples/image-scroller.py --led-no-hardware-pulse`
- Script must be run with `sudo`

### LED panel flickers or shows wrong colors
```python
opts.gpio_slowdown = 3   # try 3 then 4
```

### Microphone not detected
```bash
arecord -l
dmesg | grep -i usb
```

### Whisper is too slow
Switch to `tiny` model:
```python
whisper_model = whisper.load_model("tiny")
```

### Claude API errors
- Wrong or expired key: check console.anthropic.com
- No credits: add at console.anthropic.com/billing
- Network issue: `ping api.anthropic.com`

### Web remote cannot connect
```bash
hostname -I                  # confirm Pi's IP
sudo systemctl status roomsign
sudo ufw allow 5000          # open port if firewall is active
```

### LED library not found when running with sudo
```bash
cd rpi-rgb-led-matrix
sudo make install-python PYTHON=$(which python3)
```

### Weather shows stale data
Weather refreshes every 10 minutes by design. To force a refresh, restart the
service: `sudo systemctl restart roomsign`

---

*Last updated: May 2026*
*Hardware: Raspberry Pi 4 · Waveshare 64x32 LED Matrix · Adafruit RGB Matrix Bonnet*
*Stack: Python 3 · Flask-SocketIO · OpenAI Whisper · Anthropic Claude · OpenWeatherMap*
