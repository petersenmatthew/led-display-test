import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from led_brightness import apply_live_brightness, read_initial_brightness

opts = RGBMatrixOptions()
opts.rows = 32
opts.cols = 64
opts.brightness = read_initial_brightness()
matrix = RGBMatrix(options=opts)
offscreen = matrix.CreateFrameCanvas()

# === COLOR PALETTE ===
WHITE = (255, 255, 255)

# Skin tones - 9 shades, warm undertone
S0 = (215, 162, 120)   # Brightest specular
S1 = (195, 140, 100)   # Highlight
S2 = (175, 120, 85)    # Light
S3 = (155, 102, 72)    # Light-mid
S4 = (138, 90, 62)     # Base
S5 = (118, 76, 52)     # Mid-dark
S6 = (95, 62, 42)      # Shadow
S7 = (72, 48, 32)      # Deep shadow
S8 = (52, 35, 24)      # Darkest

# Hair
H1 = (42, 35, 30)
H2 = (28, 23, 20)
H3 = (18, 15, 13)
H4 = (8, 7, 6)         # Deepest hair shadow

# Beard
B1 = (52, 40, 33)
B2 = (38, 30, 25)
B3 = (26, 21, 17)
B4 = (15, 12, 10)

# Eyes
EW = (240, 235, 228)
EW_SH = (210, 204, 195)
IR0 = (78, 58, 45)     # Iris highlight (top, lit)
IR1 = (58, 42, 32)     # Iris mid
IR2 = (38, 28, 22)     # Iris dark
PU = (10, 8, 6)        # Pupil
CATCH = (255, 252, 245)

# Lips
L1 = (135, 78, 70)
L2 = (110, 60, 54)
L3 = (85, 48, 44)
L4 = (62, 36, 33)

# Teeth
T1 = (250, 248, 242)
T2 = (232, 228, 220)
T3 = (208, 204, 195)

# Nose / details
N1 = (38, 26, 20)      # Nostril dark
PHIL = (78, 52, 36)    # Philtrum shadow

# Jersey - Celtics green
JG1 = (0, 138, 60)
JG2 = (0, 112, 50)
JG3 = (0, 86, 38)
JG4 = (0, 64, 28)

def px(c, x, y, col):
    if 0 <= x < 64 and 0 <= y < 32:
        c.SetPixel(x, y, col[0], col[1], col[2])

def fill(c, x0, x1, y0, y1, col):
    for y in range(y0, y1):
        for x in range(x0, x1):
            px(c, x, y, col)

# ---------- EYE DRAWING ----------

def draw_left_eye_open(c):
    """Almond-shaped open left eye with iris, pupil, catchlight."""
    # Upper lash line (top lid)
    for x in range(21, 28):
        px(c, x, 10, H3)
    # Outer/inner eye corners (slightly softer)
    px(c, 20, 10, S7)
    px(c, 28, 10, S7)
    # Row 11 - top of eye, iris top
    px(c, 21, 11, EW_SH); px(c, 22, 11, EW)
    px(c, 23, 11, IR0);   px(c, 24, 11, IR0); px(c, 25, 11, IR0)
    px(c, 26, 11, EW);    px(c, 27, 11, EW_SH)
    # Row 12 - widest, pupil
    px(c, 21, 12, EW);    px(c, 22, 12, EW)
    px(c, 23, 12, IR1);   px(c, 24, 12, PU);  px(c, 25, 12, IR1)
    px(c, 26, 12, EW);    px(c, 27, 12, EW)
    # Row 13 - bottom of eye
    px(c, 21, 13, EW_SH); px(c, 22, 13, EW)
    px(c, 23, 13, IR2);   px(c, 24, 13, IR1); px(c, 25, 13, IR2)
    px(c, 26, 13, EW);    px(c, 27, 13, EW_SH)
    # Catchlight - upper-left of pupil
    px(c, 23, 11, CATCH)
    # Lower lid / lash
    for x in range(21, 28):
        px(c, x, 14, S6)
    # Tear duct (inner corner)
    px(c, 27, 12, L4)

