import os
import time
from datetime import datetime
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")

opts = RGBMatrixOptions()
opts.rows = 32
opts.cols = 64
matrix = RGBMatrix(options=opts)
offscreen = matrix.CreateFrameCanvas()

# Fonts
font_tiny = graphics.Font()
font_tiny.LoadFont(os.path.join(FONT_DIR, "tom-thumb.bdf"))

font_small = graphics.Font()
font_small.LoadFont(os.path.join(FONT_DIR, "5x7.bdf"))

font_med = graphics.Font()
font_med.LoadFont(os.path.join(FONT_DIR, "6x9.bdf"))

# Colors
color_class = graphics.Color(255, 255, 255)
color_time = graphics.Color(60, 180, 255)
color_type = graphics.Color(140, 140, 160)
color_no_class = graphics.Color(80, 80, 100)

# Status label colors
label_colors = [
    (120, 120, 160),   # PREV - grayish blue
    (255, 180, 60),    # NOW - bright amber
    (60, 180, 255),    # NEXT - cyan
]

# Schedule
schedule = [
    {"day": 0, "start": "08:30", "end": "11:20", "name": "SYDE 192L", "type": "LAB", "room": "E5 6007"},
    {"day": 0, "start": "12:30", "end": "13:20", "name": "GENE 120", "type": "SEM", "room": "RCH 105"},
    {"day": 0, "start": "12:30", "end": "13:20", "name": "SYDE 102", "type": "SEM", "room": "RCH 105"},
    {"day": 0, "start": "13:30", "end": "14:20", "name": "SYDE 112", "type": "LEC", "room": "RCH 105"},
    {"day": 0, "start": "14:30", "end": "15:20", "name": "SYDE 192", "type": "LEC", "room": "RCH 105"},
    {"day": 0, "start": "15:30", "end": "16:20", "name": "SYDE 223", "type": "LEC", "room": "RCH 105"},
    {"day": 1, "start": "10:30", "end": "11:20", "name": "SYDE 112", "type": "TUT", "room": "RCH 105"},
    {"day": 1, "start": "12:30", "end": "14:20", "name": "SYDE 162", "type": "LEC", "room": "RCH 105"},
    {"day": 1, "start": "14:30", "end": "16:20", "name": "SYDE 114", "type": "LEC", "room": "RCH 105"},
    {"day": 2, "start": "12:30", "end": "13:20", "name": "SYDE 223", "type": "TUT", "room": "RCH 105"},
    {"day": 2, "start": "13:30", "end": "14:20", "name": "SYDE 112", "type": "LEC", "room": "RCH 105"},
    {"day": 2, "start": "14:30", "end": "15:20", "name": "SYDE 192", "type": "LEC", "room": "RCH 105"},
    {"day": 2, "start": "15:30", "end": "16:20", "name": "SYDE 223", "type": "LEC", "room": "RCH 105"},
    {"day": 3, "start": "12:30", "end": "13:20", "name": "SYDE 162", "type": "LEC", "room": "RCH 105"},
    {"day": 3, "start": "13:30", "end": "14:20", "name": "SYDE 162", "type": "TUT", "room": "RCH 105"},
    {"day": 3, "start": "14:30", "end": "16:20", "name": "SYDE 114", "type": "TUT", "room": "RCH 105"},
    {"day": 4, "start": "12:30", "end": "13:20", "name": "SYDE 192", "type": "TUT", "room": "RCH 105"},
    {"day": 4, "start": "13:30", "end": "14:20", "name": "SYDE 112", "type": "LEC", "room": "RCH 105"},
    {"day": 4, "start": "14:30", "end": "15:20", "name": "SYDE 192", "type": "LEC", "room": "RCH 105"},
    {"day": 4, "start": "15:30", "end": "16:20", "name": "SYDE 223", "type": "LEC", "room": "RCH 105"},
]

