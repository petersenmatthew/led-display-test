from rgbmatrix import RGBMatrix, RGBMatrixOptions

opts = RGBMatrixOptions()
opts.rows = 32; opts.cols = 64
matrix = RGBMatrix(options=opts)
fc = matrix.CreateFrameCanvas()

# Draw a few static pixels in different colors.
for x, y, (r, g, b) in [
    (10, 10, (255,   0,   0)),
    (20, 10, (  0, 255,   0)),
    (30, 10, (  0,   0, 255)),
    (40, 10, (255, 255,   0)),
    (50, 10, (255,   0, 255)),
]:
    fc.SetPixel(x, y, r, g, b)

matrix.SwapOnVSync(fc)
