"""Cozy animated fireplace for a 64x32 RGB LED matrix.

A "24-hour fireplace channel" scene framed like a real hearth: an arched brick
surround, a firelit brick back wall, a stone hearth, and a stacked pile of logs
with sawn end-grain faces. A big plume of licking flames rises off the logs,
with pulsing embers and drifting sparks.

The flames use the classic Doom fire algorithm (heat seeded at the base, cooled
and drifted as it propagates upward) mapped through a black -> ember -> gold ->
white palette, then blended over the static backdrop with a max (lighten) blend
so the fire only ever brightens the scene.

Pure SetPixel, no external assets, so it runs unchanged in the browser preview
and on the Pi.
"""

from __future__ import annotations

import math
import random
import time

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from led_brightness import apply_live_brightness, read_initial_brightness

ROWS = 32
COLS = 64

FRAME_SLEEP = 0.045  # ~22 fps

# ─── Fireplace geometry ──────────────────────────────────────────────────────
XC = 31.5              # horizontal center
OPEN_L = 6             # inner edge of the left jamb
OPEN_R = 57            # inner edge of the right jamb
ARCH_SPRING = 10       # row where the arch starts curving up from the jambs
ARCH_RISE = 9          # how far the arch rises above the spring line
HEARTH_TOP = 30        # hearth stone occupies rows HEARTH_TOP..ROWS-1
_ARCH_HALF = (OPEN_R - OPEN_L) / 2


def arch_top(x):
    """Row of the top of the firebox opening at column x (arched)."""
    dx = (x - XC) / _ARCH_HALF
    if abs(dx) >= 1:
        return ARCH_SPRING
    return ARCH_SPRING - int(round(ARCH_RISE * math.sqrt(1.0 - dx * dx)))


def in_opening(x, y):
    return OPEN_L <= x <= OPEN_R and y >= arch_top(x) and y < HEARTH_TOP


def on_arch_rim(x, y):
    """True on the 2px stone rim just inside the arched opening."""
    if not in_opening(x, y):
        return False
    return (y - arch_top(x) < 2) or (x - OPEN_L < 2) or (OPEN_R - x < 2)


# ─── Flame source ────────────────────────────────────────────────────────────
SEED_Y = 24            # flames seed just above the log pile so the base shows
FIRE_HALF = 19         # seed spans XC +/- FIRE_HALF (wide, fills the firebox)
COOL = 4               # higher = shorter flames


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
    (72, 8, 0),
    (140, 24, 0),
    (200, 52, 0),
    (238, 96, 8),
    (252, 146, 24),
    (255, 190, 56),
    (255, 224, 120),
    (255, 248, 200),
]
PALETTE = _build_palette(FIRE_STOPS, 40)
MAX_HEAT = len(PALETTE) - 1


def _clamp8(v):
    return 0 if v < 0 else (255 if v > 255 else int(v))


# ─── Brick / stone backdrop ──────────────────────────────────────────────────
BRICK_W = 12
BRICK_H = 5

SURROUND_BRICK = (52, 22, 16)   # dark outer brick surround
SURROUND_MORTAR = (14, 9, 8)
BACK_BRICK = (104, 50, 30)      # warm inner back wall (before firelight)
BACK_MORTAR = (34, 20, 15)
HEARTH_STONE = (86, 60, 48)
HEARTH_EDGE = (128, 96, 76)
HEARTH_SEAM = (30, 20, 16)
ARCH_STONE = (150, 120, 96)     # stone rim around the firebox opening
ARCH_STONE_DK = (96, 74, 58)

# Firelight glow radiating from the base of the fire.
GLOW_X, GLOW_Y = XC, 27.0


