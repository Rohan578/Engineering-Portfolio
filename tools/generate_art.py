#!/usr/bin/env python3
"""
generate_art.py — builds the pixel-art images used by the site.

    python3 tools/generate_art.py

Writes two files:
    assets/hero-scene.svg   the homepage banner: an armored hero sitting on a
                            cliff above the ocean, under a starry night sky
    assets/starfield.svg    a small repeating tile of pixel stars used as the
                            page background behind the content

How the drawing works
---------------------
The banner is a grid of W x H "pixels" (each one becomes a 1x1 <rect> in the
SVG, which the browser scales up with crisp edges). You draw into that grid
with a few helpers:

    put(x, y, color)            one pixel
    rect(x, y, w, h, color)     a filled block
    sprite(rows, x, y, palette) a small picture drawn from text rows, where each
                                character maps to a color in `palette`
                                ("." or any unmapped character = transparent)
    animated(x, y, color, cls)  a pixel that gets a CSS class so it can
                                twinkle / glow (animations are defined in
                                SCENE_CSS below)

Everything is drawn back-to-front: sky, stars, moon, ocean, cliff, hero.
Change a section, re-run the script, and refresh the page.

Only the Python standard library is needed.
"""

import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_SCENE = os.path.join(ROOT, "assets", "hero-scene.svg")
OUT_STARS = os.path.join(ROOT, "assets", "starfield.svg")

# ---------------------------------------------------------------------------
# Scene layout (all values in scene pixels)
# ---------------------------------------------------------------------------
W, H = 200, 90        # size of the pixel grid
HORIZON = 64          # y of the ocean surface
CLIFF_TOP = 54        # y of the grass on the cliff
EDGE = 74             # x where the cliff top ends (the hero sits here)
MOON = (160, 14, 7)   # crescent moon: center x, center y, radius

SEED = 26             # change to reshuffle all the random stars/waves

# Color palettes ------------------------------------------------------------
SKY = ["#05040f", "#08061a", "#0b0922", "#0f0c2c", "#141036", "#1a1442", "#21184d", "#2a1d57"]
MILKY_WAY = ["#2a2160", "#33296e", "#3d3280", "#4a3c8f"]
STAR_COLORS = ["#ffffff", "#fff1c9", "#c8d4ff", "#e2d4ff"]
SEA = ["#0d1640", "#0b1338", "#0a1131", "#080e29", "#070b22", "#06091c"]
WAVES = ["#1d2a66", "#24357a", "#2f4590"]
MOON_GLINT = ["#f2d98a", "#fff3c4", "#c9a956"]
ROCK = ["#2b2440", "#241e38", "#1e1930", "#181428"]
GRASS = {"top": "#2f7d4a", "mid": "#235f3a", "dark": "#1a462c", "blade": "#3f9a5c"}

# The hero. Each letter below is a color; "." is transparent.
# He sits on the cliff edge facing the sea (right), head tilted up at the moon.
# Curly dark hair + sunglasses (Rohan), steel plate armor with gold trim,
# a violet cape draped on the grass behind him, armored legs over the edge.
HERO = [
    "....hHH.Hh.H........",
    "...HHhHHHHhHH.......",
    "..hHHHHHHHHHHH......",
    "..HHHHHHHHHHSSS.....",
    ".hHHHHHHHHGGGGS.....",
    "..HHHHHHHHSGgGSS....",
    "...HHHHHHHSSSSSS....",
    "....HHHHsSSSSSs.....",
    ".....HHsSSsss.......",
    "....cCTTTTTTT.......",
    "...cCPPPLAAAAT......",
    "..cCPPPPLLAAaT......",
    "..cCPTPPAALAaAs.....",
    ".cCCaPPATAAAaaAs....",
    ".cCCKKKKTKKKKAAs....",
    "cCCC.aAAAAAAAAAAA...",
    "cCCcc.aaaTaaaaaaAA..",
    ".............AAa....",
    ".............LAa....",
    ".............AAa....",
    ".............TTT....",
    "............KKKk....",
    "............KKKKk...",
]
HERO_PALETTE = {
    "H": "#1b1412", "h": "#3a2a22",   # curly black hair + highlights
    "S": "#c68b5e", "s": "#a46e48",   # skin + shadow
    "G": "#0b0b14", "g": "#8fb0ff",   # sunglasses + lens glint
    "A": "#b8c2d6", "a": "#7d88a3",   # steel armor + shadow
    "L": "#eef3ff",                   # armor highlight (moonlight)
    "P": "#9aa6c2",                   # pauldron (shoulder plate)
    "T": "#e0b65a",                   # gold trim
    "C": "#7b3fc4", "c": "#4e2585",   # violet cape + shadow
    "K": "#5a3a1c", "k": "#3d2612",   # leather belt / boots
}
HERO_SEAT_ROW = 17     # sprite row that sits level with the grass
HERO_LEG_COLUMN = 13   # sprite column where his legs go over the edge

