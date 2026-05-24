import os
import time
import math
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from led_brightness import apply_live_brightness, read_initial_brightness

# In Pyodide (browser), fonts are at "./fonts/"; on Pi, use relative path
try:
    FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
except NameError:
    FONT_DIR = "./fonts"

ROWS = 32
COLS = 64

# Ticket nearly fills the screen
TW = 62
TH = 30
TY = 1
CENTER_X = 32

# Geometry
PERF = 53        # perforation column
STUB_X0 = 55     # ADMIT ONE stub starts here
STUB_X1 = 60     # stub ends here

# Ink color (warm dark brown - matches reference ticket text)
INK = (38, 16, 4)


class ScratchCanvas:
    """Small in-memory canvas used before the matrix drops privileges."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.buf = bytearray(width * height * 3)

    def SetPixel(self, x, y, r, g, b):
        x = int(x)
        y = int(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.buf[i] = int(r) & 0xFF
            self.buf[i + 1] = int(g) & 0xFF
            self.buf[i + 2] = int(b) & 0xFF


class BdfFont:
    def __init__(self, path):
        self.path = path
        self.glyphs = {}
        self.default_char = 32
        self._load(path)

    def _load(self, path):
        current = None
        bitmap = None

        with open(path, "r", encoding="ascii") as f:
            for raw_line in f:
                line = raw_line.strip()
                if line.startswith("DEFAULT_CHAR "):
                    self.default_char = int(line.split()[1])
                elif line.startswith("STARTCHAR "):
                    current = {"encoding": None, "dwidth": 0, "bbx": (0, 0, 0, 0)}
                    bitmap = None
                elif current is not None and line.startswith("ENCODING "):
                    current["encoding"] = int(line.split()[1])
                elif current is not None and line.startswith("DWIDTH "):
                    current["dwidth"] = int(line.split()[1])
                elif current is not None and line.startswith("BBX "):
                    parts = line.split()
                    current["bbx"] = tuple(int(v) for v in parts[1:5])
                elif current is not None and line == "BITMAP":
                    bitmap = []
                elif current is not None and line == "ENDCHAR":
                    if current["encoding"] is not None and bitmap is not None:
                        current["bitmap"] = bitmap
                        self.glyphs[current["encoding"]] = current
                    current = None
                    bitmap = None
                elif bitmap is not None:
                    bitmap.append(int(line, 16) if line else 0)

    def glyph(self, ch):
        codepoint = ord(ch)
        return (
            self.glyphs.get(codepoint)
            or self.glyphs.get(self.default_char)
            or self.glyphs.get(32)
        )


def draw_text(canvas, font, x, baseline_y, color, text):
    cursor_x = int(x)
    r, g, b = color

    for ch in text:
        glyph = font.glyph(ch)
        if glyph is None:
            continue

        width, height, xoff, yoff = glyph["bbx"]
        top_y = int(baseline_y) - yoff - height

        for row, bits in enumerate(glyph["bitmap"]):
            bit_count = max(width, bits.bit_length(), 1)
            bit_count = ((bit_count + 7) // 8) * 8
            for col in range(width):
                if bits & (1 << (bit_count - 1 - col)):
                    canvas.SetPixel(cursor_x + xoff + col, top_y + row, r, g, b)

        cursor_x += glyph["dwidth"]

    return cursor_x - int(x)


# Load fonts before creating RGBMatrix — the matrix constructor drops root
# privileges to user "daemon", which can't read files inside /home/pi.
NAME_FONT = BdfFont(os.path.join(FONT_DIR, "5x8.bdf"))
YC_FONT = BdfFont(os.path.join(FONT_DIR, "7x13.bdf"))

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

def make_front_face():
    canvas = ScratchCanvas(TW, TH)
    fill_bg(canvas)
    corner_notches(canvas)
    perforation(canvas)

    # Top placeholder bars (representing "Y COMBINATOR PRESENTS / STARTUP SCHOOL 2026")
    bar(canvas, 3, 6, 3, 4)     # "Y COMBINATOR" word 1
    bar(canvas, 8, 22, 3, 4)    # word 2
    bar(canvas, 3, 13, 6, 7)    # "STARTUP"
    bar(canvas, 15, 23, 6, 7)   # "SCHOOL"
    bar(canvas, 25, 32, 6, 7)   # "2026"

    # "JUSTIN WU" with 5x8 = 9 * 5 = 45 px wide. Center in main body (53 wide).
    name = "JUSTIN WU"
    name_width = 5 * len(name)
    name_x = max(0, (PERF - name_width) // 2)
    draw_text(canvas, NAME_FONT, name_x, 18, INK, name)
    draw_text(canvas, NAME_FONT, name_x + 1, 18, INK, name)  # bold

    # Bottom placeholder bars (representing "CHASE CENTER, SF / JULY 25-26")
    bar(canvas, 3, 11, 23, 24)   # "CHASE"
    bar(canvas, 13, 22, 23, 24)  # "CENTER,"
    bar(canvas, 24, 28, 23, 24)  # "SF"
    bar(canvas, 3, 9, 26, 27)    # "JULY"
    bar(canvas, 11, 21, 26, 27)  # "25-26"

    for y0, y1 in STUB_BARS_Y:
        bar(canvas, STUB_X0, STUB_X1, y0, y1)

    return bytes(canvas.buf)


def make_back_face():
    canvas = ScratchCanvas(TW, TH)
    fill_bg(canvas, mirror=True)
    corner_notches(canvas)
    perforation(canvas)

    # Back side: same stylized layout but flipped feel, with Y COMBINATOR stamp.
    yc_x = (PERF - 14) // 2
    draw_text(canvas, YC_FONT, yc_x, 19, INK, "YC")
    draw_text(canvas, YC_FONT, yc_x + 1, 19, INK, "YC")  # bold

    bar(canvas, 3, 25, 4, 5)
    bar(canvas, 27, 38, 4, 5)
    bar(canvas, 3, 12, 25, 26)
    bar(canvas, 14, 28, 25, 26)
    bar(canvas, 30, 38, 25, 26)

    for y0, y1 in STUB_BARS_Y:
        bar(canvas, STUB_X0, STUB_X1, y0, y1)

    return bytes(canvas.buf)


# Stub: vertical stack of small bars to represent "ADMIT ONE"
STUB_BARS_Y = [(3, 4), (6, 7), (9, 10), (12, 13), (15, 16),
               (19, 20), (22, 23), (25, 26)]

# Snapshot to bytes for fast lookup during rotation.
FRONT_BUF = make_front_face()
BACK_BUF = make_back_face()

# ---------- ROTATION ----------
ANGLE_STEP = 0.045

def draw_ticket(canvas, angle):
    canvas.Clear()
    cos_t = math.cos(angle)
    abs_cos = abs(cos_t)
    half_w = TW / 2.0

    if abs_cos > 0.025:
        src = FRONT_BUF if cos_t > 0 else BACK_BUF
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
                canvas.SetPixel(sx, TY + sy, r, g, b)
    else:
        for sy in range(2, TH - 2):
            canvas.SetPixel(CENTER_X, TY + sy, 180, 75, 25)
        canvas.SetPixel(CENTER_X, TY + 1, 90, 40, 15)
        canvas.SetPixel(CENTER_X, TY + TH - 2, 90, 40, 15)


def draw_frame(canvas, frame=0):
    draw_ticket(canvas, frame * ANGLE_STEP)


def main():
    opts = RGBMatrixOptions()
    opts.rows = ROWS
    opts.cols = COLS
    opts.brightness = read_initial_brightness()

    matrix = RGBMatrix(options=opts)
    offscreen = matrix.CreateFrameCanvas()
    angle = 0.0

    while True:
        apply_live_brightness(matrix)
        draw_ticket(offscreen, angle)
        offscreen = matrix.SwapOnVSync(offscreen)
        angle += ANGLE_STEP
        if angle > 2 * math.pi:
            angle -= 2 * math.pi
        time.sleep(0.04)


if __name__ == "__main__":
    main()
