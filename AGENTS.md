A single-file HTML/Canvas LED matrix display tester

When creating scripts, write them to be as easily exportable to a Raspberry Pi as possible.

Load fonts (and any `/home/pi/...` files) before `RGBMatrix(options=opts)` — the constructor drops privileges to user `daemon` which can't read `/home/pi`.

Use this pattern in every future script:

from led_brightness import apply_live_brightness, read_initial_brightness

opts = RGBMatrixOptions()
opts.rows = 32
opts.cols = 64
opts.brightness = read_initial_brightness()
matrix = RGBMatrix(options=opts)

while True:
    apply_live_brightness(matrix)
    # draw frame...