def draw_right_eye_open(c):
    """Mirror of left eye - centered at x=40."""
    for x in range(37, 44):
        px(c, x, 10, H3)
    px(c, 36, 10, S7)
    px(c, 44, 10, S7)
    px(c, 37, 11, EW_SH); px(c, 38, 11, EW)
    px(c, 39, 11, IR0);   px(c, 40, 11, IR0); px(c, 41, 11, IR0)
    px(c, 42, 11, EW);    px(c, 43, 11, EW_SH)
    px(c, 37, 12, EW);    px(c, 38, 12, EW)
    px(c, 39, 12, IR1);   px(c, 40, 12, PU);  px(c, 41, 12, IR1)
    px(c, 42, 12, EW);    px(c, 43, 12, EW)
    px(c, 37, 13, EW_SH); px(c, 38, 13, EW)
    px(c, 39, 13, IR2);   px(c, 40, 13, IR1); px(c, 41, 13, IR2)
    px(c, 42, 13, EW);    px(c, 43, 13, EW_SH)
    px(c, 39, 11, CATCH)
    for x in range(37, 44):
        px(c, x, 14, S6)
    # Tear duct (inner corner is on left side for right eye)
    px(c, 37, 12, L4)

def draw_left_eye_closed(c):
    """Fully closed eyelid - no eye visible, only skin + lash seam."""
    # Eye socket region x=20-28, y=10-14
    # Top: shadow from brow
    for x in range(20, 29):
        px(c, x, 10, S5)
    # Eyelid bulge with highlight
    for x in range(20, 29):
        if 22 <= x <= 26:
            px(c, x, 11, S3)
        else:
            px(c, x, 11, S4)
    # Lash line / closed seam - DARK horizontal line
    for x in range(20, 29):
        px(c, x, 12, H3)
    # Soft eyelash flick at outer corner
    px(c, 20, 11, H3)
    px(c, 28, 13, H4)
    # Under-eye / lower lid
    for x in range(20, 29):
        px(c, x, 13, S4)
    # Lower transition
    for x in range(20, 29):
        px(c, x, 14, S5)

def draw_right_eye_closed(c):
    for x in range(36, 45):
        px(c, x, 10, S5)
    for x in range(36, 45):
        if 38 <= x <= 42:
            px(c, x, 11, S3)
        else:
            px(c, x, 11, S4)
    for x in range(36, 45):
        px(c, x, 12, H3)
    px(c, 44, 11, H3)
    px(c, 36, 13, H4)
    for x in range(36, 45):
        px(c, x, 13, S4)
    for x in range(36, 45):
        px(c, x, 14, S5)

def draw_left_eye_half(c):
    """Half-closed - upper lid drooped over iris."""
    for x in range(20, 29):
        px(c, x, 10, S5)
    # Lowered lid line at y=12
    for x in range(21, 28):
        px(c, x, 11, H3)
    # Small sliver of eye visible at y=12
    px(c, 21, 12, S5); px(c, 22, 12, EW_SH)
    px(c, 23, 12, IR1); px(c, 24, 12, PU); px(c, 25, 12, IR1)
    px(c, 26, 12, EW_SH); px(c, 27, 12, S5)
    # Lower lid
    for x in range(21, 28):
        px(c, x, 13, S5)
    for x in range(20, 29):
        px(c, x, 14, S5)

def draw_right_eye_half(c):
    for x in range(36, 45):
        px(c, x, 10, S5)
    for x in range(37, 44):
        px(c, x, 11, H3)
    px(c, 37, 12, S5); px(c, 38, 12, EW_SH)
    px(c, 39, 12, IR1); px(c, 40, 12, PU); px(c, 41, 12, IR1)
    px(c, 42, 12, EW_SH); px(c, 43, 12, S5)
    for x in range(37, 44):
        px(c, x, 13, S5)
    for x in range(36, 45):
        px(c, x, 14, S5)

# ---------- MAIN DRAW ----------

