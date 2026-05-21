import os
import time
import math
from rgbmatrix import RGBMatrix, RGBMatrixOptions, FrameCanvas, graphics

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")

opts = RGBMatrixOptions()
opts.rows = 32
opts.cols = 64
matrix = RGBMatrix(options=opts)
offscreen = matrix.CreateFrameCanvas()

# Ticket nearly fills the screen
TW = 62
TH = 30
TY = 1
CENTER_X = 32

# Geometry
PERF = 53        # perforation column
STUB_X0 = 55     # ADMIT ONE stub starts here
STUB_X1 = 60     # stub ends here

# Use a big, bold font for the name so it's clearly legible
fname = graphics.Font()
fname.LoadFont(os.path.join(FONT_DIR, "6x10.bdf"))

# Ink color (warm dark brown - matches reference ticket text)
INK = (38, 16, 4)
INK_C = graphics.Color(*INK)

# ---------- BACKGROUND ----------
def ticket_bg(x, y, mirror=False):
    """Warm orange ticket bg with one bright specular blob (matches reference)."""
    xx = (TW - 1 - x) if mirror else x
    hx, hy = 40, 13
    dh = math.sqrt((xx - hx) ** 2 + ((y - hy) * 1.6) ** 2)
    if dh < 4:
        t = 1.0 - dh / 4.0
        r = 255
        g = int(195 + t * 45)
        b = int(120 + t * 70)
    elif dh < 10:
        t = (10 - dh) / 6.0
        r = 255
        g = int(150 + t * 45)
        b = int(65 + t * 55)
    elif dh < 18:
        t = (18 - dh) / 8.0
        r = int(238 + t * 17)
        g = int(115 + t * 35)
        b = int(40 + t * 25)
    else:
        r, g, b = 215, 88, 28
    de = min(xx, TW - 1 - xx, y, TH - 1 - y)
    if de <= 1:
        f = 0.55 + de * 0.18
        r = int(r * f); g = int(g * f); b = int(b * f)
    return (r, g, b)

# ---------- HELPERS ----------

def fill_bg(canvas, mirror=False):
    for y in range(TH):
        for x in range(TW):
            r, g, b = ticket_bg(x, y, mirror=mirror)
            canvas.SetPixel(x, y, r, g, b)

