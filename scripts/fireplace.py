"""Cozy animated fireplace for a 64x32 RGB LED matrix.

A "24-hour fireplace channel" style scene: a contained plume of dancing flames
rising off two crossed logs, set against a dim brick back wall, with pulsing
embers and the odd drifting spark. The flames use the classic Doom fire
algorithm (heat seeded at the base, cooled and drifted as it propagates upward)
mapped through a black -> ember -> gold -> white palette, then blended over the
static brick + log backdrop so the fire only ever lightens the scene.

Pure SetPixel, no external assets, so it runs unchanged in the browser preview
and on the Pi.
"""

from __future__ import annotations

import random
import time

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from led_brightness import apply_live_brightness, read_initial_brightness

ROWS = 32
COLS = 64

FRAME_SLEEP = 0.045  # ~22 fps

# ─── Flame source ────────────────────────────────────────────────────────────
# The fire is a contained plume: seeded on a narrow band centered over the log
# crossing and cooled hard so it dies out well before the top of the panel.
CENTER_X = 32
SEED_Y = 24            # hottest flame-source row (just above the log crossing)
FIRE_HALF = 11         # seed spans CENTER_X +/- FIRE_HALF
COOL = 5               # higher = shorter flames


def _build_palette(stops, n):
    """Interpolate a list of (r, g, b) stops into an n-entry gradient."""
    palette = []
    segments = len(stops) - 1
    for i in range(n):
        t = i / (n - 1) * segments
        lo = min(int(t), segments - 1)
        f = t - lo
        r0, g0, b0 = stops[lo]
        r1, g1, b1 = stops[lo + 1]
        palette.append((
            round(r0 + (r1 - r0) * f),
            round(g0 + (g1 - g0) * f),
            round(b0 + (b1 - b0) * f),
        ))
    return palette


# Black -> deep red -> ember -> orange -> gold -> near-white flame gradient.
FIRE_STOPS = [
    (0, 0, 0),
    (24, 4, 0),
    (68, 8, 0),
    (130, 22, 0),
    (190, 48, 0),
    (232, 92, 6),
    (250, 140, 20),
    (255, 184, 48),
    (255, 222, 110),
    (255, 246, 190),
]
PALETTE = _build_palette(FIRE_STOPS, 40)
MAX_HEAT = len(PALETTE) - 1

# ─── Brick back wall ─────────────────────────────────────────────────────────
BRICK_W = 13
BRICK_H = 6
MORTAR = (16, 11, 10)
BRICK_BASE = (46, 24, 19)