def _brick_shade(x, y, base, mortar, seed):
    """Return a brick-or-mortar color for pixel (x, y)."""
    band = y // BRICK_H
    offset = (BRICK_W // 2) if (band % 2) else 0
    xx = x + offset
    if (y % BRICK_H == 0) or (xx % BRICK_W == 0):
        return mortar
    v = 0.78 + 0.4 * (((band * 7 + (xx // BRICK_W) * 13 + seed) % 5) / 4)
    r, g, b = base
    return (int(r * v), int(g * v), int(b * v))


def build_bricks():
    """Static hearth: dark arched surround, firelit back wall, stone hearth."""
    bg = [[(0, 0, 0)] * COLS for _ in range(ROWS)]
    for y in range(ROWS):
        for x in range(COLS):
            if y >= HEARTH_TOP:
                # Stone hearth slab with a lit top lip and vertical seams.
                if y == HEARTH_TOP:
                    bg[y][x] = HEARTH_EDGE
                elif x % 16 == 0:
                    bg[y][x] = HEARTH_SEAM
                else:
                    bg[y][x] = HEARTH_STONE
            elif on_arch_rim(x, y):
                # Firelit stone rim tracing the arch and jambs.
                d = math.hypot(x - GLOW_X, (y - GLOW_Y) * 1.3)
                glow = 1.35 - d / 26.0
                glow = 0.5 if glow < 0.5 else (1.3 if glow > 1.3 else glow)
                v = 0.85 + 0.3 * (((x * 5 + y * 3) % 4) / 3)
                r, g, b = ARCH_STONE
                bg[y][x] = (_clamp8(r * v * glow), _clamp8(g * v * glow * 0.9), _clamp8(b * v * glow * 0.8))
            elif in_opening(x, y):
                r, g, b = _brick_shade(x, y, BACK_BRICK, BACK_MORTAR, 2)
                # Radial firelight: brighter near the fire base, cooling upward.
                d = math.hypot(x - GLOW_X, (y - GLOW_Y) * 1.3)
                glow = 1.5 - d / 20.0
                glow = 0.32 if glow < 0.32 else (1.5 if glow > 1.5 else glow)
                bg[y][x] = (_clamp8(r * glow), _clamp8(g * glow * 0.82), _clamp8(b * glow * 0.6))
            else:
                bg[y][x] = _brick_shade(x, y, SURROUND_BRICK, SURROUND_MORTAR, 0)
    return bg


# ─── Log pile ────────────────────────────────────────────────────────────────
LOG_BODY = (116, 66, 32)    # firelit brown body
LOG_TOP = (168, 108, 54)    # top edge catches the most firelight
LOG_DARK = (66, 36, 16)     # shaded underside
RING_OUTER = (150, 94, 50)
RING_MID = (98, 58, 30)
RING_CORE = (188, 140, 88)

# A stacked pile resting on the hearth, drawn IN FRONT of the flames so the logs
# read as firelit shapes with sawn end-grain faces and the flames rise above.
# Each log: (x0, x1, y_center, side_radius, end_side, end_radius)
LOGS = [
    (18, 46, 26, 1, +1, 2),   # top log — flames lick up from just above it
    (12, 41, 28, 1, -1, 2),   # mid-left log
    (25, 52, 28, 1, +1, 2),   # mid-right log
    (11, 53, 30, 1, 0, 0),    # front log resting across the hearth
]


def _draw_log_end(canvas, cx, cy, r):
    """Sawn end-grain face: concentric rings in tan/brown."""
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            px, py = cx + dx, cy + dy
            if not (0 <= px < COLS and 0 <= py < ROWS):
                continue
            dd = dx * dx + dy * dy
            if dd > r * r + 1:
                continue
            if dd <= 1:
                color = RING_CORE
            elif dd <= (r - 0.4) * (r - 0.4):
                color = RING_MID
            else:
                color = RING_OUTER
            canvas.SetPixel(px, py, *color)


def draw_logs(canvas):
    """Draw the log pile opaquely over the flame base."""
    for x0, x1, yc, r, end, er in LOGS:
        for x in range(x0, x1 + 1):
            for dy in range(-r, r + 1):
                y = yc + dy
                if not (0 <= x < COLS and 0 <= y < ROWS):
                    continue
                if dy <= -r:
                    canvas.SetPixel(x, y, *LOG_TOP)
                elif dy >= r:
                    canvas.SetPixel(x, y, *LOG_DARK)
                else:
                    canvas.SetPixel(x, y, *LOG_BODY)
        if end == -1:
            _draw_log_end(canvas, x0, yc, er)
        elif end == 1:
            _draw_log_end(canvas, x1, yc, er)


BASE = build_bricks()

# ─── Flame + particle state ──────────────────────────────────────────────────
heat = [[0] * COLS for _ in range(ROWS)]

# Per-column seed intensity: a broad plateau across the log pile that tapers at
# the edges, giving a wide fire base with room for licking tongues on top.
SEED_BASE = [0.0] * COLS
for _x in range(COLS):
    _d = abs(_x - XC) / FIRE_HALF
    if _d >= 1.0:
        SEED_BASE[_x] = 0.0
    else:
        SEED_BASE[_x] = 1.0 - _d ** 3 * 0.9   # flat middle, quick drop at edges

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
        if rnd() < 0.82:
            level = base * (0.78 + 0.22 * rnd())
        else:
            level = base * (0.40 + 0.25 * rnd())
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
    if rnd() < 0.5:
        x = random.randint(int(XC) - 12, int(XC) + 12)
        sparks.append([float(x), float(random.randint(12, 20)), random.randint(8, 18)])
    alive = []
    for s in sparks:
        s[1] -= 0.6 + rnd() * 0.5
        s[0] += (rnd() - 0.5) * 1.1
        s[2] -= 1
        if s[2] > 0 and s[1] > 0:
            alive.append(s)
    sparks[:] = alive


def draw(canvas):
    """Blend the flames over the static backdrop (max = lighten)."""
    canvas.Clear()
    for y in range(ROWS):
        base_row = BASE[y]
        hrow = heat[y] if y <= SEED_Y else None
        for x in range(COLS):
            br, bg, bb = base_row[x]
            if hrow is not None:
                h = hrow[x]
                if h > 0 and in_opening(x, y):
                    fr, fg, fb = PALETTE[h]
                    if fr > br:
                        br = fr
                    if fg > bg:
                        bg = fg
                    if fb > bb:
                        bb = fb
            canvas.SetPixel(x, y, br, bg, bb)
    # Log pile in front of the flames.
    draw_logs(canvas)
    # A few pulsing embers glowing in the gaps of the log pile.
    rnd = random.random
    for _ in range(6):
        x = random.randint(int(XC) - 13, int(XC) + 13)
        y = random.randint(SEED_Y + 3, HEARTH_TOP - 1)
        glow = 0.5 + 0.5 * rnd()
        canvas.SetPixel(x, y, _clamp8(255 * glow), _clamp8((60 + 80 * rnd()) * glow), _clamp8(14 * glow))
    # Sparks on top.
    for s in sparks:
        f = min(1.0, s[2] / 16.0)
        canvas.SetPixel(int(s[0]), int(s[1]), _clamp8(255 * f), _clamp8(150 * f), _clamp8(40 * f))


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
