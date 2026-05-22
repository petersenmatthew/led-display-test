"""
Waterloo, Ontario live weather display.

Pulls current conditions from Open-Meteo (no API key required) for
lat=43.4643, lon=-80.5204, picks the matching animated scene, and shows
the live temperature + condition label in the top-left corner.

For a scene-by-scene visual test that does not require network, run
weather-test.py instead.
"""

import os
import time
import math
import random
import json
import datetime as dt
import urllib.request
import urllib.error
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")

# Load font before creating RGBMatrix — the matrix constructor drops root
# privileges to user "daemon", which can't read files inside /home/pi.
font = graphics.Font()
font.LoadFont(os.path.join(FONT_DIR, "4x6.bdf"))

opts = RGBMatrixOptions()
opts.rows = 32
opts.cols = 64
matrix = RGBMatrix(options=opts)
canvas = matrix.CreateFrameCanvas()

W, H = 64, 32

# ─── pixel helpers ──────────────────────────────────────────────────────────

def px(c, x, y, col):
    if 0 <= x < W and 0 <= y < H:
        c.SetPixel(x, y, col[0], col[1], col[2])

def rect(c, x0, y0, x1, y1, col):
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            px(c, x, y, col)

def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))

def vgrad(c, x0, x1, y0, y1, top, bot):
    span = max(1, y1 - y0)
    for y in range(y0, y1 + 1):
        col = lerp(top, bot, (y - y0) / span)
        for x in range(x0, x1 + 1):
            px(c, x, y, col)

def disc(c, cx, cy, r, col):
    r2 = r * r
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r2:
                px(c, cx + dx, cy + dy, col)

# ─── scenes ─────────────────────────────────────────────────────────────────

def draw_sunny(c, f):
    # Sky: warm blue gradient
    vgrad(c, 0, 63, 0, 21, (90, 165, 240), (185, 220, 245))

    # Sun (top-right area), with rotating rays
    sx, sy = 52, 8
    rot = (f * 3) % 360
    for k in range(8):
        ang = math.radians(rot + k * 45)
        for d in (6, 7, 8):
            x = int(sx + d * math.cos(ang))
            y = int(sy + d * math.sin(ang))
            px(c, x, y, (255, 210, 70))
    disc(c, sx, sy, 4, (255, 200, 60))
    disc(c, sx, sy, 3, (255, 230, 110))
    disc(c, sx, sy, 2, (255, 250, 180))
    px(c, sx - 1, sy - 1, (255, 255, 230))

    # Far hills (lighter green, parallax)
    for x in range(W):
        hy = int(20 + 1.5 * math.sin(x * 0.13))
        for y in range(hy, 24):
            px(c, x, y, (110, 175, 90))

    # Front hills (darker, rolling)
    for x in range(W):
        hy = int(23 + 2.0 * math.sin(x * 0.18 + 1.3))
        for y in range(hy, H):
            px(c, x, y, (70, 145, 55))
    # Grass tufts — sparse, only outside the building footprint
    for x in range(24, W, 7):
        y = 24 + ((x * 7) % 3)
        px(c, x, y, (150, 210, 90))
        px(c, x, y + 1, (95, 160, 65))

    # Easter egg: Claudette Millar Hall (UW residence)
    draw_cmh(c, f)


def draw_cloudy(c, f):
    # Overcast sky
    vgrad(c, 0, 63, 0, 21, (140, 155, 175), (200, 205, 215))

    # Drifting clouds — 3 layers, different speeds
    def cloud(cx, cy, scale, col_light, col_dark):
        # blob made of overlapping discs
        disc(c, cx,         cy,     2 + scale, col_dark)
        disc(c, cx + 3,     cy - 1, 2 + scale, col_dark)
        disc(c, cx - 3,     cy,     1 + scale, col_dark)
        disc(c, cx,         cy - 1, 2 + scale, col_light)
        disc(c, cx + 2,     cy - 2, 1 + scale, col_light)

    speeds = [(0.20, 6,  0, (235, 235, 240), (170, 175, 190)),
              (0.12, 14, 1, (215, 220, 230), (150, 160, 175)),
              (0.30, 30, 2, (245, 245, 250), (180, 185, 200))]
    for spd, base_x, scale, lt, dk in speeds:
        cx = (base_x + int(f * spd)) % (W + 20) - 10
        cy = 5 + scale
        cloud(cx, cy, scale, lt, dk)

    # Muted hills
    for x in range(W):
        hy = int(22 + 1.5 * math.sin(x * 0.16))
        for y in range(hy, 25):
            px(c, x, y, (95, 130, 90))
        for y in range(25, H):
            px(c, x, y, (70, 100, 70))
    # Subtle grass dither
    for x in range(0, W, 4):
        y = 26 + ((x * 5) % 3)
        px(c, x, y, (115, 145, 100))

    # Easter egg: Canada geese in V-formation
    draw_geese_v(c, f)