def build_bricks():
    """Static dim brick wall: offset courses with darker mortar seams."""
    bg = [[(0, 0, 0)] * COLS for _ in range(ROWS)]
    for y in range(ROWS):
        band = y // BRICK_H
        offset = (BRICK_W // 2) if (band % 2) else 0
        for x in range(COLS):
            xx = x + offset
            if (y % BRICK_H == 0) or (xx % BRICK_W == 0):
                bg[y][x] = MORTAR
            else:
                # Deterministic per-brick shade variation for a bit of texture.
                v = 0.75 + 0.4 * (((band * 7 + xx // BRICK_W * 13) % 5) / 4)
                r, g, b = BRICK_BASE
                bg[y][x] = (int(r * v), int(g * v), int(b * v))
    return bg


# ─── Crossed logs ────────────────────────────────────────────────────────────
LOG_A = (13, 30, 51, 16)   # lower-left  -> upper-right
LOG_B = (51, 30, 13, 16)   # lower-right -> upper-left
LOG_RADIUS = 2

# Distance-from-centerline shading: lit top, mid body, dark underside.
LOG_LIT = (120, 66, 30)
LOG_MID = (78, 40, 16)
LOG_DARK = (44, 22, 9)
LOG_CAP = (150, 96, 52)    # sawn end face


def _stamp_log(base, x0, y0, x1, y1):
    """Draw one shaded log cylinder into the base buffer."""
    steps = max(abs(x1 - x0), abs(y1 - y0))
    for i in range(steps + 1):
        t = i / steps
        cx = x0 + (x1 - x0) * t
        cy = y0 + (y1 - y0) * t
        for dx in range(-LOG_RADIUS, LOG_RADIUS + 1):
            for dy in range(-LOG_RADIUS, LOG_RADIUS + 1):
                px = int(round(cx)) + dx
                py = int(round(cy)) + dy
                if not (0 <= px < COLS and 0 <= py < ROWS):
                    continue
                dist = (dx * dx + dy * dy) ** 0.5
                if dist > LOG_RADIUS + 0.4:
                    continue
                if dy <= -1:
                    color = LOG_LIT       # top edge catches the firelight
                elif dy >= LOG_RADIUS:
                    color = LOG_DARK      # shaded underside
                else:
                    color = LOG_MID
                base[py][px] = color
    # Sawn end-cap disc at the near (lower) end of the log.
    for dx in range(-LOG_RADIUS, LOG_RADIUS + 1):
        for dy in range(-LOG_RADIUS, LOG_RADIUS + 1):
            px, py = x0 + dx, y0 + dy
            if 0 <= px < COLS and 0 <= py < ROWS and dx * dx + dy * dy <= LOG_RADIUS * LOG_RADIUS:
                base[py][px] = LOG_CAP if (dx * dx + dy * dy) <= 1 else LOG_MID


def build_base():
    """Bricks with the two crossed logs stamped on top (static per frame)."""
    base = build_bricks()
    _stamp_log(base, *LOG_A)
    _stamp_log(base, *LOG_B)
    return base


BASE = build_base()

# ─── State ───────────────────────────────────────────────────────────────────
# Heat grid, one value (0..MAX_HEAT) per pixel. y=0 is the top of the panel.
heat = [[0] * COLS for _ in range(ROWS)]

# Per-column seed intensity: a hump inside the plume band, zero outside.
SEED_BASE = [0.0] * COLS
for _x in range(COLS):
    _d = (_x - CENTER_X) / FIRE_HALF
    SEED_BASE[_x] = max(0.0, 1.0 - _d * _d) if abs(_x - CENTER_X) <= FIRE_HALF else 0.0

sparks = []  # each: [x, y, life]


def seed_fire():
    """Refresh the flame-source row with a flickering heat profile."""
    row = heat[SEED_Y]
    rnd = random.random
    for x in range(COLS):
        base = SEED_BASE[x]
        if base <= 0.0:
            row[x] = 0
            continue
        if rnd() < 0.85:
            level = base * (0.75 + 0.25 * rnd())
        else:
            level = base * (0.35 + 0.25 * rnd())
        row[x] = int(MAX_HEAT * level)


def spread_fire():
    """Propagate heat one row upward with cooling and sideways wind drift."""
    rnd = random.random
    for x in range(COLS):
        for y in range(1, SEED_Y + 1):
            val = heat[y][x]
            if val <= 0:
                heat[y - 1][x] = 0
                continue
            r = int(rnd() * 3)          # 0, 1, 2 -> drift -1, 0, +1
            nx = x + r - 1
            if nx < 0:
                nx = 0
            elif nx >= COLS:
                nx = COLS - 1
            decay = int(rnd() * COOL)
            new = val - decay
            heat[y - 1][nx] = new if new > 0 else 0


def update_sparks():
    """Spawn, move, and retire drifting sparks."""
    rnd = random.random
    if rnd() < 0.4:
        x = random.randint(CENTER_X - 8, CENTER_X + 8)
        sparks.append([float(x), float(random.randint(14, 20)), random.randint(6, 16)])
    alive = []
    for s in sparks:
        s[1] -= 0.6 + rnd() * 0.5      # rise
        s[0] += (rnd() - 0.5) * 1.0    # wander
        s[2] -= 1
        if s[2] > 0 and s[1] > 0:
            alive.append(s)
    sparks[:] = alive


def draw(canvas):
    """Blend the flames over the static brick + log backdrop (max = lighten)."""
    canvas.Clear()
    for y in range(ROWS):
        base_row = BASE[y]
        hrow = heat[y] if y <= SEED_Y else None
        for x in range(COLS):
            br, bg, bb = base_row[x]
            if hrow is not None:
                h = hrow[x]
                if h > 0:
                    fr, fg, fb = PALETTE[h]
                    if fr > br:
                        br = fr
                    if fg > bg:
                        bg = fg
                    if fb > bb:
                        bb = fb
            canvas.SetPixel(x, y, br, bg, bb)
    # Glowing embers pulsing along the logs near the crossing.
    rnd = random.random
    for _ in range(10):
        x = random.randint(CENTER_X - 12, CENTER_X + 12)
        y = random.randint(SEED_Y, SEED_Y + 5)
        glow = 0.45 + 0.55 * rnd()
        canvas.SetPixel(x, y, int(255 * glow), int((70 + 90 * rnd()) * glow), int(20 * glow))
    # Sparks on top.
    for s in sparks:
        f = min(1.0, s[2] / 14.0)
        canvas.SetPixel(int(s[0]), int(s[1]), int(255 * f), int(150 * f), int(40 * f))


opts = RGBMatrixOptions()
opts.rows = ROWS
opts.cols = COLS
opts.brightness = read_initial_brightness()
matrix = RGBMatrix(options=opts)
canvas = matrix.CreateFrameCanvas()

while True:
    apply_live_brightness(matrix)
    seed_fire()
    spread_fire()
    update_sparks()
    draw(canvas)
    canvas = matrix.SwapOnVSync(canvas)
    time.sleep(FRAME_SLEEP)
