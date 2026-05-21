import os
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")

opts = RGBMatrixOptions()
opts.rows = 32
opts.cols = 64
matrix = RGBMatrix(options=opts)
offscreen = matrix.CreateFrameCanvas()

font = graphics.Font()
font.LoadFont(os.path.join(FONT_DIR, "7x13.bdf"))
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