# Round shield leaning on the grass beside him
SHIELD = [
    "..TTTT..",
    ".TBBBBT.",
    "TBBYYBBT",
    "TBYYYYBT",
    "TBBYYBBT",
    ".TBBBBT.",
    "..TTTT..",
]
SHIELD_PALETTE = {"T": "#e0b65a", "B": "#2c4a8c", "Y": "#f2d98a"}


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
grid = {}       # (x, y) -> color for static pixels
animated_px = []  # (x, y, w, h, color, css_class) for pixels that animate
rng = random.Random(SEED)


def put(x, y, color):
    """Set one static pixel (ignored if off the canvas)."""
    if 0 <= x < W and 0 <= y < H:
        grid[(x, y)] = color


def rect(x, y, w, h, color):
    """Fill a w x h block of static pixels."""
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            put(xx, yy, color)


def sprite(rows, x0, y0, palette):
    """Draw a text-art sprite: each character is looked up in `palette`."""
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch in palette:
                put(x0 + dx, y0 + dy, palette[ch])


def animated(x, y, color, css_class, w=1, h=1):
    """Add a pixel (or short bar) that animates via a CSS class."""
    animated_px.append((x, y, w, h, color, css_class))


# ---------------------------------------------------------------------------
# 1. Sky: banded gradient with dithered seams
# ---------------------------------------------------------------------------
def draw_sky():
    band_h = HORIZON / len(SKY)
    for y in range(HORIZON):
        i = min(int(y / band_h), len(SKY) - 1)
        progress = y / band_h - i
        nxt = SKY[min(i + 1, len(SKY) - 1)]
        for x in range(W):
            # checkerboard dither into the next band near each seam
            if progress > 0.8 and (x + y) % 2 == 0:
                put(x, y, nxt)
            elif progress > 0.6 and (x + 2 * y) % 4 == 0:
                put(x, y, nxt)
            else:
                put(x, y, SKY[i])


# ---------------------------------------------------------------------------
# 2. Milky Way band, nebula clouds, and a tiny spiral galaxy
# ---------------------------------------------------------------------------
def draw_milky_way():
    x1, y1, x2, y2 = 0, 4, 200, 46            # the band runs along this line

    def distance(x, y):
        return abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / math.hypot(y2 - y1, x2 - x1)

    for y in range(HORIZON - 6):
        for x in range(W):
            width = 6 + 3 * math.sin(x / 13.0) + 2 * math.sin(x / 5.3)
            d = distance(x, y)
            if d < width:
                core = 1 - d / width          # 1 at the center of the band
                if rng.random() < 0.18 + 0.55 * core:
                    put(x, y, MILKY_WAY[min(3, int(core * 4))])
                if rng.random() < 0.06 * core:
                    put(x, y, rng.choice(["#c9c2ff", "#ffffff", "#ffd9f2"]))


def draw_nebulae():
    clouds = [  # (center x, center y, radius, colors from edge to core)
        (46, 14, 10, ["#4a2463", "#5c2c75", "#7a3a8c"]),
        (128, 30, 9, ["#1d3f66", "#235078", "#2f6a8c"]),
        (178, 40, 7, ["#47245f", "#5c2c75"]),
    ]
    for cx, cy, radius, colors in clouds:
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius * 2, cx + radius * 2 + 1):
                d = math.hypot((x - cx) / 2.0, y - cy) / radius
                if d < 1 and rng.random() < 0.55 * (1 - d) ** 1.2:
                    put(x, y, colors[min(len(colors) - 1, int((1 - d) * len(colors)))])


def draw_galaxy(gx=30, gy=40):
    for t in range(60):
        angle, radius = t * 0.35, 0.12 * t
        for arm in (0, math.pi):
            color = "#b9a8ff" if t < 25 else "#6d5bc4"
            put(int(gx + radius * math.cos(angle + arm) * 1.8), int(gy + radius * math.sin(angle + arm) * 0.8), color)


