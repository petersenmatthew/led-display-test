import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

opts = RGBMatrixOptions()
opts.rows = 32
opts.cols = 64
matrix = RGBMatrix(options=opts)
offscreen = matrix.CreateFrameCanvas()

# Colors - higher contrast for visibility
WHITE = (255, 255, 255)
SKIN_HI = (180, 120, 85)
SKIN = (140, 92, 62)
SKIN_MID = (115, 75, 50)
SKIN_DK = (85, 55, 38)
SKIN_SH = (55, 36, 25)
HAIR = (22, 18, 15)
EYE_W = (245, 240, 235)
PUPIL = (15, 12, 10)
LIP = (95, 55, 50)
TEETH = (250, 248, 245)
JERSEY = (0, 130, 55)

def px(c, x, y, col):
    if 0 <= x < 64 and 0 <= y < 32:
        c.SetPixel(x, y, col[0], col[1], col[2])

def draw_jaylen(c, blink=False, smile=True):
    # White background
    for y in range(32):
        for x in range(64):
            px(c, x, y, WHITE)
    
    # ===== HAIR - full, short cut =====
    # Row 0-1: top of hair
    for x in range(20, 44):
        px(c, x, 0, HAIR)
        px(c, x, 1, HAIR)
    # Row 2-3: hair widens
    for x in range(17, 47):
        px(c, x, 2, HAIR)
        px(c, x, 3, HAIR)
    # Row 4-5: hair meets forehead
    for x in range(15, 49):
        px(c, x, 4, HAIR)
    for x in range(15, 49):
        # Hairline - slight curves
        if x < 20 or x > 43:
            px(c, x, 5, HAIR)
        elif x < 23 or x > 40:
            px(c, x, 5, HAIR)
    
    # ===== FOREHEAD =====
    for y in range(5, 9):
        for x in range(16, 48):
            if x < 20 or x > 43:
                px(c, x, y, SKIN_DK)
            elif x < 23 or x > 40:
                px(c, x, y, SKIN_MID)
            elif 28 <= x <= 35:
                px(c, x, y, SKIN_HI)  # highlight center
            else:
                px(c, x, y, SKIN)
    
    # ===== EYEBROWS - bold arches =====
    # Left brow
    for x in range(20, 28):
        y = 9 if 22 <= x <= 26 else 10
        px(c, x, y, HAIR)
    # Right brow  
    for x in range(36, 44):
        y = 9 if 37 <= x <= 41 else 10
        px(c, x, y, HAIR)
    
    # ===== EYES - large, expressive =====
    if blink:
        # Closed eyes
        for x in range(21, 28):
            px(c, x, 12, HAIR)
        for x in range(36, 43):
            px(c, x, 12, HAIR)
    else:
        # Left eye
        # White
        for dy in range(3):
            for dx in range(5):
                px(c, 21 + dx, 11 + dy, EYE_W)
        # Pupil - large and centered
        px(c, 23, 11, PUPIL)
        px(c, 22, 12, PUPIL)
        px(c, 23, 12, PUPIL)
        px(c, 24, 12, PUPIL)
        px(c, 23, 13, PUPIL)
        
        # Right eye
        for dy in range(3):
            for dx in range(5):
                px(c, 38 + dx, 11 + dy, EYE_W)
        px(c, 40, 11, PUPIL)
        px(c, 39, 12, PUPIL)
        px(c, 40, 12, PUPIL)
        px(c, 41, 12, PUPIL)
        px(c, 40, 13, PUPIL)
    
    # ===== FACE SIDES =====
    for y in range(9, 22):
        # Left side
        px(c, 14, y, SKIN_SH)
        px(c, 15, y, SKIN_DK)
        px(c, 16, y, SKIN_MID)
        # Right side
        px(c, 47, y, SKIN_MID)
        px(c, 48, y, SKIN_DK)
        px(c, 49, y, SKIN_SH)
    
    # ===== CHEEKS =====
    for y in range(11, 18):
        for x in range(17, 21):
            px(c, x, y, SKIN_MID)
        for x in range(21, 27):
            px(c, x, y, SKIN)
        for x in range(37, 43):
            px(c, x, y, SKIN)
        for x in range(43, 47):
            px(c, x, y, SKIN_MID)
    # Highlight on cheekbones
    for y in range(13, 16):
        px(c, 19, y, SKIN_HI)
        px(c, 20, y, SKIN_HI)
        px(c, 43, y, SKIN_HI)
        px(c, 44, y, SKIN_HI)
    
    # ===== NOSE - defined bridge and nostrils =====
    # Bridge
    for y in range(11, 17):
        px(c, 30, y, SKIN_MID)
        px(c, 31, y, SKIN_DK)
        px(c, 32, y, SKIN_DK)
        px(c, 33, y, SKIN_MID)
    # Tip highlight
    px(c, 31, 16, SKIN_HI)
    px(c, 32, 16, SKIN_HI)
    # Nostrils - wide
    px(c, 28, 17, SKIN_DK)
    px(c, 29, 17, SKIN_SH)
    px(c, 30, 17, SKIN_MID)
    px(c, 31, 17, SKIN)
    px(c, 32, 17, SKIN)
    px(c, 33, 17, SKIN_MID)
    px(c, 34, 17, SKIN_SH)
    px(c, 35, 17, SKIN_DK)
    
    # Center face fill
    for y in range(11, 17):
        for x in range(27, 30):
            px(c, x, y, SKIN)
        for x in range(34, 37):
            px(c, x, y, SKIN)
    
    # ===== MOUTH =====
    if smile:
        # Big smile with teeth
        # Upper lip
        for x in range(25, 39):
            px(c, x, 19, LIP)
        # Teeth row 1
        for x in range(26, 38):
            px(c, x, 20, TEETH)
        # Teeth row 2
        for x in range(27, 37):
            px(c, x, 21, TEETH)
        # Lower lip
        for x in range(26, 38):
            px(c, x, 22, LIP)
        # Smile corners curve up
        px(c, 24, 20, LIP)
        px(c, 39, 20, LIP)
    else:
        # Closed mouth
        for x in range(27, 37):
            px(c, x, 20, LIP)
            px(c, x, 21, LIP)
    
    # ===== LOWER FACE / JAW =====
    for y in range(18, 24):
        w = 15 - (y - 18)
        for x in range(32 - w, 32 + w):
            # Light stubble texture
            if (x + y) % 4 == 0:
                px(c, x, y, SKIN_DK)
            else:
                px(c, x, y, SKIN_MID)
    
    # Chin
    for x in range(28, 36):
        px(c, x, 24, SKIN_DK)
    for x in range(30, 34):
        px(c, x, 25, SKIN_SH)
    
    # ===== EARS =====
    for y in range(10, 17):
        px(c, 12, y, SKIN_DK)
        px(c, 13, y, SKIN_MID)
        px(c, 50, y, SKIN_MID)
        px(c, 51, y, SKIN_DK)
    
    # ===== NECK =====
    for y in range(24, 28):
        for x in range(26, 38):
            px(c, x, y, SKIN_SH)
    
    # ===== JERSEY =====
    for y in range(27, 32):
        for x in range(18, 46):
            px(c, x, y, JERSEY)

# Animation
frame = 0
while True:
    offscreen.Clear()
    
    # Blink every ~3 seconds
    blink = (frame % 60) < 3
    
    draw_jaylen(offscreen, blink=blink, smile=True)
    
    offscreen = matrix.SwapOnVSync(offscreen)
    frame += 1
    time.sleep(0.05)