def draw_rainy(c, f):
    # Dark stormy sky
    vgrad(c, 0, 63, 0, 21, (55, 65, 85), (95, 105, 125))

    # Heavy clouds across top
    for cx in (8, 24, 40, 56):
        offset = int(math.sin((f + cx * 4) * 0.05) * 1)
        disc(c, cx, 4 + offset, 3, (70, 75, 95))
        disc(c, cx + 4, 3 + offset, 2, (55, 60, 80))
        disc(c, cx - 3, 5 + offset, 2, (85, 90, 110))
    for x in range(W):
        for y in range(0, 4):
            if (x * 3 + y * 7) % 9 == 0:
                px(c, x, y, (45, 50, 70))

    # Occasional lightning flash
    if (f // 7) % 23 == 0:
        rect(c, 0, 0, 63, 21, (220, 220, 255))

    # Rain streaks (animated, denser)
    random.seed(0)
    drops = []
    for i in range(45):
        drops.append((random.randint(0, 63), random.randint(0, 28),
                      random.choice([1, 1, 2])))
    for x0, y0, length in drops:
        y = (y0 + f) % 28
        for k in range(length):
            yy = y + k
            xx = x0 - (k // 2)
            if 0 <= yy < 22:
                px(c, xx, yy, (160, 200, 240))
            elif yy < 24:
                px(c, xx, yy, (200, 230, 255))

    # Wet ground (darker, reflective)
    for x in range(W):
        for y in range(22, H):
            base = (35, 65, 60) if y < 26 else (25, 50, 45)
            px(c, x, y, base)
    # Puddles with ripples
    for puddle_x in (10, 32, 50):
        for dx in range(-3, 4):
            px(c, puddle_x + dx, 29, (75, 110, 130))
        ripple = (f // 4) % 6
        if ripple < 3:
            px(c, puddle_x - 2 + ripple, 28, (130, 170, 200))
            px(c, puddle_x + 2 - ripple, 28, (130, 170, 200))


def draw_snowy(c, f):
    # Pale winter sky
    vgrad(c, 0, 63, 0, 21, (175, 195, 220), (225, 230, 240))

    # Distant snow-capped hills
    for x in range(W):
        hy = int(18 + 2.5 * math.sin(x * 0.10))
        for y in range(hy, 22):
            px(c, x, y, (190, 200, 215))
        # Cap highlight
        px(c, x, hy, (245, 250, 255))

    # Bare tree silhouette (right side)
    tx = 48
    rect(c, tx, 18, tx, 27, (50, 40, 35))
    # branches
    for bx, by in [(tx - 1, 19), (tx + 1, 20), (tx - 2, 21),
                   (tx + 2, 22), (tx - 1, 23)]:
        px(c, bx, by, (50, 40, 35))

    # Snow ground
    for x in range(W):
        ground = int(22 + 1.5 * math.sin(x * 0.20 + 0.5))
        for y in range(ground, H):
            shade = (240, 245, 252) if y == ground else (220, 228, 240)
            px(c, x, y, shade)
    # Snow speckles on ground
    for x in range(0, W, 5):
        y = 26 + ((x * 3) % 4)
        px(c, x, y, (255, 255, 255))

    # Falling snowflakes (slow drift)
    random.seed(2)
    flakes = [(random.randint(0, 63), random.randint(0, 21),
               random.uniform(0.15, 0.55)) for _ in range(30)]
    for fx, fy, speed in flakes:
        y = int(fy + f * speed) % 22
        x = int(fx + 2 * math.sin((f * speed + fy) * 0.15))
        col = (255, 255, 255) if speed > 0.35 else (220, 230, 245)
        px(c, x, y, col)


def draw_night(c, f):
    # Deep night sky
    vgrad(c, 0, 63, 0, 22, (8, 12, 35), (35, 30, 70))

    # Stars (twinkle)
    random.seed(7)
    stars = [(random.randint(0, 63), random.randint(0, 18),
              random.randint(0, 99)) for _ in range(40)]
    for sx, sy, phase in stars:
        b = 140 + int(80 * math.sin((f + phase) * 0.12))
        b = max(60, min(255, b))
        px(c, sx, sy, (b, b, max(120, b - 30)))
    # A couple of bright stars
    for sx, sy in [(10, 5), (45, 3), (30, 9), (58, 11)]:
        px(c, sx, sy, (255, 255, 230))
        px(c, sx + 1, sy, (180, 180, 160))
        px(c, sx, sy + 1, (180, 180, 160))

    # Crescent moon
    mx, my = 16, 8
    disc(c, mx, my, 4, (240, 235, 200))
    disc(c, mx + 2, my - 1, 4, (8, 12, 35))  # subtract for crescent

    # Distant tree-lined horizon
    for x in range(W):
        h = 21 + ((int(2 * math.sin(x * 0.5)) + int(3 * math.sin(x * 0.13))) // 2)
        for y in range(h, 23):
            px(c, x, y, (10, 20, 25))

    # Ground (dark with faint moon-reflected snow / grass)
    for x in range(W):
        for y in range(23, H):
            t = (y - 23) / 8
            col = lerp((25, 35, 55), (10, 15, 30), t)
            px(c, x, y, col)
    # Snow patches (moonlit)
    for x in range(0, W, 4):
        y = 24 + ((x * 5) % 4)
        px(c, x, y, (90, 100, 130))

    # Easter egg: E7 (UW engineering building)
    draw_e7(c, f, 34, 10)


# ─── Easter eggs: Waterloo landmarks ───────────────────────────────────────

def draw_goose(c, x, y, flap):
    """One tiny Canada goose, 3px wide. `flap` toggles wing position."""
    body = (35, 30, 28)
    head = (12, 10, 10)
    cheek = (235, 235, 230)  # white chinstrap hint (only visible on bigger lead)
    if flap == 0:
        # Wings up — V shape
        px(c, x - 1, y, body)
        px(c, x + 1, y, body)
        px(c, x,     y + 1, body)
    else:
        # Wings level — flat with belly hanging
        px(c, x - 1, y + 1, body)
        px(c, x,     y,     body)
        px(c, x + 1, y + 1, body)
    # Neck/head poking forward (flight direction = right)
    px(c, x + 2, y + 1, head)
    return cheek  # unused; kept so future tweaks can highlight the lead


def draw_geese_v(c, f):
    """A small V-formation drifting left-to-right across the sky."""
    # Leader slowly traverses, wrapping past the right edge
    base_x = (f // 2) % 90 - 14
    base_y = 12
    # Offsets from leader (leader = front-right of the V)
    flock = [
        (0,  0),                 # leader
        (-3, -1), (-3, 1),       # 2nd pair
        (-6, -2), (-6, 2),       # 3rd pair
        (-9, -3),                # straggler
    ]
    for i, (dx, dy) in enumerate(flock):
        flap = ((f + i * 3) // 5) % 2
        draw_goose(c, base_x + dx, base_y + dy, flap)


def draw_cmh(c, f):
    """Claudette Millar Hall (UW residence): plain rectangle with beige
    flanks, a darker brown center, and 4 tall window columns."""
    BEIGE  = (215, 200, 175)
    BROWN  = (110, 70, 45)
    WINDOW = (40, 50, 70)

    x0, x1 = 4, 21      # 18 wide
    y0, y1 = 6, 24      # 19 tall

    # Beige flanks (left + right, 4 px wide each)
    rect(c, x0,     y0, x0 + 3, y1, BEIGE)
    rect(c, x1 - 3, y0, x1,     y1, BEIGE)
    # Dark brown center
    rect(c, x0 + 4, y0, x1 - 4, y1, BROWN)

    # 4 vertical window columns, evenly spaced across the building
    for wx in (7, 11, 14, 18):
        for wy in range(y0 + 2, y1 - 1):
            px(c, wx, wy, WINDOW)


def draw_e7(c, f, x0, y0):
    """E7 — UW's Engineering 7 building. Rectangular tower with a chevron-
    patterned facade, lit windows, and a skybridge running off to the left."""
    bw, bh = 18, 13
    x1 = x0 + bw - 1
    y1 = y0 + bh - 1

    # Concrete silhouette
    rect(c, x0, y0, x1, y1, (55, 52, 68))

    # Chevron / diamond facade — alternating light/dark to suggest the
    # panelled exterior. Skip the outer 1px frame.
    for y in range(y0 + 1, y1):
        for x in range(x0 + 1, x1):
            if (x + y) % 2 == 0:
                px(c, x, y, (92, 88, 108))
            else:
                px(c, x, y, (68, 64, 82))

    # Vertical edges a touch brighter (corner highlight under moonlight)
    for y in range(y0, y1 + 1):
        px(c, x0, y, (78, 74, 92))
    # Roofline highlight
    for x in range(x0, x1 + 1):
        px(c, x, y0, (110, 105, 128))

    # Lit windows (warm yellow). A few flicker on a slow cycle.
    lit = [
        (x0 + 3,  y0 + 3), (x0 + 9,  y0 + 3), (x0 + 14, y0 + 3),
        (x0 + 5,  y0 + 5), (x0 + 11, y0 + 5),
        (x0 + 3,  y0 + 7), (x0 + 7,  y0 + 7), (x0 + 13, y0 + 7),
        (x0 + 5,  y0 + 9), (x0 + 9,  y0 + 9), (x0 + 15, y0 + 9),
        (x0 + 7,  y0 + 11), (x0 + 11, y0 + 11),
    ]
    for i, (wx, wy) in enumerate(lit):
        flicker = (f + i * 13) % 90
        if flicker < 4:
            continue  # blink off briefly
        if flicker < 8:
            px(c, wx, wy, (180, 130, 50))  # dim
        else:
            px(c, wx, wy, (255, 210, 110))

    # Glass skybridge running off-screen to the left
    bridge_y = y0 + 8
    for bx in range(x0 - 8, x0):
        px(c, bx, bridge_y,     (120, 150, 195))
        px(c, bx, bridge_y + 1, (70,  90,  130))
    # Support pylon at the far end
    for y in range(bridge_y + 2, y1 + 1):
        px(c, x0 - 7, y, (50, 45, 60))


# ─── HUD: temperature + condition in top-left corner ───────────────────────

def draw_label(c, text):
    """Dim pill behind text so it reads over any sky color."""
    text_w = len(text) * 4
    pad = 1
    rect(c, 0, 0, text_w + pad + 1, 7, (15, 15, 25))
    # Faint highlight on top edge
    for x in range(0, text_w + pad + 2):
        if x < W:
            r, g, b = 35, 35, 50
            c.SetPixel(x, 0, r, g, b)
    color = graphics.Color(255, 230, 140)
    graphics.DrawText(c, font, pad, 6, color, text)


# ─── composable weather renderer ───────────────────────────────────────────

PHASE_DAY = "day"
PHASE_SUNRISE = "sunrise"
PHASE_SUNSET = "sunset"
PHASE_NIGHT = "night"
TWILIGHT_WINDOW = dt.timedelta(minutes=45)

COND_CLEAR = "clear"
COND_CLOUDY = "cloudy"
COND_RAIN = "rain"
COND_DRIZZLE = "drizzle"
COND_SNOW = "snow"
COND_STORM = "storm"

CLOUD_NONE = "none"
CLOUD_PARTIAL = "partial"
CLOUD_OVERCAST = "overcast"


def draw_phase_sky(c, phase, condition, clouds):
    stormy = condition in (COND_RAIN, COND_DRIZZLE, COND_STORM)
    snowy = condition == COND_SNOW
    cloudy = clouds == CLOUD_OVERCAST or condition == COND_CLOUDY

    if phase == PHASE_NIGHT:
        top, bot = (5, 9, 32), (24, 22, 52)
    elif phase == PHASE_SUNRISE:
        top, bot = ((28, 45, 84), (238, 150, 94))
        if stormy:
            top, bot = (35, 42, 70), (132, 92, 94)
        elif snowy:
            top, bot = (72, 92, 130), (242, 176, 140)
    elif phase == PHASE_SUNSET:
        top, bot = ((54, 42, 92), (238, 116, 68))
        if stormy:
            top, bot = (38, 43, 70), (104, 70, 90)
        elif snowy:
            top, bot = (72, 68, 120), (232, 142, 124)
    elif stormy:
        top, bot = (55, 65, 85), (95, 105, 125)
    elif snowy:
        top, bot = (175, 195, 220), (225, 230, 240)
    elif cloudy:
        top, bot = (140, 155, 175), (200, 205, 215)
    else:
        top, bot = (90, 165, 240), (185, 220, 245)
    vgrad(c, 0, 63, 0, 21, top, bot)


def draw_phase_land(c, phase, condition, f):
    snowy = condition == COND_SNOW
    wet = condition in (COND_RAIN, COND_DRIZZLE, COND_STORM)

    if phase == PHASE_NIGHT:
        for x in range(W):
            h = 21 + (
                (int(2 * math.sin(x * 0.5)) + int(3 * math.sin(x * 0.13))) // 2
            )
            for y in range(h, 23):
                px(c, x, y, (10, 20, 25))
            for y in range(23, H):
                t = (y - 23) / 8
                px(c, x, y, lerp((25, 35, 55), (10, 15, 30), t))
        draw_e7(c, f, 34, 10)
        return

    if snowy:
        for x in range(W):
            ground = int(22 + 1.5 * math.sin(x * 0.20 + 0.5))
            for y in range(ground, H):
                shade = (240, 245, 252) if y == ground else (220, 228, 240)
                if phase == PHASE_SUNRISE:
                    shade = lerp(shade, (255, 200, 172), 0.18)
                elif phase == PHASE_SUNSET:
                    shade = lerp(shade, (235, 165, 170), 0.22)
                px(c, x, y, shade)
        draw_cmh(c, f)
        return

    for x in range(W):
        hy = int(22 + 1.5 * math.sin(x * 0.16))
        far = (95, 130, 90) if wet else (110, 175, 90)
        near = (35, 65, 60) if wet else (70, 145, 55)
        if phase == PHASE_SUNRISE:
            far = lerp(far, (180, 130, 85), 0.22)
            near = lerp(near, (120, 85, 55), 0.16)
        elif phase == PHASE_SUNSET:
            far = lerp(far, (170, 100, 85), 0.28)
            near = lerp(near, (95, 60, 70), 0.22)
        for y in range(hy, 25):
            px(c, x, y, far)
        for y in range(25, H):
            px(c, x, y, near)

    if wet:
        for puddle_x in (10, 32, 50):
            for dx in range(-3, 4):
                px(c, puddle_x + dx, 29, (75, 110, 130))
            ripple = (f // 4) % 6
            if ripple < 3:
                px(c, puddle_x - 2 + ripple, 28, (130, 170, 200))
                px(c, puddle_x + 2 - ripple, 28, (130, 170, 200))
    draw_cmh(c, f)


def draw_phase_sun(c, phase, f):
    if phase == PHASE_NIGHT:
        return
    if phase == PHASE_SUNRISE:
        sx, sy = 34, 23
        core = (255, 198, 92)
    elif phase == PHASE_SUNSET:
        sx, sy = 50, 24
        core = (255, 150, 72)
    else:
        sx, sy = 52, 8
        core = (255, 200, 60)

    if phase in (PHASE_SUNRISE, PHASE_SUNSET):
        disc(c, sx, sy, 4, core)
        disc(c, sx, sy, 3, (255, 230, 110))
        return

    rot = (f * 3) % 360
    for k in range(8):
        ang = math.radians(rot + k * 45)
        for d in (5, 6, 7):
            px(c, int(sx + d * math.cos(ang)), int(sy + d * math.sin(ang)), core)
    disc(c, sx, sy, 4, core)
    disc(c, sx, sy, 3, (255, 230, 110))
    px(c, sx - 1, sy - 1, (255, 255, 220))


def draw_phase_clouds(c, phase, condition, clouds, f):
    stormy = condition in (COND_RAIN, COND_DRIZZLE, COND_STORM)
    if clouds == CLOUD_NONE and not stormy and condition != COND_CLOUDY:
        return

    if phase == PHASE_NIGHT:
        light, dark = (75, 82, 110), (42, 48, 74)
    elif condition == COND_STORM or clouds == CLOUD_OVERCAST:
        light, dark = (95, 95, 120), (48, 52, 76)
    elif phase == PHASE_SUNRISE:
        light, dark = (228, 180, 168), (132, 100, 122)
    elif phase == PHASE_SUNSET:
        light, dark = (226, 142, 148), (104, 80, 130)
    else:
        light, dark = (225, 230, 238), (150, 160, 175)

    cloud_centers = (12, 48) if clouds == CLOUD_PARTIAL and not stormy else (8, 24, 40, 56)
    if clouds == CLOUD_OVERCAST and not stormy:
        cloud_centers = (4, 16, 28, 40, 52, 62)

    for cx in cloud_centers:
        offset = int(math.sin((f + cx * 4) * 0.05) * 1)
        disc(c, cx, 4 + offset, 3, dark)
        disc(c, cx + 4, 3 + offset, 2, dark)
        disc(c, cx - 3, 5 + offset, 2, light)


def draw_phase_night_details(c, f):
    random.seed(7)
    stars = [
        (random.randint(0, 63), random.randint(0, 18), random.randint(0, 99))
        for _ in range(40)
    ]
    for sx, sy, phase in stars:
        b = 140 + int(80 * math.sin((f + phase) * 0.12))
        b = max(60, min(255, b))
        px(c, sx, sy, (b, b, max(120, b - 30)))
    disc(c, 16, 8, 4, (240, 235, 200))
    disc(c, 18, 7, 4, (5, 9, 32))


def draw_live_rain(c, f, density):
    random.seed(0)
    for _ in range(density):
        x0 = random.randint(0, 63)
        y0 = random.randint(0, 28)
        length = random.choice((1, 2, 3))
        y = (y0 + f) % 28
        for k in range(length):
            yy = y + k
            if yy < 24:
                px(c, x0 - (k // 2), yy, (150, 205, 245))


def draw_live_snow(c, f):
    random.seed(2)
    flakes = [
        (random.randint(0, 63), random.randint(0, 21), random.uniform(0.15, 0.55))
        for _ in range(30)
    ]
    for fx, fy, speed in flakes:
        y = int(fy + f * speed) % 22
        x = int(fx + 2 * math.sin((f * speed + fy) * 0.15))
        px(c, x, y, (245, 250, 255))


def draw_condition_scene(c, f, condition, phase, clouds):
    draw_phase_sky(c, phase, condition, clouds)
    if (
        (condition == COND_CLEAR or phase in (PHASE_SUNRISE, PHASE_SUNSET))
        and clouds != CLOUD_OVERCAST
    ):
        draw_phase_sun(c, phase, f)
    draw_phase_land(c, phase, condition, f)
    draw_phase_clouds(c, phase, condition, clouds, f)

    if condition == COND_CLEAR:
        if phase in (PHASE_DAY, PHASE_SUNRISE, PHASE_SUNSET):
            draw_geese_v(c, f)
    elif condition == COND_DRIZZLE:
        draw_live_rain(c, f, 20)
    elif condition == COND_RAIN:
        draw_live_rain(c, f, 45)
    elif condition == COND_STORM:
        if (f // 7) % 23 == 0:
            rect(c, 0, 0, 63, 21, (220, 220, 255))
        draw_live_rain(c, f, 55)
    elif condition == COND_SNOW:
        draw_live_snow(c, f)

    if phase == PHASE_NIGHT:
        draw_phase_night_details(c, f)


# ─── live weather fetch (Open-Meteo) ───────────────────────────────────────

LAT, LON = 43.4643, -80.5204  # Waterloo, Ontario
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&current=temperature_2m,weather_code,is_day"
    "&daily=sunrise,sunset"
    "&forecast_days=1"
    "&timezone=auto"
).format(lat=LAT, lon=LON)

REFRESH_SECONDS = 600  # pull new conditions every 10 minutes
HTTP_TIMEOUT = 10

def parse_open_meteo_time(value):
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    if not isinstance(value, str):
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return dt.datetime.fromisoformat(value)


def classify_phase(current_time, sunrise, sunset, is_day):
    now = parse_open_meteo_time(current_time)
    sunrise_time = parse_open_meteo_time(sunrise)
    sunset_time = parse_open_meteo_time(sunset)

    if now is None:
        now = dt.datetime.now()
    if any(
        value is not None and (value.tzinfo is None) != (now.tzinfo is None)
        for value in (sunrise_time, sunset_time)
    ):
        now = now.replace(tzinfo=None)
        if sunrise_time is not None:
            sunrise_time = sunrise_time.replace(tzinfo=None)
        if sunset_time is not None:
            sunset_time = sunset_time.replace(tzinfo=None)
    if sunrise_time is not None and abs(now - sunrise_time) <= TWILIGHT_WINDOW:
        return PHASE_SUNRISE
    if sunset_time is not None and abs(now - sunset_time) <= TWILIGHT_WINDOW:
        return PHASE_SUNSET
    return PHASE_DAY if is_day else PHASE_NIGHT


# WMO weather codes → (short label, condition effect).
def classify_condition(weather_code):
    c = weather_code
    if c in (0,):
        return ("CLR", COND_CLEAR, CLOUD_NONE)
    if c in (1, 2):
        return ("PCLD", COND_CLEAR, CLOUD_PARTIAL)
    if c in (3,):
        return ("CLD", COND_CLEAR, CLOUD_OVERCAST)
    if c in (45, 48):
        return ("FOG", COND_CLOUDY, CLOUD_OVERCAST)
    if c in (51, 53, 55, 56, 57):
        return ("DRZL", COND_DRIZZLE, CLOUD_OVERCAST)
    if c in (61, 63, 65, 66, 67, 80, 81, 82):
        return ("RAIN", COND_RAIN, CLOUD_OVERCAST)
    if c in (71, 73, 75, 77, 85, 86):
        return ("SNOW", COND_SNOW, CLOUD_OVERCAST)
    if c in (95, 96, 99):
        return ("STRM", COND_STORM, CLOUD_OVERCAST)
    return ("?", COND_CLOUDY, CLOUD_OVERCAST)


def fetch_weather():
    """Return a current weather dict or None on failure."""
    try:
        with urllib.request.urlopen(WEATHER_URL, timeout=HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        cur = data["current"]
        daily = data.get("daily", {})
        return {
            "temp_c": int(round(cur["temperature_2m"])),
            "weather_code": int(cur["weather_code"]),
            "is_day": bool(cur["is_day"]),
            "current_time": cur.get("time"),
            "sunrise": daily.get("sunrise", [None])[0],
            "sunset": daily.get("sunset", [None])[0],
        }
    except (urllib.error.URLError, ValueError, KeyError, TypeError, OSError):
        return None


def make_label(temp_c, cond):
    return "{:d}\xb0C {}".format(temp_c, cond)


def make_render_state(reading):
    cond_label, condition, clouds = classify_condition(reading["weather_code"])
    phase = classify_phase(
        reading.get("current_time"),
        reading.get("sunrise"),
        reading.get("sunset"),
        reading.get("is_day"),
    )
    return make_label(reading["temp_c"], cond_label), condition, phase, clouds


# ─── main loop ─────────────────────────────────────────────────────────────

current = fetch_weather()
if current is None:
    # No network yet — fall back to a neutral overcast scene until next try.
    label = "-- NET"
    condition = COND_CLOUDY
    phase = PHASE_DAY
    clouds = CLOUD_OVERCAST
else:
    label, condition, phase, clouds = make_render_state(current)

last_fetch = time.time()
frame = 0

while True:
    canvas.Clear()
    draw_condition_scene(canvas, frame, condition, phase, clouds)
    draw_label(canvas, label)
    canvas = matrix.SwapOnVSync(canvas)

    frame += 1
    if time.time() - last_fetch >= REFRESH_SECONDS:
        result = fetch_weather()
        last_fetch = time.time()
        if result is not None:
            label, condition, phase, clouds = make_render_state(result)
        # On failure, keep showing the last good reading.

    time.sleep(0.05)
