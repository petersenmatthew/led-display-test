"""GitHub contribution graph for a 64x32 RGB LED matrix.

Renders the green contribution "square" for a GitHub user, exactly as it
appears on the profile (53 weeks x 7 days, one pixel per day, no titles).

A baked snapshot is used so this works offline and in the browser preview.
On the Pi it tries to refresh live from GitHub's no-auth contributions
endpoint, falling back to the snapshot if the network is unavailable.
"""

from __future__ import annotations

import re
import time

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from led_brightness import apply_live_brightness, read_initial_brightness

USERNAME = "petersenmatthew"

ROWS = 32
COLS = 64
REFRESH_SECONDS = 30 * 60  # re-fetch live data every 30 minutes

# Big square cells with a 1px gap, GitHub style. 3px cells fit 7 rows in the
# 32px height with room for the gaps; only the most recent weeks that fit the
# 64px width are shown (oldest weeks are cropped off the left).
CELL = 3
GAP = 1

# GitHub dark-theme palette (level 0-4). Level 0 is kept dim so the empty
# grid cells read as a faint dark grid rather than glowing white.
PALETTE = (
    (10, 13, 16),    # 0 - none
    (14, 68, 41),    # 1
    (0, 109, 50),    # 2
    (38, 166, 65),   # 3
    (57, 211, 83),   # 4
)

# Baked snapshot: 53 columns (oldest -> newest), each 7 chars (Sun..Sat).
SNAPSHOT = [
    '0000000', '0000000', '0000000', '0000000', '0000000', '0000000',
    '0000000', '0001001', '1111000', '0000100', '0010100', '0000100',
    '0000001', '1000000', '0001010', '1000011', '0000100', '0000000',
    '0000000', '0001000', '0000000', '0000000', '0000000', '0000000',
    '0000000', '0000000', '0000000', '0110003', '3111102', '2001102',
    '3001100', '1101103', '2011322', '1113210', '1112434', '2120224',
    '1122211', '1111110', '0102110', '0111110', '0141100', '0010001',
    '0100001', '0000000', '0000000', '1011020', '0010214', '1011100',
    '0000000', '0032101', '2100000', '0000000', '0000000',
]


def parse_html(html):
    """Parse GitHub's contributions HTML into columns of 7 level digits."""
    cells = []
    max_col = 0
    for td in re.findall(r'<td[^>]*class="ContributionCalendar-day"[^>]*>', html):
        idm = re.search(r'contribution-day-component-(\d+)-(\d+)', td)
        lvl = re.search(r'data-level="(\d)"', td)
        if not idm or not lvl:
            continue
        row, col, level = int(idm.group(1)), int(idm.group(2)), int(lvl.group(1))
        cells.append((col, row, level))
        max_col = max(max_col, col)
    if not cells:
        return None
    grid = [[0] * 7 for _ in range(max_col + 1)]
    for col, row, level in cells:
        grid[col][row] = level
    return [''.join(str(grid[c][r]) for r in range(7)) for c in range(max_col + 1)]


def fetch_live():
    """Return fresh columns from GitHub, or None on any failure."""
    try:
        import urllib.request

        url = "https://github.com/users/%s/contributions" % USERNAME
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", "replace")
        return parse_html(html)
    except Exception:
        return None


def draw(canvas, columns):
    """Draw the grid with big square cells, most-recent weeks filling the panel."""
    pitch = CELL + GAP
    cols_fit = (COLS + GAP) // pitch
    visible = columns[-cols_fit:]  # most recent weeks
    grid_w = len(visible) * pitch - GAP
    grid_h = 7 * pitch - GAP
    x0 = (COLS - grid_w) // 2
    y0 = (ROWS - grid_h) // 2
    canvas.Clear()
    for cx, col in enumerate(visible):
        for cy, ch in enumerate(col):
            r, g, b = PALETTE[int(ch)]
            px = x0 + cx * pitch
            py = y0 + cy * pitch
            for dx in range(CELL):
                for dy in range(CELL):
                    canvas.SetPixel(px + dx, py + dy, r, g, b)


opts = RGBMatrixOptions()
opts.rows = ROWS
opts.cols = COLS
opts.brightness = read_initial_brightness()
matrix = RGBMatrix(options=opts)
canvas = matrix.CreateFrameCanvas()

columns = fetch_live() or SNAPSHOT
last_fetch = time.monotonic()

while True:
    apply_live_brightness(matrix)
    if time.monotonic() - last_fetch >= REFRESH_SECONDS:
        fresh = fetch_live()
        if fresh:
            columns = fresh
        last_fetch = time.monotonic()
    draw(canvas, columns)
    canvas = matrix.SwapOnVSync(canvas)
    time.sleep(0.5)
