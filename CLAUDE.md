# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A single-file HTML/Canvas LED matrix display that scrolls "HELLO WORLD" across a simulated 64×32 LED grid with a pulsing amber glow effect.

## Running

Open `index.html` directly in a browser — no build step, no dependencies, no server required.

## Architecture

Everything lives in `index.html`. The structure is:

- **Grid model** — a `ROWS×COLS` boolean 2D array representing lit/unlit LEDs
- **Font** — inline 5×5 bitmap font (`FONT` object), characters defined as `#`/`.` strings
- **`measure(text)`** — calculates pixel width of a string in LED-pixel units
- **`drawText(grid, text, x0, y0)`** — writes glyphs into the grid at a given LED-pixel offset; clips to grid bounds (enables scrolling)
- **`getPulseIntensity(time)`** — returns a 0.5–1.0 brightness value on a sine curve, firing every `PULSE_INTERVAL` ms
- **`render(grid, intensity)`** — draws the grid to canvas; applies `shadowBlur` glow when intensity > 0.6
- **`animate(time)`** — main RAF loop throttled to ~20fps; advances `scrollX` left each frame, resets when text exits

## Key Constants

| Constant | Value | Purpose |
|---|---|---|
| `COLS` / `ROWS` | 64 / 32 | Grid dimensions |
| `PITCH` | 10px | Canvas pixels per LED cell |
| `DOT` | 9px | Size of lit dot (1px gap) |
| `ON_BASE` | `[255, 159, 67]` | Base amber LED color |
| `SCROLL_SPEED` | 2 | LED pixels per frame |
| `PULSE_INTERVAL` | 3000ms | Time between brightness pulses |
