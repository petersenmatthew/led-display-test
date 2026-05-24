import os
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from led_brightness import apply_live_brightness, read_initial_brightness

# In Pyodide (browser), fonts are at "./fonts/"; on Pi, use relative path
try:
    FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
except NameError:
    FONT_DIR = "./fonts"

# Manually draw "@JUSTINWU" stretched to fill the full 64x32 display
def draw_compressed_text(canvas):
    """
    Draw @JUSTINWU stretched to fill the entire 64x32 display.
    Bold, blocky font matching the reference image.
    """
    canvas.Clear()

    # Full height display: y ranges from 0-31
    # Each character is taller and bolder, filling vertical space

    # Fill screen width: @_J_U_S_T_I_N_W_U (0-63)
    # @ symbol (x=0-5)
    at = []
    for y in range(9, 24):
        if y in [9, 23]:  # Top and bottom
            at.extend([(x, y) for x in range(1, 5)])
        elif y in range(10, 23):
            at.append((0, y))  # Left edge
            at.append((5, y))  # Right edge
            if y in range(14, 19):  # Inner @
                at.extend([(2, y), (3, y)])

    # J (x=7-12)
    j = []
    for y in range(9, 24):
        if y == 9:  # Top bar
            j.extend([(x, y) for x in range(7, 13)])
        elif y in range(10, 21):  # Vertical stem
            j.extend([(10, y), (11, y)])
        elif y in range(21, 24):  # Bottom curve
            j.extend([(7, y), (8, y), (9, y)])

    # U (x=14-19)
    u = []
    for y in range(9, 24):
        if y in range(9, 22):  # Vertical sides
            u.extend([(14, y), (15, y), (18, y), (19, y)])
        if y in range(22, 24):  # Bottom
            u.extend([(x, y) for x in range(14, 20)])

    # S (x=21-26)
    s = []
    for y in range(9, 24):
        if y in [9, 10]:  # Top
            s.extend([(x, y) for x in range(21, 27)])
        elif y in [15, 16]:  # Middle
            s.extend([(x, y) for x in range(21, 27)])
        elif y in [22, 23]:  # Bottom
            s.extend([(x, y) for x in range(21, 27)])
        elif y in range(11, 15):  # Top left
            s.extend([(21, y), (22, y)])
        elif y in range(17, 22):  # Bottom right
            s.extend([(25, y), (26, y)])

    # T (x=28-33)
    t = []
    for y in range(9, 24):
        if y in [9, 10]:  # Top bar
            t.extend([(x, y) for x in range(28, 34)])
        elif y in range(11, 24):  # Vertical stem
            t.extend([(30, y), (31, y)])

    # I (x=35-38)
    i = []
    for y in range(9, 24):
        if y in [9, 10, 22, 23]:  # Top and bottom bars
            i.extend([(x, y) for x in range(35, 39)])
        elif y in range(11, 22):  # Vertical stem
            i.extend([(36, y), (37, y)])

    # N (x=40-45)
    n = []
    for y in range(9, 24):
        n.extend([(40, y), (41, y)])  # Left vertical
        n.extend([(44, y), (45, y)])  # Right vertical
        # Diagonal
        diag_x = 42 + int((y - 9) * 1 / 7)
        if 42 <= diag_x <= 43:
            n.append((diag_x, y))

    # W (x=47-55) - Clean W shape
    w = []
    for y in range(9, 24):
        # Left diagonal down: \ from (47,9) to (49,23)
        if y < 16:
            w.append((47, y))
        else:
            offset = (y - 16) // 4
            w.append((47 + offset, y))

        # Left diagonal up: / from (49,23) to (51,9)
        if y < 16:
            offset = (15 - y) // 3
            w.append((51 - offset, y))
        else:
            w.append((49, y))

        # Right diagonal down: \ from (51,9) to (53,23)
        if y < 16:
            w.append((51, y))
        else:
            offset = (y - 16) // 4
            w.append((51 + offset, y))

        # Right diagonal up: / from (53,23) to (55,9)
        if y < 16:
            offset = (15 - y) // 3
            w.append((55 - offset, y))
        else:
            w.append((53, y))

    # U (x=57-63)
    u2 = []
    for y in range(9, 24):
        if y in range(9, 22):  # Vertical sides
            u2.extend([(57, y), (58, y), (62, y), (63, y)])
        if y in range(22, 24):  # Bottom
            u2.extend([(x, y) for x in range(57, 64)])

    # Combine all characters
    all_pixels = at + j + u + s + t + i + n + w + u2

    # Draw all pixels
    for x, y in all_pixels:
        canvas.SetPixel(x, y, 255, 255, 255)


def draw_frame(canvas, frame=0):
    """For browser compatibility."""
    draw_compressed_text(canvas)


def main():
    opts = RGBMatrixOptions()
    opts.rows = 32
    opts.cols = 64
    opts.brightness = read_initial_brightness()
    matrix = RGBMatrix(options=opts)
    offscreen = matrix.CreateFrameCanvas()

    while True:
        apply_live_brightness(matrix)
        draw_compressed_text(offscreen)
        offscreen = matrix.SwapOnVSync(offscreen)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
