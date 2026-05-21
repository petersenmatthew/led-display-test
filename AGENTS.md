A single-file HTML/Canvas LED matrix display tester

When creating scripts, write them to be as easily exportable to a Raspberry Pi as possible.

RPi font-loading rule: in any script that uses `rgbmatrix.graphics`, load all BDF fonts (and read any other files from `/home/pi/...`) BEFORE calling `RGBMatrix(options=opts)`. The matrix constructor drops root privileges to user `daemon`, which cannot read `/home/pi` (mode 700), so font loads after that point fail with "Couldn't load font ...". The browser test in `worker.js` does not care about order, so this reordering is always safe for both environments. Alternative: set `opts.drop_privileges = False` before constructing the matrix.