import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

opts = RGBMatrixOptions()
opts.rows = 32
opts.cols = 64
matrix = RGBMatrix(options=opts)
offscreen = matrix.CreateFrameCanvas()

# Photorealistic color palette - Jaylen Brown
# Background
WHITE = (255, 255, 255)
OFF_WHITE = (248, 246, 243)

# Skin tones - warm undertone, 8 shades for smooth gradients
S1 = (195, 140, 100)   # Brightest highlight
S2 = (175, 120, 85)    # Light
S3 = (155, 102, 72)    # Light-mid
S4 = (138, 90, 62)     # Mid (base)
S5 = (118, 76, 52)     # Mid-dark
S6 = (95, 62, 42)      # Dark
S7 = (72, 48, 32)      # Shadow
S8 = (52, 35, 24)      # Deep shadow

# Hair - subtle variation
H1 = (42, 35, 30)      # Hair highlight
H2 = (28, 23, 20)      # Hair mid
H3 = (18, 15, 13)      # Hair dark

# Beard - slightly warmer than hair
B1 = (48, 38, 32)      # Beard light
B2 = (35, 28, 24)      # Beard mid
B3 = (24, 20, 17)      # Beard dark
B4 = (16, 13, 11)      # Beard shadow

# Eyes
EW = (242, 238, 232)   # Eye white
EW_SH = (220, 215, 208) # Eye white shadow
IR1 = (55, 42, 35)     # Iris outer
IR2 = (38, 30, 25)     # Iris inner
PU = (12, 10, 8)       # Pupil
CATCH = (255, 252, 248) # Catchlight

# Lips
L1 = (125, 72, 65)     # Lip highlight
L2 = (105, 58, 52)     # Lip mid
L3 = (82, 48, 44)      # Lip dark
L4 = (62, 38, 35)      # Lip shadow

# Teeth
T1 = (250, 248, 244)   # Teeth bright
T2 = (235, 232, 226)   # Teeth shadow

# Nose
N1 = (45, 32, 25)      # Nostril

# Jersey
JG1 = (0, 135, 58)     # Jersey bright
JG2 = (0, 110, 48)     # Jersey mid
JG3 = (0, 85, 38)      # Jersey dark

def px(c, x, y, col):
    if 0 <= x < 64 and 0 <= y < 32:
        c.SetPixel(x, y, col[0], col[1], col[2])

