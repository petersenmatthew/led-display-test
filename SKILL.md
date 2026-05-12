---
name: room-sign
description: >
  Use this skill whenever working on the room sign project — a modular
  Raspberry Pi system with a 64x32 LED matrix, voice input, Claude AI,
  weather API, class schedule display, and a Flask-SocketIO web remote.
  Triggers include: any mention of the LED sign, room sign, display modules,
  voice pipeline, web remote, schedule display, or adding new hardware to
  the Pi system. Also triggers when the user asks to add a new module,
  fix a display bug, extend the web remote, or integrate a new sensor/device.
---

## Project identity

This is a modular room sign system built by Justin and Matthew at the
University of Waterloo. The Pi runs in a university room and displays weather,
class schedules, and AI responses on a 64x32 HUB75 LED matrix. A Flask-SocketIO
web server at port 5000 provides a real-time browser remote control.

---

## Core architecture rule

**Modules never import each other. They only import `core.state`.**

Every feature is a standalone module with a single `run()` function that loops
forever in a background thread. Input modules write to state. Output modules
read from state. `main.py` is the only file that imports modules.

Adding a new device always follows exactly three steps:
1. Add new keys to `core/state.py`
2. Write the module (`inputs/` or `outputs/`) with a `run()` function
3. Add two lines to `main.py`: one import, one `start()` call

No other files change. Never break this pattern.

---

## Folder layout

```
room_sign/
  main.py              <- only file that imports modules; boots everything
  schedule.json        <- class timetable data
  requirements.txt
  core/
    state.py           <- thread-safe shared dict; single source of truth
  inputs/              <- write to state
    weather_module.py
    schedule_module.py
    voice_module.py
    thermal_module.py  (future)
    sensor_module.py   (future)
    camera_module.py   (future)
  outputs/             <- read from state
    led_module.py
    tts_module.py
    monitor_module.py  (future)
    printer_module.py  (future)
  web/
    server.py          <- Flask-SocketIO, port 5000
    templates/
      remote.html      <- browser remote control
```

---

## State keys reference

When adding code that reads or writes state, use these exact key names.
Never access `_state` directly — always use `state.get()` and `state.set()`.

```python
# Weather (written by weather_module, read by led_module + voice_module)
"weather_display"         # str  — short: "18C Clouds"
"weather_full"            # str  — long: "18C, cloudy, 72% humidity"
"weather_updated"         # float — unix timestamp

# Schedule (written by schedule_module)
"current_class"           # dict | None — {"name", "room", "start", "end"}
"next_class"              # dict | None

# Voice / LLM (written by voice_module)
"is_listening"            # bool
"is_thinking"             # bool
"llm_response"            # str
"llm_expires_at"          # float — unix timestamp

# Web remote (written by web/server.py)
"custom_message"          # str
"custom_message_expires"  # float — unix timestamp
"display_mode"            # str — "normal"|"weather"|"schedule"|"blank"
"brightness"              # int — 0-100
"print_trigger"           # bool — reset to False after printing

# Future sensors
"thermal_max_temp"        # float | None
"person_detected"         # bool
"bathroom_occupied"       # bool
"outfit_check_trigger"    # bool

# System
"system_error"            # str
```

---

## LED display layout

The panel is 64 pixels wide x 32 pixels tall. The default font is 6px wide x 8px
tall per character. Use these y-positions for the four text rows:

```
y=0   weather_display (cyan)      + "Hi J+M!" right-aligned (purple)
y=9   "NOW" + current_class name  (orange)
y=17  "NXT" + next_class name     (blue)
y=25  is_listening / is_thinking / llm_response / custom_message
```

Colors used in led_module.py:
- Weather:  (0,   220, 255)  cyan
- Welcome:  (180, 100, 255)  purple
- NOW:      (255, 140, 0)    orange
- NXT:      (80,  160, 255)  blue
- Response: (255, 255, 255)  white
- Listening:(0,   255, 100)  green
- Thinking: (255, 220, 0)    yellow
- Dim:      (60,  60,  60)   gray

Display mode priority in `_draw_frame()`:
1. `display_mode == "blank"` — black screen
2. `custom_message` is set and not expired — show it fullscreen
3. `display_mode == "weather"` — weather fullscreen
4. `display_mode == "schedule"` — schedule fullscreen
5. Default "normal" — all four rows as above

---

## Hardware constants