# ---------------------------------------------------------------------------
# 3. Stars and the crescent moon
# ---------------------------------------------------------------------------
def draw_stars():
    for _ in range(150):
        x, y = rng.randrange(W), rng.randrange(HORIZON - 4)
        color = rng.choice(STAR_COLORS)
        if rng.random() < 0.35:
            animated(x, y, color, "tw" + str(rng.randrange(3)))   # twinkling
        else:
            put(x, y, color)
    # a few bright four-point sparkles
    for x, y in [(22, 30), (84, 22), (112, 46), (150, 54), (190, 18), (64, 6), (140, 4)]:
        for dx, dy in [(0, -1), (-1, 0), (1, 0), (0, 1)]:
            animated(x + dx, y + dy, "#9fb0ff", "tw1")
        animated(x, y, "#ffffff", "tw1")


def draw_moon():
    mx, my, r = MOON
    for y in range(my - r - 3, my + r + 4):                    # soft halo
        for x in range(mx - r - 3, mx + r + 4):
            if r < math.hypot(x - mx, y - my) < r + 3 and rng.random() < 0.35:
                put(x, y, "#2c2462")
    for y in range(my - r, my + r + 1):                        # crescent
        for x in range(mx - r, mx + r + 1):
            inside = math.hypot(x - mx, y - my) <= r
            bite = math.hypot(x - (mx + 4), y - (my - 2)) <= r - 0.5
            if inside and not bite:
                put(x, y, "#fff3c4" if math.hypot(x - mx + 2, y - my) < r - 2 else "#f2d98a")


