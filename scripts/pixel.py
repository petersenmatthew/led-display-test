import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from led_brightness import apply_live_brightness, read_initial_brightness

opts = RGBMatrixOptions()
opts.rows = 32; opts.cols = 64
opts.brightness = read_initial_brightness()
matrix = RGBMatrix(options=opts)
fc = matrix.CreateFrameCanvas()

PIXELS = [
    (10, 10, (255,   0,   0)),
    (20, 10, (  0, 255,   0)),
    (30, 10, (  0,   0, 255)),
    (40, 10, (255, 255,   0)),
    (50, 10, (255,   0, 255)),
]

while True:
    apply_live_brightness(matrix)
    fc.Clear()
    for x, y, (r, g, b) in PIXELS:
        fc.SetPixel(x, y, r, g, b)
    fc = matrix.SwapOnVSync(fc)
    time.sleep(0.15)