```python
# LED matrix options (RGBMatrixOptions)
opts.rows             = 32
opts.cols             = 64           # 128 if chain_length=2
opts.chain_length     = 1            # 2 for second panel daisy-chained
opts.hardware_mapping = "adafruit-hat"
opts.brightness       = 70           # overridden at runtime by state["brightness"]
opts.gpio_slowdown    = 2            # increase to 3-4 if flickering

# Voice recording
SAMPLE_RATE    = 16000   # Hz — Whisper expects 16kHz
RECORD_SECONDS = 5
SILENCE_THRESH = 500     # mean amplitude below this = skip transcription
TEMP_FILE      = "/tmp/voice_input.wav"

# Whisper
MODEL_SIZE = "tiny"      # tiny ~3s | base ~6s | small ~15s on Pi 4

# Claude
MODEL      = "claude-sonnet-4-20250514"
MAX_TOKENS = 80          # keep responses short for the LED display

# Web server
PORT = 5000
HOST = "0.0.0.0"         # accessible from any device on the same WiFi

# Weather
WEATHER_REFRESH = 600    # seconds between API calls (10 min)
CITY            = "Waterloo,CA"
```

---

## Module template

Use this exact pattern for every new module:

```python
# inputs/example_module.py  (or outputs/)
import time
from core import state

def run():
    """Called by main.py in a background daemon thread. Runs forever."""
    while True:
        try:
            # --- do the thing ---
            value = read_some_sensor()
            state.set("some_key", value)
        except Exception as e:
            state.set("system_error", f"ModuleName: {e}")
        time.sleep(INTERVAL)
```

And in `main.py`:

```python
from inputs import example_module   # add import
start(example_module)               # add start call
```

---

## Web remote — WebSocket events

**Browser emits (commands to Pi):**
- `set_message`    `{text: str}`     — custom text on LED for 30s
- `clear_message`  `{}`
- `set_mode`       `{mode: str}`     — "normal"|"weather"|"schedule"|"blank"
- `set_brightness` `{value: int}`    — 0-100
- `trigger_print`  `{}`

**Pi emits (state push to browser):**
- `state_update`   full state dict   — on connect + every 1s + after every command

When adding a new web remote button:
1. Add a `@socketio.on("event_name")` handler in `web/server.py`
2. Call `state.set(...)` then `socketio.emit("state_update", state.get_all())`
3. Add `socket.emit("event_name", payload)` to the button's onclick in `remote.html`

---

## Voice pipeline sequence

```
record()          5 sec audio -> /tmp/voice_input.wav
is_silent()       skip if mean amplitude < SILENCE_THRESH
transcribe()      Whisper local STT, language="en", fp16=False
ask_claude()      system prompt includes weather_full + current_class + next_class
state.set(...)    llm_response + llm_expires_at = now + 10
espeak-ng         subprocess.run(["espeak-ng", "-s", "150", "-v", "en", response])
```

Claude system prompt must always include:
- Current weather (`state.get("weather_full")`)
- Current class (`state.get("current_class")`)
- Next class (`state.get("next_class")`)
- Instruction to answer in under 15 words

---

## Schedule data format

`schedule.json` is a list of class dicts:

```json
{
  "name":     "CS 246",
  "room":     "DC 1350",
  "start":    "14:30",
  "end":      "15:20",
  "datetime": "2026-05-13T14:30"
}
```

`start`/`end` are `HH:MM` 24h strings used for current/next detection.
`datetime` is ISO 8601 used for sorting.

---

## Common pitfalls

- **Never run without `sudo`** — the LED library needs direct GPIO hardware access
- **Never power the LED panel from the Pi's USB** — it draws up to 4A; use the separate 5V 4A barrel supply
- **HUB75 ribbon must go into the INPUT port** — the port where the arrow points INTO the panel
- **Whisper `fp16=False`** — the Pi has no GPU; fp16 will crash
- **`gpio_slowdown`** — start at 2, increase to 3-4 if you see flickering or color corruption
- **Audio PWM conflict** — add `dtparam=audio=off` to `/boot/config.txt` or the LED display will glitch
- **Always wrap API calls in try/except** — network errors must not crash the display loop
- **`state.get_all()` for web** — never serialize `_state` directly; use the public API

---

## Running the project

```bash
# Development
sudo python3 main.py

# Production (auto-starts on boot)
sudo systemctl start roomsign
sudo systemctl status roomsign
journalctl -u roomsign -f

# Remote control
# Open http://PI_IP:5000 on any device on the same WiFi
# Find Pi IP with: hostname -I
```

---

## Future modules checklist

When any of these are requested, follow the three-step pattern above.
State keys are already defined in `core/state.py`.

- [ ] `inputs/thermal_module.py`  — MLX90640 over I2C, writes `thermal_max_temp`, `person_detected`
- [ ] `inputs/sensor_module.py`   — PIR/reed switch on GPIO, writes `bathroom_occupied`
- [ ] `inputs/camera_module.py`   — Pi Camera + Claude vision, writes `llm_response` on trigger
- [ ] `outputs/printer_module.py` — USB serial thermal printer, reads `print_trigger`
- [ ] `outputs/monitor_module.py` — Pygame fullscreen on HDMI, reads all display state
- [ ] `satellite.py`              — polls `/state` from primary Pi, drives remote LED panel
