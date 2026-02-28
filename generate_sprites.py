from PIL import Image, ImageDraw
import sys

def draw_lobster(draw, offset, frame):
    x, y = offset
    # base
    draw.rectangle([x+10, y+10, x+38, y+38], fill="#ff6b35")
    # eyes
    if frame == 1:
        draw.rectangle([x+16, y+18, x+22, y+20], fill="black")
        draw.rectangle([x+26, y+18, x+32, y+20], fill="black")
    else:
        draw.rectangle([x+16, y+16, x+22, y+22], fill="white")
        draw.rectangle([x+26, y+16, x+32, y+22], fill="white")
        draw.rectangle([x+18, y+18, x+20, y+20], fill="black")
        draw.rectangle([x+28, y+18, x+30, y+20], fill="black")
    # legs (animate if walking)
    if frame == 2:
        draw.rectangle([x+16, y+38, x+20, y+44], fill="#ff6b35")
    elif frame == 3:
        draw.rectangle([x+28, y+38, x+32, y+44], fill="#ff6b35")
    else:
        draw.rectangle([x+14, y+38, x+20, y+44], fill="#ff6b35")
        draw.rectangle([x+28, y+38, x+34, y+44], fill="#ff6b35")

def draw_robot(draw, offset, frame):
    x, y = offset
    draw.rectangle([x+10, y+12, x+38, y+36], fill="#78909c", outline="#455a64", width=2)
    # eyes
    if frame == 1:
        draw.rectangle([x+16, y+20, x+22, y+22], fill="#455a64")
        draw.rectangle([x+26, y+20, x+32, y+22], fill="#455a64")
    else:
        draw.rectangle([x+16, y+18, x+22, y+24], fill="#64ffda")
        draw.rectangle([x+26, y+18, x+32, y+24], fill="#64ffda")
    
    draw.rectangle([x+22, y+6, x+26, y+12], fill="#ff5252") # antenna
    # tracks
    if frame == 2:
        draw.rectangle([x+14, y+36, x+22, y+42], fill="#455a64")
    elif frame == 3:
        draw.rectangle([x+26, y+36, x+34, y+42], fill="#455a64")
    else:
        draw.rectangle([x+14, y+36, x+20, y+42], fill="#455a64")
        draw.rectangle([x+28, y+36, x+34, y+42], fill="#455a64")

def draw_cat(draw, offset, frame):
    x, y = offset
    # ears
    draw.polygon([(x+10, y+16), (x+16, y+20), (x+10, y+24)], fill="#ffb74d")
    draw.polygon([(x+38, y+16), (x+32, y+20), (x+38, y+24)], fill="#ffb74d")
    # body
    draw.rectangle([x+14, y+16, x+34, y+38], fill="#ffe0b2")
    # eyes
    if frame == 1:
        draw.rectangle([x+18, y+26, x+22, y+27], fill="black")
        draw.rectangle([x+26, y+26, x+30, y+27], fill="black")
    else:
        draw.ellipse([x+18, y+24, x+22, y+28], fill="black")
        draw.ellipse([x+26, y+24, x+30, y+28], fill="black")
    # nose
    draw.polygon([(x+24, y+30), (x+22, y+28), (x+26, y+28)], fill="#ef5350")
    # paws
    if frame == 2:
        draw.rectangle([x+18, y+38, x+22, y+44], fill="#ffb74d")
    elif frame == 3:
        draw.rectangle([x+26, y+38, x+30, y+44], fill="#ffb74d")
    else:
        draw.rectangle([x+16, y+38, x+22, y+44], fill="#ffb74d")
        draw.rectangle([x+26, y+38, x+32, y+44], fill="#ffb74d")

def make_sheet(name, draw_func):
    img = Image.new("RGBA", (48*4, 48), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    for i in range(4):
        draw_func(draw, (i*48, 0), i)
    img.save(f"/home/jason/.openclaw/workspace/star-office-ui/frontend/{name}.png")

make_sheet("lobster", draw_lobster)
make_sheet("robot", draw_robot)
make_sheet("cat", draw_cat)
print("Spritesheets generated!")