def bar(canvas, x0, x1, y0, y1):
    """Solid black bar (representative of text). Skips the perforation column."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if 0 <= x < TW and 0 <= y < TH and x != PERF:
                canvas.SetPixel(x, y, INK[0], INK[1], INK[2])

def corner_notches(canvas):
    for cx, cy in [(0, 0), (TW - 1, 0), (0, TH - 1), (TW - 1, TH - 1)]:
        canvas.SetPixel(cx, cy, 0, 0, 0)

def perforation(canvas):
    # Top + bottom notches
    canvas.SetPixel(PERF, 0, 0, 0, 0)
    canvas.SetPixel(PERF - 1, 0, 0, 0, 0)
    canvas.SetPixel(PERF + 1, 0, 0, 0, 0)
    canvas.SetPixel(PERF, 1, 0, 0, 0)
    canvas.SetPixel(PERF, TH - 1, 0, 0, 0)
    canvas.SetPixel(PERF - 1, TH - 1, 0, 0, 0)
    canvas.SetPixel(PERF + 1, TH - 1, 0, 0, 0)
    canvas.SetPixel(PERF, TH - 2, 0, 0, 0)
    for yy in range(3, TH - 3, 2):
        canvas.SetPixel(PERF, yy, 0, 0, 0)

# ---------- FRONT FACE ----------
front_canvas = FrameCanvas(TW, TH)
fill_bg(front_canvas)
corner_notches(front_canvas)
perforation(front_canvas)

# Top placeholder bars (representing "Y COMBINATOR PRESENTS / STARTUP SCHOOL 2026")
# Line 1
bar(front_canvas, 3, 6,  3, 4)    # "Y COMBINATOR" word 1
bar(front_canvas, 8, 22, 3, 4)    # word 2
# Line 2
bar(front_canvas, 3, 13, 6, 7)    # "STARTUP"
bar(front_canvas, 15, 23, 6, 7)   # "SCHOOL"
bar(front_canvas, 25, 32, 6, 7)   # "2026"

# === THE NAME — biggest, clearest element ===
# 6x10 advance width = 6 per char. "JUSTIN WU" = 9 chars * 6 = 54 px.
# Main body is x=0..52 (53 wide). 54 > 53 by 1 — fudge by drawing at x=-1 and
# clipping, or use 5x8. Use 5x8 for a clean fit with margin.
fname_small = graphics.Font()
fname_small.LoadFont(os.path.join(FONT_DIR, "5x8.bdf"))
# "JUSTIN WU" with 5x8 = 9 * 5 = 45 px wide. Center in main body (53 wide).
name = "JUSTIN WU"
name_width = 5 * len(name)
name_x = max(0, (PERF - name_width) // 2)
# Baseline y so that 8-tall text vertically centers around y=17
graphics.DrawText(front_canvas, fname_small, name_x, 18, INK_C, name)
# Make the name BOLD by drawing a second pass shifted 1px right
graphics.DrawText(front_canvas, fname_small, name_x + 1, 18, INK_C, name)

# Bottom placeholder bars (representing "CHASE CENTER, SF · JULY 25-26")
# Line 1
bar(front_canvas, 3, 11, 23, 24)   # "CHASE"
bar(front_canvas, 13, 22, 23, 24)  # "CENTER,"
bar(front_canvas, 24, 28, 23, 24)  # "SF"
# Line 2
bar(front_canvas, 3, 9, 26, 27)    # "JULY"
bar(front_canvas, 11, 21, 26, 27)  # "25-26"

# Stub: vertical stack of small bars to represent "ADMIT ONE"
stub_bars_y = [(3, 4), (6, 7), (9, 10), (12, 13), (15, 16),
               (19, 20), (22, 23), (25, 26)]
for y0, y1 in stub_bars_y:
    bar(front_canvas, STUB_X0, STUB_X1, y0, y1)

# ---------- BACK FACE ----------
back_canvas = FrameCanvas(TW, TH)
fill_bg(back_canvas, mirror=True)
corner_notches(back_canvas)
perforation(back_canvas)

# Back side: same stylized layout but flipped feel — Y COMBINATOR stamp
# Big "YC" centered
fyc = graphics.Font()
fyc.LoadFont(os.path.join(FONT_DIR, "7x13.bdf"))
# "YC" = 2 chars * 7 = 14 px
yc_x = (PERF - 14) // 2
graphics.DrawText(back_canvas, fyc, yc_x, 19, INK_C, "YC")
graphics.DrawText(back_canvas, fyc, yc_x + 1, 19, INK_C, "YC")  # bold

# Decorative bars top + bottom on back
bar(back_canvas, 3, 25, 4, 5)
bar(back_canvas, 27, 38, 4, 5)
bar(back_canvas, 3, 12, 25, 26)
bar(back_canvas, 14, 28, 25, 26)
bar(back_canvas, 30, 38, 25, 26)

# Mirror the stub pattern on back
for y0, y1 in stub_bars_y:
    bar(back_canvas, STUB_X0, STUB_X1, y0, y1)

# Snapshot to bytes for fast lookup during rotation
front_buf = bytes(front_canvas.buf)
back_buf = bytes(back_canvas.buf)

# ---------- ROTATION ----------
angle = 0.0
ANGLE_STEP = 0.045

while True:
    offscreen.Clear()
    cos_t = math.cos(angle)
    abs_cos = abs(cos_t)
    half_w = TW / 2.0

    if abs_cos > 0.025:
        src = front_buf if cos_t > 0 else back_buf
        bright = 0.5 + 0.5 * abs_cos
        spec_center = CENTER_X + int(11 * math.sin(angle))

        for sx in range(64):
            u = (sx + 0.5 - CENTER_X) / cos_t
            c_raw = u + half_w - 0.5
            c = int(round(c_raw))
            if c < 0 or c >= TW:
                continue
            src_col = (TW - 1 - c) if cos_t < 0 else c

            edge_t = abs(c_raw - (TW - 1) / 2.0) / ((TW - 1) / 2.0)
            col_shade = 1.0 - 0.18 * edge_t * (1.0 - abs_cos)

            dx_spec = sx - spec_center
            spec_boost = max(0.0, 1.0 - (dx_spec * dx_spec) / 28.0) * 0.30 * abs_cos

            for sy in range(TH):
                i = (sy * TW + src_col) * 3
                r = src[i]; g = src[i + 1]; b = src[i + 2]
                if r == 0 and g == 0 and b == 0:
                    continue
                m = bright * col_shade
                r = min(255, int(r * m + r * spec_boost))
                g = min(255, int(g * m + g * spec_boost))
                b = min(255, int(b * m + b * spec_boost))
                offscreen.SetPixel(sx, TY + sy, r, g, b)
    else:
        for sy in range(2, TH - 2):
            offscreen.SetPixel(CENTER_X, TY + sy, 180, 75, 25)
        offscreen.SetPixel(CENTER_X, TY + 1, 90, 40, 15)
        offscreen.SetPixel(CENTER_X, TY + TH - 2, 90, 40, 15)

    offscreen = matrix.SwapOnVSync(offscreen)
    angle += ANGLE_STEP
    if angle > 2 * math.pi:
        angle -= 2 * math.pi
    time.sleep(0.04)
