import os
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

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
matrix = RGBMatrix(options=opts)
offscreen = matrix.CreateFrameCanvas()
color = graphics.Color(255, 159, 67)

pos = offscreen.width
text = "Hello world!"
while True:
    offscreen.Clear()
    length = graphics.DrawText(offscreen, font, pos, 21, color, text)
    pos -= 1
    if pos + length < 0:
        pos = offscreen.width
    time.sleep(0.04)
    offscreen = matrix.SwapOnVSync(offscreen)
