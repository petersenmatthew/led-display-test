---
name: led-matrix-preview
description: Render Raspberry Pi rgbmatrix LED matrix Python scripts to local PNG previews using a mocked RGBMatrix, FrameCanvas, and graphics module. Use when Codex needs to visually inspect, debug, or share output from 64x32 HUB75 display scripts, weather scenes, canvas animations, or scripts that call rgbmatrix without requiring a physical LED panel or the browser preview.
---

# LED Matrix Preview

## Overview

Use this skill to render LED matrix Python scripts or specific draw functions to a PNG preview. It is intended for fast visual checks of pixel placement, colors, weather scenes, and animation frames in this project.

## Workflow

1. From the repo root, identify the script and draw function to preview.
2. Use `scripts/render_led_matrix.py` with `--function` for deterministic output.
3. Open the output PNG with the local image viewer and inspect alignment, colors, text, and animation frame state.
4. If the script has an infinite loop at top level, expose a draw function first; the renderer imports the script before calling the function.

## Render Command

Use:

```bash
python3 .agents/skills/led-matrix-preview/scripts/render_led_matrix.py \
  scripts/weather-test.py \
  --function draw_night \
  --frame 42 \
  --output /private/tmp/preview.png
```

For other scenes, change the function name:

```bash
python3 .agents/skills/led-matrix-preview/scripts/render_led_matrix.py \
  scripts/weather-test.py \
  --function draw_sunny \
  --frame 18 \
  --output /private/tmp/weather-sunny.png
```

## Notes

- Default canvas size is inferred from `ROWS`/`COLS`, `W`/`H`, or matrix options when possible; override with `--width` and `--height` when needed.
- Default scale is `10`, using nearest-neighbor so LED pixels remain crisp.
- The renderer stubs common `rgbmatrix` APIs: `RGBMatrix`, `RGBMatrixOptions`, `FrameCanvas`, `SetPixel`, `Clear`, `Fill`, `SwapOnVSync`, `graphics.Font`, `graphics.Color`, `graphics.DrawText`, and `graphics.DrawLine`.
- Text rendering is intentionally approximate. It is good for layout smoke tests; use `index.html` or hardware for exact BDF font rendering.