def draw_jaylen(c, eyes="open", mouth="big_smile"):
    # === BACKGROUND ===
    for y in range(32):
        for x in range(64):
            px(c, x, y, WHITE)
    
    # === HAIR ===
    # Top rows - textured short hair
    hair_data = [
        # (y, x_start, x_end)
        (0, 24, 40), (1, 21, 43), (2, 19, 45), (3, 17, 47), (4, 16, 48), (5, 15, 49)
    ]
    for y, xs, xe in hair_data:
        for x in range(xs, xe):
            # Texture variation
            if (x * 3 + y * 7) % 5 == 0:
                px(c, x, y, H1)
            elif (x * 3 + y * 7) % 5 < 3:
                px(c, x, y, H2)
            else:
                px(c, x, y, H3)
    
    # Hairline - natural curve
    for x in range(15, 49):
        if x < 19 or x > 44:
            px(c, x, 6, H2)
        elif x < 22 or x > 41:
            px(c, x, 6, H3)
        elif 29 <= x <= 34:
            px(c, x, 6, H3)  # Slight widow's peak
    
    # === FOREHEAD ===
    # Row 6-9 with gradient lighting
    for y in range(6, 10):
        for x in range(16, 48):
            if x < 19 or x > 44:
                px(c, x, y, S7)
            elif x < 21 or x > 42:
                px(c, x, y, S6)
            elif x < 24 or x > 39:
                px(c, x, y, S5)
            elif 29 <= x <= 34 and y >= 7:
                px(c, x, y, S2)  # Forehead highlight
            elif 26 <= x <= 37:
                px(c, x, y, S3)
            else:
                px(c, x, y, S4)
    
    # === BROW RIDGE ===
    for x in range(20, 29):
        px(c, x, 9, S6 if x < 22 or x > 26 else S5)
    for x in range(35, 44):
        px(c, x, 9, S6 if x < 37 or x > 41 else S5)
    
    # === EYEBROWS ===
    # Left brow - natural arch
    brow_l = [(20,10), (21,9), (22,9), (23,9), (24,9), (25,9), (26,9), (27,10)]
    for x, y in brow_l:
        px(c, x, y, H3)
        if 22 <= x <= 25:
            px(c, x, y+1, H2)
    
    # Right brow
    brow_r = [(36,10), (37,9), (38,9), (39,9), (40,9), (41,9), (42,9), (43,10)]
    for x, y in brow_r:
        px(c, x, y, H3)
        if 38 <= x <= 41:
            px(c, x, y+1, H2)
    
    # === EYES ===
    if eyes == "closed":
        for x in range(21, 28):
            px(c, x, 12, S6)
            px(c, x, 13, S5)
        for x in range(36, 43):
            px(c, x, 12, S6)
            px(c, x, 13, S5)
    elif eyes == "half":
        for x in range(21, 28):
            px(c, x, 11, S6)
            px(c, x, 12, EW_SH)
            px(c, x, 13, IR2 if 23 <= x <= 25 else EW)
        for x in range(36, 43):
            px(c, x, 11, S6)
            px(c, x, 12, EW_SH)
            px(c, x, 13, IR2 if 38 <= x <= 40 else EW)
    else:
        # LEFT EYE - detailed
        # Eye socket shadow
        for x in range(20, 28):
            px(c, x, 10, S6)
        
        # Eye white with realistic shading
        for x in range(21, 27):
            px(c, x, 11, EW_SH)  # Top shadow from lid
            px(c, x, 12, EW)
            px(c, x, 13, EW)
            px(c, x, 14, EW_SH)  # Bottom shadow
        
        # Iris - gradient
        px(c, 23, 11, IR1)
        px(c, 24, 11, IR1)
        px(c, 22, 12, IR1)
        px(c, 23, 12, IR2)
        px(c, 24, 12, PU)  # Pupil center
        px(c, 25, 12, IR2)
        px(c, 22, 13, IR1)
        px(c, 23, 13, IR2)
        px(c, 24, 13, IR2)
        px(c, 25, 13, IR1)
        px(c, 23, 14, IR1)
        px(c, 24, 14, IR1)
        
        # Catchlight
        px(c, 23, 11, CATCH)
        
        # Upper eyelid crease
        for x in range(21, 27):
            px(c, x, 10, S5)
        
        # RIGHT EYE
        for x in range(36, 43):
            px(c, x, 10, S6)
        
        for x in range(37, 43):
            px(c, x, 11, EW_SH)
            px(c, x, 12, EW)
            px(c, x, 13, EW)
            px(c, x, 14, EW_SH)
        
        px(c, 39, 11, IR1)
        px(c, 40, 11, IR1)
        px(c, 38, 12, IR1)
        px(c, 39, 12, IR2)
        px(c, 40, 12, PU)
        px(c, 41, 12, IR2)
        px(c, 38, 13, IR1)
        px(c, 39, 13, IR2)
        px(c, 40, 13, IR2)
        px(c, 41, 13, IR1)
        px(c, 39, 14, IR1)
        px(c, 40, 14, IR1)
        
        px(c, 39, 11, CATCH)
        
        for x in range(37, 43):
            px(c, x, 10, S5)
    
    # === CHEEKS ===
    for y in range(10, 17):
        # Left side - gradient from edge to center
        px(c, 14, y, S8)
        px(c, 15, y, S7)
        px(c, 16, y, S6)
        px(c, 17, y, S6)
        px(c, 18, y, S5)
        px(c, 19, y, S5)
        px(c, 20, y, S4)
        
        # Right side
        px(c, 43, y, S4)
        px(c, 44, y, S5)
        px(c, 45, y, S5)
        px(c, 46, y, S6)
        px(c, 47, y, S6)
        px(c, 48, y, S7)
        px(c, 49, y, S8)
    
    # Cheekbone highlights
    for y in range(12, 15):
        px(c, 19, y, S2)
        px(c, 20, y, S3)
        px(c, 43, y, S3)
        px(c, 44, y, S2)
    
    # Mid-face fill
    for y in range(10, 17):
        for x in range(28, 36):
            px(c, x, y, S4)
    
    # === NOSE ===
    # Bridge with shadow
    for y in range(11, 16):
        px(c, 30, y, S5)
        px(c, 31, y, S6)
        px(c, 32, y, S6)
        px(c, 33, y, S5)
    
    # Nose tip highlight
    px(c, 31, 15, S2)
    px(c, 32, 15, S2)
    
    # Nose base and nostrils
    for x in range(28, 36):
        px(c, x, 16, S5)
    px(c, 29, 16, N1)
    px(c, 30, 16, S7)
    px(c, 33, 16, S7)
    px(c, 34, 16, N1)
    
    # Nose wings
    px(c, 28, 15, S6)
    px(c, 35, 15, S6)
    
    # === BEARD ===
    # Beard on jaw and chin - realistic texture
    for y in range(16, 25):
        # Width narrows toward chin
        if y < 18:
            w = 15
        elif y < 20:
            w = 14
        elif y < 22:
            w = 12
        elif y < 24:
            w = 9
        else:
            w = 5
        
        for x in range(32 - w, 32 + w):
            # Skip mouth area
            if 18 <= y <= 22 and 26 <= x <= 37:
                continue
            
            # Beard texture pattern
            pattern = (x * 7 + y * 11) % 7
            if pattern == 0:
                px(c, x, y, B4)
            elif pattern < 3:
                px(c, x, y, B3)
            elif pattern < 5:
                px(c, x, y, B2)
            else:
                px(c, x, y, B1)
    
    # Beard on cheeks/sideburns
    for y in range(14, 22):
        for dx in range(3):
            x_l = 15 + dx
            x_r = 48 - dx
            pattern = (x_l + y) % 4
            col = [B4, B3, B2, B1][pattern]
            px(c, x_l, y, col)
            px(c, x_r, y, col)
    
    # Mustache
    for x in range(27, 37):
        px(c, x, 17, B3)
        if 29 <= x <= 34:
            px(c, x, 18, B2)
    
    # === MOUTH ===
    if mouth == "big_smile":
        # Upper lip
        for x in range(25, 39):
            px(c, x, 18, L4)
        for x in range(26, 38):
            px(c, x, 19, L3)
        
        # Teeth - realistic with slight shadow
        for x in range(27, 37):
            px(c, x, 19, T1)
            px(c, x, 20, T1)
        for x in range(28, 36):
            px(c, x, 21, T2)
        
        # Lower lip
        for x in range(26, 38):
            px(c, x, 22, L2)
        for x in range(27, 37):
            px(c, x, 23, L3)
        
        # Mouth corners
        px(c, 24, 19, L4)
        px(c, 25, 20, L4)
        px(c, 38, 19, L4)
        px(c, 39, 20, L4)
        
    elif mouth == "smile":
        for x in range(27, 37):
            px(c, x, 18, L4)
        for x in range(28, 36):
            px(c, x, 19, T1)
            px(c, x, 20, L2)
        px(c, 26, 19, L4)
        px(c, 37, 19, L4)
    else:
        for x in range(28, 36):
            px(c, x, 19, L2)
            px(c, x, 20, L3)
    
    # === EARS ===
    for y in range(11, 17):
        px(c, 12, y, S7)
        px(c, 13, y, S6)
        px(c, 50, y, S6)
        px(c, 51, y, S7)
    # Ear detail
    px(c, 13, 13, S5)
    px(c, 50, 13, S5)
    
    # === NECK ===
    for y in range(24, 28):
        for x in range(25, 39):
            px(c, x, y, S8)
    
    # === JERSEY ===
    for y in range(27, 32):
        for x in range(17, 47):
            if y == 27:
                px(c, x, y, JG3)
            elif x < 22 or x > 41:
                px(c, x, y, JG2)
            else:
                px(c, x, y, JG1)

# Animation
ANIM = [
    ("open", "big_smile", 70),
    ("half", "big_smile", 3),
    ("closed", "big_smile", 3),
    ("half", "big_smile", 3),
    ("open", "big_smile", 55),
    ("open", "smile", 45),
    ("open", "big_smile", 60),
    ("closed", "smile", 4),
    ("open", "smile", 40),
    ("open", "neutral", 35),
    ("open", "smile", 45),
    ("open", "big_smile", 65),
]

idx = 0
cnt = 0

while True:
    offscreen.Clear()
    
    eyes, mouth, dur = ANIM[idx]
    draw_jaylen(offscreen, eyes, mouth)
    
    offscreen = matrix.SwapOnVSync(offscreen)
    
    cnt += 1
    if cnt >= dur:
        cnt = 0
        idx = (idx + 1) % len(ANIM)
    
    time.sleep(0.05)
