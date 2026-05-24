# LED Matrix Prototyper

## Run

From this directory:

```bash
python3 -m http.server 8080
```

Open [http://localhost:8080](http://localhost:8080) in your browser.

## Web control panel

On the Pi:

```bash
sudo systemctl restart led-web led-listener
sudo systemctl stop led-web led-listener
```

UI: `http://<pi>:5000`. Services: `led-web`, `led-listener`.

## Run direct scripts on the Pi

```bash
cd led-display-test
```

```bash
sudo python3 scripts/weather-test.py
```

Sudo is required for GPIO access. `Ctrl+C` to stop.

Tuning knobs live at the top of each script (`GPIO_SLOWDOWN`, `BRIGHTNESS`, `HARDWARE_MAPPING`, etc.). If the panel flickers, bump `GPIO_SLOWDOWN` to 3 or 4.