# ---------------------------------------------------------------------------
# 4. Ocean: bands, horizon islands, waves, moon reflection
# ---------------------------------------------------------------------------
def draw_ocean():
    for y in range(HORIZON, H):
        i = min((y - HORIZON) * len(SEA) // (H - HORIZON), len(SEA) - 1)
        rect(0, y, W, 1, SEA[i])
    rect(0, HORIZON, W, 1, "#2a2a6a")                          # horizon line

    for x0, w, h in [(118, 14, 3), (128, 6, 5), (184, 16, 2)]:  # islands
        for i in range(w):
            hh = max(1, int(h * math.sin(math.pi * i / w)))
            rect(x0 + i, HORIZON - hh, 1, hh, "#120f33")

    for _ in range(70):                                        # wave highlights
        x, y = rng.randrange(EDGE + 6, W), rng.randrange(HORIZON + 2, H)
        w, color = rng.randrange(2, 6), rng.choice(WAVES)
        if rng.random() < 0.3:
            animated(x, y, color, "wave" + str(rng.randrange(2)), w)
        else:
            rect(x, y, w, 1, color)

    mx = MOON[0]                                               # moon path on water
    for y in range(HORIZON + 1, H, 2):
        spread = 1 + (y - HORIZON) // 6
        for _ in range(2):
            x = mx - spread + rng.randrange(2 * spread + 1)
            animated(x, y, rng.choice(MOON_GLINT), "glint" + str(rng.randrange(3)), rng.randrange(1, 4))


# ---------------------------------------------------------------------------
# 5. The cliff on the left, with grass, flowers, a tree, and surf
# ---------------------------------------------------------------------------
def cliff_edge_x(y):
    """x position of the cliff's right edge at height y (juts out, then slopes into the sea)."""
    t = y - CLIFF_TOP
    return EDGE + (1 if 4 < t < 9 else 0) + (2 if 9 <= t < 14 else 0) + max(0, (t - 12) // 2)


def draw_cliff():
    for y in range(CLIFF_TOP, H):
        edge = cliff_edge_x(y)
        for x in range(edge):
            depth = edge - x
            put(x, y, ROCK[min(3, depth // 6)] if depth < 24 else ROCK[3])
        put(edge - 1, y, "#3a3156")                            # moonlit rim

    for _ in range(60):                                        # rock cracks
        x, y = rng.randrange(4, EDGE + 4), rng.randrange(CLIFF_TOP + 4, H)
        if grid.get((x, y)) in ROCK:
            rect(x, y, rng.randrange(2, 5), 1, rng.choice(["#352d4f", "#14111f"]))

    for y in range(HORIZON, H, 3):                             # surf at the base
        ex = cliff_edge_x(y) + 2
        animated(ex, y, "#c8d6ff", "foam" + str(y % 2), 2)
        animated(ex + 2, y + 1, "#7f93d6", "foam" + str((y + 1) % 2), 2)

    rect(0, CLIFF_TOP - 1, EDGE + 1, 2, GRASS["top"])          # grass
    rect(0, CLIFF_TOP + 1, EDGE, 2, GRASS["mid"])
    rect(0, CLIFF_TOP + 3, EDGE - 1, 1, GRASS["dark"])
    for x in range(EDGE + 1):
        if rng.random() < 0.5:
            put(x, CLIFF_TOP - 2, GRASS["blade"])
        if rng.random() < 0.18:
            put(x, CLIFF_TOP - 3, GRASS["blade"])
    for x, color in [(10, "#e9a6d8"), (19, "#f2d98a"), (31, "#9ad7f0"), (40, "#e9a6d8")]:
        put(x, CLIFF_TOP - 3, GRASS["mid"])
        put(x, CLIFF_TOP - 4, color)

    tx = 12                                                    # lone tree
    rect(tx + 4, CLIFF_TOP - 16, 3, 15, "#3a2618")
    rect(tx + 4, CLIFF_TOP - 16, 1, 15, "#4f3523")
    for dx, dy, w, h, color in [(0, -30, 11, 5, "#1f4d34"), (-3, -26, 17, 6, "#1f4d34"), (-1, -21, 14, 5, "#1f4d34"),
                                (1, -29, 6, 2, "#2f6e48"), (-2, -25, 7, 2, "#2f6e48"), (9, -20, 4, 1, "#163a27")]:
        rect(tx + dx, CLIFF_TOP + dy, w, h, color)


# ---------------------------------------------------------------------------
# 6. The hero, his sword, shield, and lantern
# ---------------------------------------------------------------------------
def draw_hero():
    hx = EDGE - HERO_LEG_COLUMN                 # legs land just past the edge
    hy = CLIFF_TOP - HERO_SEAT_ROW + 1
    sprite(HERO, hx, hy, HERO_PALETTE)

    # sword planted in the grass behind him
    sx = hx - 4
    for y in range(CLIFF_TOP - 13, CLIFF_TOP + 1):
        put(sx, y, "#e3eaff")                                  # blade
    rect(sx + 1, CLIFF_TOP - 12, 1, 10, "#9aa6d6")             # blade shadow
    rect(sx - 2, CLIFF_TOP - 14, 5, 1, "#e0b65a")              # crossguard
    rect(sx, CLIFF_TOP - 17, 1, 3, "#5a3a1c")                  # grip
    put(sx, CLIFF_TOP - 18, "#e0b65a")                         # pommel
    animated(sx, CLIFF_TOP - 11, "#ffffff", "tw2")             # glint on the blade

    # shield leaning against the grass
    sprite(SHIELD, hx - 14, CLIFF_TOP - 7, SHIELD_PALETTE)

    # lantern with a warm glow
    lx = hx - 20
    rect(lx, CLIFF_TOP - 5, 4, 5, "#3a2618")
    rect(lx + 1, CLIFF_TOP - 6, 2, 1, "#2a1a10")
    animated(lx + 1, CLIFF_TOP - 4, "#ffd27a", "lamp", 2, 3)

    # fireflies drifting off the cliff
    for x, y, delay in [(56, 44, "f0"), (84, 40, "f1"), (34, 46, "f2"), (92, 50, "f0"), (26, 38, "f1"), (68, 32, "f2")]:
        animated(x, y, "#fff2a0", "ff " + delay)


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------
# Animations live inside the SVG so the image works on its own (<img src=...>).
SCENE_CSS = """
  @keyframes twinkle { 50% { opacity: .2 } }
  @keyframes lamp { to { fill: #ffb45e } }
  @keyframes firefly { 0% { opacity: .2; transform: translate(0,0) } 50% { opacity: 1; transform: translate(2px,-3px) } 100% { opacity: .2; transform: translate(-1px,-6px) } }
  @keyframes shoot { 0% { opacity: 0; transform: translate(0,0) } 2% { opacity: 1 } 12% { opacity: 1; transform: translate(40px,20px) } 13%, 100% { opacity: 0; transform: translate(40px,20px) } }
  .tw0 { animation: twinkle 2.6s steps(2) infinite }
  .tw1 { animation: twinkle 3.4s steps(2) .6s infinite }
  .tw2 { animation: twinkle 2s steps(2) 1.1s infinite }
  .wave0 { animation: twinkle 3s steps(2) infinite }
  .wave1 { animation: twinkle 3s steps(2) 1.5s infinite }
  .glint0 { animation: twinkle 1.6s steps(2) infinite }
  .glint1 { animation: twinkle 2.1s steps(2) .4s infinite }
  .glint2 { animation: twinkle 1.3s steps(2) .9s infinite }
  .foam0 { animation: twinkle 1.8s steps(2) infinite }
  .foam1 { animation: twinkle 1.8s steps(2) .9s infinite }
  .lamp { animation: lamp 1.4s steps(3) infinite alternate }
  .ff { animation: firefly 3.2s steps(6) infinite }
  .f1 { animation-delay: -1.1s } .f2 { animation-delay: -2.2s }
  .shooter { opacity: 0; animation: shoot 10s steps(12) 2s infinite }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important } .shooter { display: none } }
"""


def scene_svg():
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" shape-rendering="crispEdges">',
        "<!-- Generated by tools/generate_art.py. Edit that script, not this file. -->",
        f"<style>{SCENE_CSS}</style>",
    ]
    # Static pixels: merge horizontal runs of the same color to keep the file small.
    for y in range(H):
        x = 0
        while x < W:
            color = grid.get((x, y))
            if color is None:
                x += 1
                continue
            start = x
            while x < W and grid.get((x, y)) == color:
                x += 1
            out.append(f'<rect x="{start}" y="{y}" width="{x - start}" height="1" fill="{color}"/>')
    for x, y, w, h, color, cls in animated_px:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" class="{cls}"/>')
    out.append('<g class="shooter">'
               '<rect x="60" y="14" width="1" height="1" fill="#fff"/>'
               '<rect x="59" y="13" width="1" height="1" fill="#cfd8ff"/>'
               '<rect x="58" y="12" width="1" height="1" fill="#8a9cff"/>'
               '<rect x="57" y="11" width="1" height="1" fill="#5a6bd6"/></g>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def starfield_svg(size=360, seed=7):
    """A seamless tile of pixel stars and sparkles for the page background."""
    r = random.Random(seed)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}" shape-rendering="crispEdges">',
        "<!-- Generated by tools/generate_art.py. Repeats as the page background. -->",
    ]
    for _ in range(70):                       # tiny dim stars
        x, y = r.randrange(size), r.randrange(size)
        out.append(f'<rect x="{x}" y="{y}" width="1" height="1" fill="{r.choice(STAR_COLORS)}" opacity="{r.choice([0.35, 0.5, 0.7])}"/>')
    for _ in range(26):                       # brighter 2px stars, some twinkle
        x, y = r.randrange(size - 2), r.randrange(size - 2)
        color = r.choice(STAR_COLORS)
        if r.random() < 0.5:
            dur = r.choice([2.4, 3.1, 3.8, 4.6])
            out.append(f'<rect x="{x}" y="{y}" width="2" height="2" fill="{color}">'
                       f'<animate attributeName="opacity" values="1;0.2;1" dur="{dur}s" begin="{r.random() * 3:.1f}s" repeatCount="indefinite"/></rect>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="2" height="2" fill="{color}" opacity="0.85"/>')
    for _ in range(5):                        # four-point sparkles
        x, y = r.randrange(4, size - 4), r.randrange(4, size - 4)
        color = r.choice(["#c8d4ff", "#e2d4ff", "#fff1c9"])
        dur = r.choice([3.2, 4.4, 5.6])
        out.append(f'<g fill="{color}"><animate attributeName="opacity" values="1;0.25;1" dur="{dur}s" repeatCount="indefinite"/>'
                   f'<rect x="{x}" y="{y - 3}" width="1" height="7"/><rect x="{x - 3}" y="{y}" width="7" height="1"/>'
                   f'<rect x="{x - 1}" y="{y - 1}" width="3" height="3" fill="#ffffff"/></g>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    draw_sky()
    draw_milky_way()
    draw_nebulae()
    draw_galaxy()
    draw_stars()
    draw_moon()
    draw_ocean()
    draw_cliff()
    draw_hero()

    os.makedirs(os.path.dirname(OUT_SCENE), exist_ok=True)
    with open(OUT_SCENE, "w") as f:
        f.write(scene_svg())
    with open(OUT_STARS, "w") as f:
        f.write(starfield_svg())
    print(f"wrote {os.path.relpath(OUT_SCENE, ROOT)} ({os.path.getsize(OUT_SCENE) // 1024} KB)")
    print(f"wrote {os.path.relpath(OUT_STARS, ROOT)} ({os.path.getsize(OUT_STARS) // 1024} KB)")


if __name__ == "__main__":
    main()
