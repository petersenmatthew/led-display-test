import time, math
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

opts = RGBMatrixOptions()
opts.rows = 32; opts.cols = 64
matrix = RGBMatrix(options=opts)
fc = matrix.CreateFrameCanvas()

orange  = graphics.Color(255, 100, 20)
red     = graphics.Color(180, 40, 0)
white   = graphics.Color(220, 220, 220)
gray    = graphics.Color(80, 80, 80)
net_col = graphics.Color(160, 160, 160)

# Hoop position
HOOP_X   = 48
HOOP_Y   = 12
HOOP_R   = 5   # radius of rim
BOARD_X  = 58  # backboard x

# Ball arc: launch from left, arc over to hoop center
LAUNCH_X = 6
LAUNCH_Y = 26
ARC_FRAMES = 40   # frames ball is in flight
PAUSE_FRAMES = 18 # frames to hold after scoring

def ball_pos(t):
    """Parabolic arc from launch point to hoop center."""
    frac = t / ARC_FRAMES
    x = LAUNCH_X + (HOOP_X - LAUNCH_X) * frac
    # parabola: starts at LAUNCH_Y, peaks at ~y=4, lands at HOOP_Y
    y = (1 - frac) * LAUNCH_Y + frac * HOOP_Y - 18 * frac * (1 - frac)
    return int(x), int(y)

def draw_backboard(canvas):
    for y in range(6, 22):
        canvas.SetPixel(BOARD_X, y, 200, 200, 200)

def draw_hoop(canvas):
    # Rim: horizontal line with small depth
    for x in range(HOOP_X - HOOP_R, HOOP_X + HOOP_R + 1):
        canvas.SetPixel(x, HOOP_Y, 180, 40, 0)
    # Pole connecting rim to board
    graphics.DrawLine(canvas, HOOP_X + HOOP_R, HOOP_Y, BOARD_X - 1, HOOP_Y, red)

def draw_net(canvas, sway=0):
    # Net hangs below the rim as a simple trapezoid with lines
    top_l = HOOP_X - HOOP_R + 1
    top_r = HOOP_X + HOOP_R - 1
    net_depth = 7
    bottom_l = HOOP_X - 2 + sway
    bottom_r = HOOP_X + 2 + sway
    # Left and right edges
    graphics.DrawLine(canvas, top_l, HOOP_Y + 1, bottom_l, HOOP_Y + net_depth, net_col)
    graphics.DrawLine(canvas, top_r, HOOP_Y + 1, bottom_r, HOOP_Y + net_depth, net_col)
    # Horizontal strands
    for i in range(1, 4):
        frac = i / 4
        xl = int(top_l + (bottom_l - top_l) * frac)
        xr = int(top_r + (bottom_r - top_r) * frac)
        y  = HOOP_Y + 1 + int(net_depth * frac)
        graphics.DrawLine(canvas, xl, y, xr, y, gray)
    # Vertical strands
    for s in range(3):
        frac = (s + 1) / 4
        x_top  = int(top_l  + (top_r  - top_l)  * frac)
        x_bot  = int(bottom_l + (bottom_r - bottom_l) * frac)
        graphics.DrawLine(canvas, x_top, HOOP_Y + 1, x_bot, HOOP_Y + net_depth, gray)

def draw_ball(canvas, bx, by, r=2):
    graphics.DrawCircle(canvas, bx, by, r, orange)
    # Simple seam line
    canvas.SetPixel(bx, by - r + 1, 60, 30, 0)
    canvas.SetPixel(bx, by + r - 1, 60, 30, 0)

frame = 0
phase = "fly"    # fly | score | reset
sway  = 0
sway_dir = 1

while True:
    fc.Clear()

    draw_backboard(fc)
    draw_hoop(fc)

    if phase == "fly":
        bx, by = ball_pos(frame)
        draw_net(fc, sway=0)
        draw_ball(fc, bx, by)
        frame += 1
        if frame >= ARC_FRAMES:
            phase = "score"
            frame = 0
            sway = 0
            sway_dir = 1

    elif phase == "score":
        # Ball passes through net — draw at hoop center sinking down
        sink = int(frame * 6 / PAUSE_FRAMES)
        draw_net(fc, sway=sway)
        draw_ball(fc, HOOP_X, HOOP_Y + sink)
        sway += sway_dir
        if abs(sway) >= 2:
            sway_dir *= -1
        frame += 1
        if frame >= PAUSE_FRAMES:
            phase = "fly"
            frame = 0

    fc = matrix.SwapOnVSync(fc)
    time.sleep(0.05)
