# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A two-part project:
1. **Browser prototyper** (`index.html` + `worker.js`) — a single-page LED matrix simulator where you write and run display scripts live in the browser before deploying to hardware.
2. **Raspberry Pi scripts** (`scripts/`) — Python scripts that run on a real 64×32 HUB75 LED panel via `hzeller/rpi-rgb-led-matrix`.

## Running the browser prototyper

```bash
python3 -m http.server 8080
# Open http://localhost:8080
```

Do not open `index.html` from the filesystem — the worker requires a real HTTP URL.

## Writing scripts

Scripts in `scripts/` use the `rgbmatrix` Python library (Pi-only). The standard pattern:

```python
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

opts = RGBMatrixOptions()
opts.rows = 32
opts.cols = 64
matrix = RGBMatrix(options=opts)
offscreen = matrix.CreateFrameCanvas()
# ... draw loop using offscreen.SwapOnVSync(offscreen)
```

**Fonts** live in `fonts/` as BDF files (e.g. `tom-thumb.bdf`, `5x7.bdf`, `6x9.bdf`, `7x13.bdf`). Load with `graphics.Font(); font.LoadFont("fonts/5x7.bdf")`.

**Target hardware:** 64×32 pixel display. Character widths: `tom-thumb` ~4px, `5x7` ~5px, `6x9`/`6x10`/`6x12` ~6px, `7x13`/`7x14` ~7px. Plan layouts accordingly.

Scripts should run standalone with `python3 scripts/foo.py` from the repo root. Keep all font paths relative to the repo root.

## Pi deployment notes (from ROOM_SIGN_DOCS.md)

- LED scripts must run with `sudo`
- Pi 4 typically needs `opts.gpio_slowdown = 2` (increase to 3–4 if flickering)
- Never power the LED panel from Pi USB — use a dedicated 5V 4A supply
- The full room sign system (`ROOM_SIGN_DOCS.md`) uses a shared state bus pattern: all modules only import `core/state`, never each other
