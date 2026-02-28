import os

frontend_dir = "/home/jason/.openclaw/workspace/star-office-ui/frontend"

avatars = {
    "lobster_open.svg": """<svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="5" y="5" width="14" height="14" rx="2" fill="#ff6b35"/>
<rect x="8" y="8" width="3" height="3" fill="white"/>
<rect x="13" y="8" width="3" height="3" fill="white"/>
<rect x="9" y="9" width="1" height="1" fill="black"/>
<rect x="14" y="9" width="1" height="1" fill="black"/>
<rect x="7" y="16" width="3" height="3" fill="#ff6b35"/>
<rect x="14" y="16" width="3" height="3" fill="#ff6b35"/>
</svg>""",
    "lobster_closed.svg": """<svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="5" y="5" width="14" height="14" rx="2" fill="#ff6b35"/>
<rect x="8" y="9" width="3" height="1" fill="black"/>
<rect x="13" y="9" width="3" height="1" fill="black"/>
<rect x="7" y="16" width="3" height="3" fill="#ff6b35"/>
<rect x="14" y="16" width="3" height="3" fill="#ff6b35"/>
</svg>""",
    "robot_open.svg": """<svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="5" y="6" width="14" height="12" rx="3" fill="#78909c"/>
<rect x="8" y="9" width="3" height="3" fill="#64ffda"/>
<rect x="13" y="9" width="3" height="3" fill="#64ffda"/>
<rect x="11" y="4" width="2" height="2" fill="#ff5252"/>
</svg>""",
    "robot_closed.svg": """<svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="5" y="6" width="14" height="12" rx="3" fill="#78909c"/>
<rect x="8" y="10" width="3" height="1" fill="#455a64"/>
<rect x="13" y="10" width="3" height="1" fill="#455a64"/>
<rect x="11" y="4" width="2" height="2" fill="#ff5252"/>
</svg>""",
    "cat_open.svg": """<svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M5 8 L8 10 L16 10 L19 8 L17 19 L7 19 Z" fill="#ffe0b2"/>
<polygon points="5,8 8,10 5,12" fill="#ffb74d"/>
<polygon points="19,8 16,10 19,12" fill="#ffb74d"/>
<circle cx="9" cy="13" r="1.5" fill="black"/>
<circle cx="15" cy="13" r="1.5" fill="black"/>
<path d="M12 15 L11 14 L13 14 Z" fill="#ef5350"/>
</svg>""",
    "cat_closed.svg": """<svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M5 8 L8 10 L16 10 L19 8 L17 19 L7 19 Z" fill="#ffe0b2"/>
<polygon points="5,8 8,10 5,12" fill="#ffb74d"/>
<polygon points="19,8 16,10 19,12" fill="#ffb74d"/>
<rect x="8" y="13" width="2" height="0.5" fill="black"/>
<rect x="14" y="13" width="2" height="0.5" fill="black"/>
<path d="M12 15 L11 14 L13 14 Z" fill="#ef5350"/>
</svg>"""
}

for name, svg in avatars.items():
    with open(os.path.join(frontend_dir, name), "w") as f:
        f.write(svg)

print("Generated 6 SVG avatar images.")