def draw_jaylen(c, eyes="open", mouth="big_smile"):
    # Background
    fill(c, 0, 64, 0, 32, WHITE)

    # ===== HAIR (top crown) =====
    hair_rows = [
        (0, 25, 39),
        (1, 22, 42),
        (2, 20, 44),
        (3, 18, 46),
        (4, 17, 47),
        (5, 16, 48),
    ]
    for y, xs, xe in hair_rows:
        for x in range(xs, xe):
            t = (x * 5 + y * 11) % 9
            if t == 0:
                px(c, x, y, H1)
            elif t < 3:
                px(c, x, y, H2)
            elif t < 7:
                px(c, x, y, H3)
            else:
                px(c, x, y, H4)
    # Hairline curve y=6 (slight widow's peak)
    hairline = {
        15: H3, 16: H3, 17: H2,
        18: H3, 19: H3, 20: H3, 21: H3,
        22: H3, 23: H3, 24: H3,
        25: H4, 26: H4, 27: H4,  # peak shadow
        28: H3, 29: H3, 30: H3, 31: H3,
        32: H3, 33: H3, 34: H3,
        35: H3, 36: H3, 37: H3, 38: H3,
        39: H3, 40: H3, 41: H3, 42: H3,
        43: H2, 44: H2, 45: H3, 46: H3,
    }
    for x, col in hairline.items():
        px(c, x, 6, col)
    # Sideburns extending down
    for y in range(7, 10):
        px(c, 14 + (y - 7), y, H3)
        px(c, 49 - (y - 7), y, H3)
    px(c, 15, 9, H2)
    px(c, 48, 9, H2)

    # ===== FOREHEAD with lighting gradient =====
    for y in range(7, 10):
        for x in range(16, 48):
            if x < 18 or x > 45:
                continue
            if x < 20 or x > 43:
                px(c, x, y, S7)
            elif x < 22 or x > 41:
                px(c, x, y, S6)
            elif x < 25 or x > 38:
                px(c, x, y, S5)
            elif 28 <= x <= 35 and y >= 8:
                px(c, x, y, S2)   # bright forehead highlight
            elif 26 <= x <= 37:
                px(c, x, y, S3)
            else:
                px(c, x, y, S4)
    # Subtle forehead crease (subtle line)
    px(c, 28, 8, S5)
    px(c, 35, 8, S5)

    # ===== BROW BONE / EYEBROWS =====
    # Brow bone shadow
    for x in range(19, 30):
        px(c, x, 9, S6)
    for x in range(34, 45):
        px(c, x, 9, S6)
    # Left brow - thick, slightly arched
    left_brow = [(19,10),(20,9),(21,9),(22,8),(23,8),(24,8),(25,9),(26,9),(27,9),(28,10)]
    for x, y in left_brow:
        px(c, x, y, H4)
    # Thickness
    for x in range(21, 28):
        px(c, x, 9, H3)
    px(c, 22, 9, H4); px(c, 23, 9, H4); px(c, 24, 9, H4); px(c, 25, 9, H4)
    # Right brow
    right_brow = [(35,10),(36,9),(37,9),(38,8),(39,8),(40,8),(41,9),(42,9),(43,9),(44,10)]
    for x, y in right_brow:
        px(c, x, y, H4)
    for x in range(36, 43):
        px(c, x, 9, H3)
    px(c, 38, 9, H4); px(c, 39, 9, H4); px(c, 40, 9, H4); px(c, 41, 9, H4)

    # ===== TEMPLES / OUTER FACE =====
    for y in range(8, 17):
        # Left temple gradient
        px(c, 14, y, S8)
        px(c, 15, y, S7)
        px(c, 16, y, S6)
        # Right temple
        px(c, 49, y, S8)
        px(c, 48, y, S7)
        px(c, 47, y, S6)

    # ===== CHEEK / FACE FILL (before eyes so eyes overwrite) =====
    for y in range(10, 17):
        for x in range(17, 48):
            if x < 19:
                px(c, x, y, S6)
            elif x < 21:
                px(c, x, y, S5)
            elif x > 45:
                px(c, x, y, S6)
            elif x > 43:
                px(c, x, y, S5)
            else:
                px(c, x, y, S4)

    # Cheekbone highlights (under eyes, outer)
    for x in range(18, 22):
        px(c, x, 15, S3)
        px(c, x, 16, S2)
    for x in range(42, 46):
        px(c, x, 15, S3)
        px(c, x, 16, S2)
    # Apex cheekbones
    px(c, 19, 16, S1); px(c, 20, 16, S1)
    px(c, 43, 16, S1); px(c, 44, 16, S1)

    # ===== EYES =====
    if eyes == "open":
        draw_left_eye_open(c)
        draw_right_eye_open(c)
    elif eyes == "closed":
        draw_left_eye_closed(c)
        draw_right_eye_closed(c)
    elif eyes == "half":
        draw_left_eye_half(c)
        draw_right_eye_half(c)
    elif eyes == "wink_left":
        draw_left_eye_closed(c)
        draw_right_eye_open(c)
    elif eyes == "wink_right":
        draw_left_eye_open(c)
        draw_right_eye_closed(c)

    # ===== NOSE =====
    # Bridge with side shadows (longer, narrower)
    for y in range(11, 17):
        px(c, 30, y, S6)   # left shadow
        px(c, 33, y, S6)   # right shadow
        px(c, 31, y, S3)   # bridge highlight
        px(c, 32, y, S3)
    # Bridge tip
    px(c, 31, 15, S1)
    px(c, 32, 15, S1)
    # Nose tip (rounder)
    px(c, 30, 16, S5)
    px(c, 31, 16, S2)
    px(c, 32, 16, S2)
    px(c, 33, 16, S5)
    px(c, 31, 17, S3)
    px(c, 32, 17, S3)
    # Nose wings/alae
    px(c, 29, 16, S6)
    px(c, 34, 16, S6)
    px(c, 29, 17, S5)
    px(c, 34, 17, S5)
    # Nostrils
    px(c, 30, 17, N1)
    px(c, 33, 17, N1)
    # Septum
    px(c, 31, 18, S5)
    px(c, 32, 18, S5)

    # ===== PHILTRUM (groove above lip) =====
    px(c, 31, 18, PHIL)
    px(c, 32, 18, PHIL)
    px(c, 31, 19, S6)
    px(c, 32, 19, S6)

    # ===== EARS =====
    for y in range(11, 18):
        px(c, 12, y, S7)
        px(c, 13, y, S5)
        px(c, 51, y, S7)
        px(c, 50, y, S5)
    # Ear inner shadow
    px(c, 13, 13, S6)
    px(c, 13, 14, S7)
    px(c, 50, 13, S6)
    px(c, 50, 14, S7)
    # Earlobe
    px(c, 12, 17, S8)
    px(c, 13, 17, S6)
    px(c, 51, 17, S8)
    px(c, 50, 17, S6)

    # ===== BEARD - jaw, chin, mustache =====
    # Beard area definition
    beard_rows = [
        (17, 16, 48),
        (18, 16, 48),
        (19, 16, 48),
        (20, 17, 47),
        (21, 18, 46),
        (22, 19, 45),
        (23, 20, 44),
        (24, 22, 42),
        (25, 24, 40),
        (26, 26, 38),
    ]
    for y, xs, xe in beard_rows:
        for x in range(xs, xe):
            # Skip mouth area
            if 18 <= y <= 23 and 24 <= x <= 39:
                continue
            t = (x * 11 + y * 13) % 11
            if t == 0:
                px(c, x, y, B4)
            elif t < 3:
                px(c, x, y, B3)
            elif t < 7:
                px(c, x, y, B2)
            else:
                px(c, x, y, B1)
    # Beard edge / hairline definition on cheek
    for y in range(15, 22):
        px(c, 16, y, B4)
        px(c, 47, y, B4)
    # Sideburn-to-beard connection
    for y in range(10, 18):
        px(c, 15, y, B3)
        px(c, 48, y, B3)

    # ===== MUSTACHE =====
    # Just under nose, curving down at ends
    mustache = [
        (25, 18), (26, 18), (27, 18), (28, 17), (29, 17),
        (30, 17), (33, 17), (34, 17),
        (35, 17), (36, 18), (37, 18), (38, 18),
    ]
    for x, y in mustache:
        px(c, x, y, B3)
    # Center gap (philtrum shows through)
    px(c, 31, 17, S3)
    px(c, 32, 17, S3)
    # Mustache body fuller below
    for x in range(24, 39):
        if x < 26 or x > 36:
            continue
        if x in (31, 32):
            continue
        px(c, x, 18, B2)

    # ===== MOUTH =====
    if mouth == "big_smile":
        # Upper lip line (thin)
        for x in range(24, 40):
            px(c, x, 19, L4)
        # Wide open smile - teeth
        # Top teeth row
        for x in range(25, 39):
            px(c, x, 20, T1)
        # Tooth separations (thin shadows)
        for x in (27, 30, 33, 36):
            px(c, x, 20, T3)
        # Bottom teeth row (slightly darker - in shadow)
        for x in range(26, 38):
            px(c, x, 21, T2)
        # Inner mouth shadow at very back
        px(c, 31, 21, T3)
        px(c, 32, 21, T3)
        # Lower lip
        for x in range(25, 39):
            px(c, x, 22, L2)
        for x in range(26, 38):
            px(c, x, 23, L3)
        # Lower lip highlight
        px(c, 30, 22, L1); px(c, 31, 22, L1); px(c, 32, 22, L1); px(c, 33, 22, L1)
        # Mouth corners (deep)
        px(c, 23, 20, L4); px(c, 24, 20, L4)
        px(c, 39, 20, L4); px(c, 40, 20, L4)
        px(c, 24, 21, L4); px(c, 39, 21, L4)
        # Nasolabial folds (smile lines)
        px(c, 22, 17, S7); px(c, 22, 18, S7); px(c, 23, 19, S6)
        px(c, 41, 17, S7); px(c, 41, 18, S7); px(c, 40, 19, S6)

    elif mouth == "smile":
        # Closed-mouth smile
        for x in range(26, 38):
            px(c, x, 19, L4)
        for x in range(27, 37):
            px(c, x, 20, L2)
        for x in range(27, 37):
            px(c, x, 21, L3)
        # Cupid's bow on upper lip
        px(c, 31, 19, L3); px(c, 32, 19, L3)
        # Lower lip highlight
        px(c, 30, 20, L1); px(c, 31, 20, L1); px(c, 32, 20, L1); px(c, 33, 20, L1)
        # Slight smile corners turned up
        px(c, 25, 19, L4); px(c, 25, 20, L4)
        px(c, 38, 19, L4); px(c, 38, 20, L4)
        # Subtle smile lines
        px(c, 23, 18, S6); px(c, 40, 18, S6)

    else:  # neutral
        for x in range(28, 36):
            px(c, x, 19, L3)
        for x in range(28, 36):
            px(c, x, 20, L2)
        for x in range(29, 35):
            px(c, x, 21, L3)
        # Cupid's bow
        px(c, 31, 19, L4); px(c, 32, 19, L4)
        # Lower lip highlight
        px(c, 30, 20, L1); px(c, 33, 20, L1)
        # Corners
        px(c, 27, 20, L4); px(c, 36, 20, L4)

    # ===== CHIN =====
    # Chin highlight
    px(c, 31, 25, S2); px(c, 32, 25, S2)
    # Chin definition / dimple shadow
    px(c, 31, 26, S6); px(c, 32, 26, S6)
    # Chin shadow under
    for x in range(28, 36):
        px(c, x, 27, S7)

    # ===== NECK =====
    for y in range(27, 30):
        for x in range(26, 38):
            px(c, x, y, S7)
    # Neck shadow
    for x in range(26, 38):
        px(c, x, 28, S8)
    # Adam's apple subtle hint
    px(c, 31, 28, S6); px(c, 32, 28, S6)
    # Neck side definition
    for y in range(27, 30):
        px(c, 25, y, S8)
        px(c, 38, y, S8)

    # ===== JERSEY =====
    # Top edge / collar shadow
    for x in range(15, 49):
        px(c, x, 29, JG4)
    # Main jersey body with shading
    for y in range(30, 32):
        for x in range(15, 49):
            if x < 18 or x > 45:
                px(c, x, y, JG3)
            elif x < 22 or x > 41:
                px(c, x, y, JG2)
            else:
                px(c, x, y, JG1)
    # Collar V-neck
    px(c, 30, 29, S8); px(c, 31, 29, S8); px(c, 32, 29, S8); px(c, 33, 29, S8)
    px(c, 31, 30, S8); px(c, 32, 30, S8)
    # Jersey trim/stitching (white-ish at very edges)
    px(c, 15, 29, (240, 240, 240))
    px(c, 48, 29, (240, 240, 240))


# === ANIMATION SEQUENCE ===
# (eyes, mouth, frame_duration)
ANIM = [
    ("open", "big_smile", 60),
    ("half", "big_smile", 2),
    ("closed", "big_smile", 3),
    ("half", "big_smile", 2),
    ("open", "big_smile", 50),
    ("open", "smile", 40),
    ("wink_right", "smile", 12),
    ("open", "smile", 35),
    ("open", "big_smile", 55),
    ("closed", "big_smile", 4),
    ("open", "big_smile", 45),
    ("open", "neutral", 30),
    ("open", "smile", 40),
    ("wink_left", "big_smile", 12),
    ("open", "big_smile", 60),
]

idx = 0
cnt = 0

while True:
    apply_live_brightness(matrix)
    offscreen.Clear()
    eyes, mouth, dur = ANIM[idx]
    draw_jaylen(offscreen, eyes, mouth)
    offscreen = matrix.SwapOnVSync(offscreen)
    cnt += 1
    if cnt >= dur:
        cnt = 0
        idx = (idx + 1) % len(ANIM)
    time.sleep(0.05)