def time_to_minutes(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m

def get_todays_classes():
    now = datetime.now()
    today = now.weekday()
    todays = [c for c in schedule if c["day"] == today]
    return sorted(todays, key=lambda c: time_to_minutes(c["start"]))

def find_class_context():
    now = datetime.now()
    current_mins = now.hour * 60 + now.minute
    todays = get_todays_classes()
    
    if not todays:
        return None, None, None
    
    prev_class, curr_class, next_class = None, None, None
    
    for i, c in enumerate(todays):
        start = time_to_minutes(c["start"])
        end = time_to_minutes(c["end"])
        
        if start <= current_mins < end:
            curr_class = c
            prev_class = todays[i - 1] if i > 0 else None
            next_class = todays[i + 1] if i < len(todays) - 1 else None
            break
        elif current_mins < start:
            next_class = c
            prev_class = todays[i - 1] if i > 0 else None
            break
        else:
            prev_class = c
    
    return prev_class, curr_class, next_class

def draw_slot(canvas, cls, label, label_idx, x_offset):
    """Draw a class slot at given x offset. No pulsing - solid colors."""
    center_x = 32 + x_offset
    
    # Static label color (no pulsing)
    base = label_colors[label_idx]
    label_color = graphics.Color(base[0], base[1], base[2])
    
    # Draw label
    label_x = center_x - (len(label) * 5) // 2
    graphics.DrawText(canvas, font_small, label_x, 6, label_color, label)
    
    if cls:
        # Class name
        name = cls["name"]
        name_x = center_x - (len(name) * 6) // 2
        graphics.DrawText(canvas, font_med, name_x, 14, color_class, name)
        
        # Type
        type_str = cls["type"]
        type_x = center_x - (len(type_str) * 4) // 2
        graphics.DrawText(canvas, font_tiny, type_x, 20, color_type, type_str)
        
        # Time
        time_str = f"{cls['start']}-{cls['end']}"
        time_x = center_x - (len(time_str) * 5) // 2
        graphics.DrawText(canvas, font_small, time_x, 28, color_time, time_str)
    else:
        msg = "NO CLASS"
        msg_x = center_x - (len(msg) * 6) // 2
        graphics.DrawText(canvas, font_med, msg_x, 16, color_no_class, msg)

def draw_dots(canvas, current, y):
    dot_spacing = 8
    start_x = 32 - (3 * dot_spacing) // 2
    for i in range(3):
        x = start_x + i * dot_spacing
        if i == current:
            canvas.SetPixel(x, y, 255, 180, 60)
            canvas.SetPixel(x + 1, y, 255, 180, 60)
        else:
            canvas.SetPixel(x, y, 50, 50, 60)
            canvas.SetPixel(x + 1, y, 50, 50, 60)

# Animation state
SCREEN_WIDTH = 64
HOLD_FRAMES = 60       # frames to hold before sliding (~4 sec)
SCROLL_SPEED = 1       # 1 pixel per frame (slow, visible movement)

display_order = [1, 2, 0]  # NOW -> NEXT -> PREV (indices into classes list)
labels = ["PREV", "NOW", "NEXT"]
current_slot = 0           # which slot in display_order we're showing
scroll_x = 0               # integer pixel position
hold_counter = 0
is_sliding = False

while True:
    offscreen.Clear()
    
    prev_class, curr_class, next_class = find_class_context()
    classes = [prev_class, curr_class, next_class]
    
    # State machine: hold or slide
    if not is_sliding:
        # Holding
        hold_counter += 1
        if hold_counter >= HOLD_FRAMES:
            is_sliding = True
            hold_counter = 0
            scroll_x = 0
    else:
        # Sliding - move 1 pixel at a time (slow, choppy)
        scroll_x -= SCROLL_SPEED
        
        if scroll_x <= -SCREEN_WIDTH:
            # Slide complete
            is_sliding = False
            current_slot = (current_slot + 1) % 3
            scroll_x = 0
    
    # Get class indices
    current_idx = display_order[current_slot]
    next_slot_idx = (current_slot + 1) % 3
    next_idx = display_order[next_slot_idx]
    
    # ALWAYS draw both slots - current and next
    # Current slot position
    draw_slot(offscreen, classes[current_idx], labels[current_idx], current_idx, scroll_x)
    
    # Next slot (to the right of current)
    next_x = SCREEN_WIDTH + scroll_x
    draw_slot(offscreen, classes[next_idx], labels[next_idx], next_idx, next_x)
    
    # Pagination dots (always visible)
    draw_dots(offscreen, current_slot, 31)
    
    offscreen = matrix.SwapOnVSync(offscreen)
    time.sleep(0.08)  # ~12fps for choppy LED feel
