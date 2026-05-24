import time, math
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from led_brightness import apply_live_brightness, read_initial_brightness

opts = RGBMatrixOptions()
opts.rows = 32; opts.cols = 64
opts.brightness = read_initial_brightness()
matrix = RGBMatrix(options=opts)
fc = matrix.CreateFrameCanvas()

amber = graphics.Color(255, 159, 67)
cyan  = graphics.Color(60, 200, 255)
mag   = graphics.Color(255, 80, 180)

t = 0
while True:
    apply_live_brightness(matrix)
    fc.Clear()
    # rotating line
    cx, cy = 32, 16
    a = t * 0.08
    x2 = int(cx + math.cos(a) * 14)
    y2 = int(cy + math.sin(a) * 12)
    graphics.DrawLine(fc, cx, cy, x2, y2, amber)
    # pulsing circle
    rad = 6 + int(3 * math.sin(t * 0.12))
    graphics.DrawCircle(fc, 12, 16, rad, cyan)
    # static circle
    graphics.DrawCircle(fc, 52, 16, 6, mag)
    t += 1
    time.sleep(0.04)
    fc = matrix.SwapOnVSync(fc)
