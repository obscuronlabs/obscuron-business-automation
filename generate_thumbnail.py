from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1280, 960

# Colors
BG = (10, 10, 15)
PURPLE = (108, 95, 255)
PINK = (255, 107, 157)
WHITE = (255, 255, 255)
GREEN = (72, 199, 142)
GRAY = (150, 150, 170)
DARK_CARD = (20, 20, 35)
PURPLE_BUBBLE = (80, 65, 200)

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# --- Background subtle gradient overlay (top strip) ---
for y in range(300):
    alpha = int(30 * (1 - y / 300))
    draw.line([(0, y), (W, y)], fill=(108, 95, 255, alpha) if False else (
        max(10, 10 + int(20 * (1 - y/300))),
        max(10, 10 + int(5 * (1 - y/300))),
        max(15, 15 + int(40 * (1 - y/300)))
    ))

# --- Decorative accent circles ---
draw.ellipse([-100, -100, 300, 300], fill=(30, 20, 80))
draw.ellipse([1050, -80, 1450, 320], fill=(80, 20, 60))

# --- Font loading (fallback to default) ---
def load_font(size, bold=False):
    font_paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()

font_small = load_font(28)
font_medium = load_font(48)
font_large = load_font(110, bold=True)
font_xlarge = load_font(80, bold=True)
font_sub = load_font(62)
font_check = load_font(42)
font_price = load_font(100, bold=True)
font_url = load_font(30)
font_bubble = load_font(36)

def center_x(text, font, y, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), text, font=font, fill=color)

# --- Top label ---
label = "Obscuron AI Chat"
bbox = draw.textbbox((0, 0), label, font=font_small)
lw = bbox[2] - bbox[0]
lh = bbox[3] - bbox[1]
pad = 10
rx, ry = (W - lw) // 2 - pad, 52
draw.rounded_rectangle([rx, ry, rx + lw + pad*2, ry + lh + pad*2], radius=20, fill=(30, 24, 80), outline=PURPLE, width=2)
draw.text((rx + pad, ry + pad), label, font=font_small, fill=PURPLE)

# --- Main headline ---
center_x("24/7 AI Chatbot", font_large, 120, WHITE)

# --- Subheadline ---
center_x("For Your Website", font_sub, 250, (210, 210, 230))

# --- Divider line ---
draw.line([(W//2 - 200, 340), (W//2 + 200, 340)], fill=PURPLE, width=2)

# --- Checkmarks ---
checks = [
    "  Live in 3 Days",
    "  Any Website Platform",
    "  No Monthly SaaS Fees",
]
cy = 368
for check in checks:
    full = "✓" + check
    bbox = draw.textbbox((0, 0), full, font=font_check)
    tw = bbox[2] - bbox[0]
    tx = (W - tw) // 2
    # draw checkmark in green, rest in white
    check_bbox = draw.textbbox((tx, cy), "✓", font=font_check)
    draw.text((tx, cy), "✓", font=font_check, fill=GREEN)
    rest_bbox = draw.textbbox((0, 0), "✓", font=font_check)
    rest_x = tx + rest_bbox[2] - rest_bbox[0]
    draw.text((rest_x, cy), check, font=font_check, fill=WHITE)
    cy += 60

# --- Chat bubble mockup ---
bubble_y = 570
bubble_x = W // 2 - 320
bubble_w = 640
bubble_h = 90

# Avatar circle
draw.ellipse([bubble_x - 60, bubble_y + 10, bubble_x - 10, bubble_y + 60], fill=PURPLE)
draw.text((bubble_x - 50, bubble_y + 18), "AI", font=load_font(26, bold=True), fill=WHITE)

# Bubble background
draw.rounded_rectangle([bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h],
                        radius=20, fill=PURPLE_BUBBLE)
# Bubble tail
draw.polygon([
    (bubble_x + 20, bubble_y + bubble_h - 10),
    (bubble_x - 10, bubble_y + bubble_h + 20),
    (bubble_x + 50, bubble_y + bubble_h - 10),
], fill=PURPLE_BUBBLE)

bubble_text = "Hi! How can I help you today?"
tb = draw.textbbox((0, 0), bubble_text, font=font_bubble)
tw = tb[2] - tb[0]
th = tb[3] - tb[1]
draw.text((bubble_x + (bubble_w - tw) // 2, bubble_y + (bubble_h - th) // 2), bubble_text, font=font_bubble, fill=WHITE)

# Second bubble (user reply stub) - smaller, right aligned
reply_x = W // 2 + 50
reply_y = bubble_y + 110
reply_w = 260
reply_h = 55
draw.rounded_rectangle([reply_x, reply_y, reply_x + reply_w, reply_y + reply_h],
                        radius=15, fill=(40, 40, 60))
draw.text((reply_x + 20, reply_y + 12), "Tell me more...", font=load_font(28), fill=GRAY)

# --- Price tag: gradient simulation ---
price_text = "$45"
price_x = W - 200
price_y = H - 200

# Simulate gradient by drawing multiple colored layers
pb = draw.textbbox((0, 0), price_text, font=font_price)
pw = pb[2] - pb[0]
ph = pb[3] - pb[1]
px = W - pw - 60
py = H - ph - 80

# Draw shadow
draw.text((px + 4, py + 4), price_text, font=font_price, fill=(0, 0, 0))
# Draw gradient-like effect by layering
for i in range(ph):
    t = i / ph
    r = int(108 + (255 - 108) * t)
    g = int(95 + (107 - 95) * t)
    b = int(255 + (157 - 255) * t)
    # clip horizontally using a mask approach - draw line by line
    draw.text((px, py - i + ph), price_text, font=font_price, fill=(r, g, b))

# Redraw cleanly with solid purple (gradient approximation looks good enough)
draw.text((px, py), price_text, font=font_price, fill=PURPLE)
# Overlay pink tint on top half
for i in range(ph // 2):
    t = i / (ph // 2)
    r = int(108 * (1-t) + 255 * t)
    g = int(95 * (1-t) + 107 * t)
    b = int(255 * (1-t) + 157 * t)

# Use a simpler approach: just draw with PURPLE and add a pink accent label
draw.text((px, py), price_text, font=font_price, fill=PURPLE)
draw.text((px + 2, py), price_text, font=font_price, fill=(180, 100, 255))  # slight shimmer

# "starting at" label above price
start_label = "Starting at"
draw.text((px, py - 36), start_label, font=load_font(28), fill=GRAY)

# --- Bottom URL ---
url = "obscuronlabs.com"
ub = draw.textbbox((0, 0), url, font=font_url)
uw = ub[2] - ub[0]
draw.text(((W - uw) // 2, H - 50), url, font=font_url, fill=GRAY)

# --- Bottom divider ---
draw.line([(60, H - 65), (W - 60, H - 65)], fill=(40, 40, 60), width=1)

# --- Purple glow line at top ---
for i in range(4):
    alpha_color = (108, 95, 255) if i == 0 else (80, 65, 200)
    draw.line([(0, i), (W, i)], fill=alpha_color)

out_path = "/home/user/obscuron-business-automation/gig_thumbnail.png"
img.save(out_path, "PNG")
print(f"Saved to {out_path}")
import os
size = os.path.getsize(out_path)
print(f"File size: {size:,} bytes")
print(f"Image size: {img.size}")
