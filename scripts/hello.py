import os
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from led_brightness import (
    apply_live_brightness,
    read_initial_brightness,
    read_live_brightness,
)

# In Pyodide (browser), fonts are at "./fonts/"; on Pi, use relative path
try:
    FONT_DIR = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts"))
except NameError:
    FONT_DIR = "./fonts"

# Load font before creating RGBMatrix — the matrix constructor drops root
# privileges to user "daemon", which can't read files inside /home/pi.
font = graphics.Font()
font.LoadFont(os.path.join(FONT_DIR, "7x13.bdf"))

opts = RGBMatrixOptions()
opts.rows = 32
opts.cols = 64
opts.brightness = read_initial_brightness()
matrix = RGBMatrix(options=opts)
offscreen = matrix.CreateFrameCanvas()


_last_debug_brightness = None


def scaled_color(r, g, b):
    global _last_debug_brightness
    brightness = read_live_brightness()
    scale = brightness / 100
    scaled = (int(r * scale), int(g * scale), int(b * scale))
    if brightness != _last_debug_brightness:
        print(f"[hello] brightness={brightness} color={scaled}", flush=True)
        _last_debug_brightness = brightness
    return graphics.Color(*scaled)


pos = offscreen.width
text = "Hello world!"
while True:
    apply_live_brightness(matrix)
    offscreen.Clear()
    color = scaled_color(255, 159, 67)
    length = graphics.DrawText(offscreen, font, pos, 21, color, text)
    pos -= 1
    if pos + length < 0:
        pos = offscreen.width
    time.sleep(0.04)
    offscreen = matrix.SwapOnVSync(offscreen)
