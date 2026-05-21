A single-file HTML/Canvas LED matrix display tester

When creating scripts, write them to be as easily exportable to a Raspberry Pi as possible.

Load fonts (and any `/home/pi/...` files) before `RGBMatrix(options=opts)` — the constructor drops privileges to user `daemon` which can't read `/home/pi`.