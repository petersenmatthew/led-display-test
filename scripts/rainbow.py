import time, math
from rgbmatrix import RGBMatrix, RGBMatrixOptions

opts = RGBMatrixOptions()
opts.rows = 32; opts.cols = 64
matrix = RGBMatrix(options=opts)
fc = matrix.CreateFrameCanvas()

def hsv(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r, g, b = [
        (v, t, p), (q, v, p), (p, v, t),
        (p, q, v), (t, p, v), (v, p, q),
    ][i % 6]
    return int(r * 255), int(g * 255), int(b * 255)

t0 = 0
while True:
    for x in range(64):
        for y in range(32):
            r, g, b = hsv((x + t0) / 64.0, 1.0, 0.9)
            fc.SetPixel(x, y, r, g, b)
    t0 += 1
    time.sleep(0.03)
    fc = matrix.SwapOnVSync(fc)
