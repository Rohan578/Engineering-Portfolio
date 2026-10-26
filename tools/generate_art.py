#!/usr/bin/env python3
"""
generate_art.py — draws all of the site's pixel art.

    python3 tools/generate_art.py

Writes these files into assets/:

    hero-scene.svg      Homepage banner. The armored hero sits on a cliff above
                        the ocean at night, seen from the side.
    project-scene.svg   Project page banner. The hero stands facing us in a night
                        meadow, hands resting on a sword planted in the ground.
    contact-scene.svg   Contact section. The same hero seen from behind, looking
                        out at what he sees: the ocean, the moon, the stars.
    starfield.svg       Small repeating tile of stars for the page background.

How drawing works
-----------------
Each picture is a Canvas: a grid of "pixels" that becomes 1x1 <rect>s in an SVG,
which the browser scales up with crisp edges. Canvas methods:

    put(x, y, color)               one pixel
    rect(x, y, w, h, color)        a filled block
    sprite(rows, x, y, palette)    text art: each character maps to a color in
                                   `palette`; "." (or anything unmapped) is empty
    animate(x, y, color, cls)      a pixel that twinkles or glows; the animation
                                   for each class is defined in SCENE_CSS

Scenes are painted back to front: sky, stars, moon, ocean, land, hero.
To change something, edit it below, run the script, and refresh the page.
Only the Python standard library is needed.
"""

import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")


# ===========================================================================
# Colors
# ===========================================================================
SKY = ["#05040f", "#08061a", "#0b0922", "#0f0c2c", "#141036", "#1a1442", "#21184d", "#2a1d57"]
MILKY_WAY = ["#2a2160", "#33296e", "#3d3280", "#4a3c8f"]
BRIGHT_DUST = ["#c9c2ff", "#ffffff", "#ffd9f2"]
STAR_COLORS = ["#ffffff", "#fff1c9", "#c8d4ff", "#e2d4ff"]
SEA = ["#0d1640", "#0b1338", "#0a1131", "#080e29", "#070b22", "#06091c"]
WAVES = ["#1d2a66", "#24357a", "#2f4590"]
MOON_GLINT = ["#f2d98a", "#fff3c4", "#c9a956"]
ROCK = ["#2b2440", "#241e38", "#1e1930", "#181428"]
GRASS = {"rim": "#3f9a5c", "top": "#2f7d4a", "mid": "#235f3a", "dark": "#1a462c", "deep": "#12331f", "deepest": "#0c2416"}
FLOWERS = ["#e9a6d8", "#f2d98a", "#9ad7f0"]
FIREFLY = "#fff2a0"

# The hero's colors (shared by both views so he always looks the same)
HERO_PALETTE = {
    "H": "#1b1412", "h": "#3a2a22",   # curly black hair + highlights
    "S": "#c68b5e", "s": "#a46e48",   # skin + shadow
    "G": "#0b0b14", "g": "#8fb0ff",   # sunglasses + lens glint
    "A": "#b8c2d6", "a": "#7d88a3",   # steel armor + shadow
    "L": "#eef3ff",                   # armor highlight (moonlight)
    "P": "#9aa6c2",                   # pauldrons (shoulder plates)
    "T": "#e0b65a",                   # gold trim
    "C": "#7b3fc4", "c": "#4e2585",   # violet cape + shadow
    "K": "#5a3a1c", "k": "#3d2612",   # leather belt / boots
    "E": "#e3eaff", "e": "#9aa6d6",   # sword blade + its shadow (front view)
}


# ===========================================================================
# Sprites (text art). Each letter is a color from the palette next to it.
# ===========================================================================

# Side view: sitting on the cliff edge facing the sea (right), head tilted up
# at the moon. Curly hair and sunglasses, plate armor, cape behind him on the
# grass, armored legs hanging over the edge.
HERO_SIDE = [
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
HERO_SIDE_SEAT_ROW = 17     # row that sits level with the grass
HERO_SIDE_LEG_COLUMN = 13   # column where his legs go over the edge

# Back view: what you see standing behind him. Curly hair, the arms of his
# sunglasses at the ears, shoulder plates, and the violet cape spreading onto
# the grass.
HERO_BACK = [
    "........hHh.hH......",
    "......hHHHHhHHh.....",
    ".....hHHhHHHHHHh....",
    ".....HHHHHHHhHHH....",
    "....hHHhHHHHHHHHh...",
    ".....HHHHHHHHhHH....",
    ".....GHHHhHHHHHG....",
    "......hHHHHHHHh.....",
    ".......sHHHHHs......",
    "...PPPPTTCCTTPPPP...",
    "..PLPPPTCCCCTPPPLP..",
    "..PPPPACCCCCCAPPPP..",
    "..aAAACCCCCCCCAAAa..",
    "...aAACCCCcCCCAAa...",
    "...AAACCCCcCCCAAA...",
    "...aAACCCCcCCCCAa...",
    "...KKCCCCCcCCCCKK...",
    "..cCCCCCCCcCCCCCCc..",
    ".cCCCCCCCCcCCCCCCCc.",
    "cCCCCCCCCcCCCCCCCCCc",
]

# Round shield (blue with a gold star) and its colors
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


def mirror(left_halves):
    """Build a symmetric sprite from its left halves (the last column is the center)."""
    return [row + row[:-1][::-1] for row in left_halves]


# Front view: standing guard, facing us. Both gauntlets rest on the pommel of
# a sword planted point-down between his boots; the violet cape hangs behind.
# Only the left half is written out; mirror() copies it to the right.
HERO_FRONT = mirror([
    ".......hHhHh",   # big curly hair
    ".....hHHhHHH",
    "....hHhHHhHH",
    "....HHHHHHHH",
    "....hHHHSSSS",   # forehead
    "....HHHGGGGS",   # sunglasses (nose bridge in the middle)
    "....hHHGGGGS",
    ".....hHSSSSS",   # cheeks
    "......HsSSSS",
    ".......hsSSs",   # chin
    "..........sS",   # neck
    "...cPPPPTTTT",   # pauldrons + gold collar
    "...CPLPPAAAT",   # breastplate with a gold center line
    "...CPPPAALAT",   # (the cape hangs straight down behind him: it only shows
    "...CaAaAAAAT",   #  at his outline and in the gaps between arms, body, and legs)
    "...CcaAaAAAT",   # arms angle in toward the sword
    "...CccaAaAAA",
    "...CcccaAaKT",   # gold pommel between the forearms
    "...CccccLAak",   # gauntlets gripping the leather hilt
    "...CccccaAak",
    "...CccaAAAak",
    "...CcTTTTTTT",   # crossguard
    "...CccAAAAaE",   # armored skirt; blade runs down the middle
    "...CccAAAAaE",
    "...CccaAAccE",   # legs apart, cape visible behind and between them
    "...CccaAAccE",
    "..CCccaLAccE",
    "..CCccaAAccE",   # the cape widens toward the hem
    ".CCCccTTTccE",   # gold knee trim
    ".CCcckKKKccE",   # boots
    "CCcckKKKKcce",   # blade tip in the grass; cape hem on the ground
])


# ===========================================================================
# Canvas
# ===========================================================================
class Canvas:
    """A grid of pixels that can be written out as an SVG."""

    def __init__(self, width, height, seed):
        self.w, self.h = width, height
        self.pixels = {}          # (x, y) -> color
        self.animated = []        # (x, y, w, h, color, css_class)
        self.animated_at = {}     # (x, y) -> indexes into self.animated covering that cell
        self.covered = set()      # animated pixels hidden by something drawn later
        self.rng = random.Random(seed)

    def put(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.pixels[(x, y)] = color
            # anything drawn later sits in front, so it hides an animated
            # pixel underneath (e.g. a twinkling star behind the hero)
            self.covered.update(self.animated_at.get((x, y), ()))

    def get(self, x, y):
        return self.pixels.get((x, y))

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, color)

    def sprite(self, rows, x0, y0, palette):
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch in palette:
                    self.put(x0 + dx, y0 + dy, palette[ch])

    def animate(self, x, y, color, css_class, w=1, h=1):
        index = len(self.animated)
        self.animated.append((x, y, w, h, color, css_class))
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.animated_at.setdefault((xx, yy), []).append(index)

    def to_svg(self, note, css="", extra=""):
        out = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" shape-rendering="crispEdges">',
            f"<!-- {note} Generated by tools/generate_art.py: edit that script, not this file. -->",
        ]
        if css:
            out.append(f"<style>{css}</style>")
        # merge horizontal runs of the same color to keep the file small
        for y in range(self.h):
            x = 0
            while x < self.w:
                color = self.get(x, y)
                if color is None:
                    x += 1
                    continue
                start = x
                while x < self.w and self.get(x, y) == color:
                    x += 1
                out.append(f'<rect x="{start}" y="{y}" width="{x - start}" height="1" fill="{color}"/>')
        for i, (x, y, w, h, color, cls) in enumerate(self.animated):
            if i in self.covered:
                continue
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" class="{cls}"/>')
        if extra:
            out.append(extra)
        out.append("</svg>")
        return "\n".join(out) + "\n"


# Animations embedded in each scene SVG, so the images work on their own.
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


def shooting_star(x, y):
    """A small shooting star that streaks across now and then (class 'shooter')."""
    return (f'<g class="shooter"><rect x="{x}" y="{y}" width="1" height="1" fill="#fff"/>'
            f'<rect x="{x - 1}" y="{y - 1}" width="1" height="1" fill="#cfd8ff"/>'
            f'<rect x="{x - 2}" y="{y - 2}" width="1" height="1" fill="#8a9cff"/>'
            f'<rect x="{x - 3}" y="{y - 3}" width="1" height="1" fill="#5a6bd6"/></g>')


# ===========================================================================
# Painters shared by both scenes
# ===========================================================================
def paint_sky(c, horizon):
    """Banded night-sky gradient down to the horizon, dithered at each seam."""
    band_h = horizon / len(SKY)
    for y in range(horizon):
        i = min(int(y / band_h), len(SKY) - 1)
        progress = y / band_h - i
        nxt = SKY[min(i + 1, len(SKY) - 1)]
        for x in range(c.w):
            if progress > 0.8 and (x + y) % 2 == 0:
                c.put(x, y, nxt)
            elif progress > 0.6 and (x + 2 * y) % 4 == 0:
                c.put(x, y, nxt)
            else:
                c.put(x, y, SKY[i])


def paint_milky_way(c, start, end, bottom):
    """A dusty band of stars running from `start` to `end` (x, y)."""
    (x1, y1), (x2, y2) = start, end
    length = math.hypot(x2 - x1, y2 - y1)
    for y in range(bottom):
        for x in range(c.w):
            width = 6 + 3 * math.sin(x / 13.0) + 2 * math.sin(x / 5.3)
            d = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / length
            if d < width:
                core = 1 - d / width          # 1 at the center of the band
                if c.rng.random() < 0.18 + 0.55 * core:
                    c.put(x, y, MILKY_WAY[min(3, int(core * 4))])
                if c.rng.random() < 0.06 * core:
                    c.put(x, y, c.rng.choice(BRIGHT_DUST))


def paint_cloud(c, cx, cy, radius, colors, density=0.55):
    """A soft, dithered nebula cloud. `colors` go from the edge to the core."""
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius * 2, cx + radius * 2 + 1):
            d = math.hypot((x - cx) / 2.0, y - cy) / radius
            if d < 1 and c.rng.random() < density * (1 - d) ** 1.2:
                c.put(x, y, colors[min(len(colors) - 1, int((1 - d) * len(colors)))])


def paint_galaxy(c, gx, gy):
    """A tiny two-armed spiral galaxy."""
    for t in range(60):
        angle, radius = t * 0.35, 0.12 * t
        for arm in (0, math.pi):
            color = "#b9a8ff" if t < 25 else "#6d5bc4"
            c.put(int(gx + radius * math.cos(angle + arm) * 1.8), int(gy + radius * math.sin(angle + arm) * 0.8), color)


def paint_stars(c, count, bottom, sparkles):
    """Random stars (about a third twinkle) plus bright four-point sparkles."""
    for _ in range(count):
        x, y = c.rng.randrange(c.w), c.rng.randrange(bottom)
        color = c.rng.choice(STAR_COLORS)
        if c.rng.random() < 0.35:
            c.animate(x, y, color, "tw" + str(c.rng.randrange(3)))
        else:
            c.put(x, y, color)
    for x, y in sparkles:
        for dx, dy in [(0, -1), (-1, 0), (1, 0), (0, 1)]:
            c.animate(x + dx, y + dy, "#9fb0ff", "tw1")
        c.animate(x, y, "#ffffff", "tw1")


def paint_moon(c, mx, my, r):
    """A crescent moon with a faint halo."""
    for y in range(my - r - 3, my + r + 4):
        for x in range(mx - r - 3, mx + r + 4):
            if r < math.hypot(x - mx, y - my) < r + 3 and c.rng.random() < 0.35:
                c.put(x, y, "#2c2462")
    for y in range(my - r, my + r + 1):
        for x in range(mx - r, mx + r + 1):
            inside = math.hypot(x - mx, y - my) <= r
            bite = math.hypot(x - (mx + 4), y - (my - 2)) <= r - 0.5
            if inside and not bite:
                c.put(x, y, "#fff3c4" if math.hypot(x - mx + 2, y - my) < r - 2 else "#f2d98a")


def paint_ocean(c, horizon, moon_x, islands, wave_from_x=0, wave_count=70, bottom=None):
    """Ocean bands, small islands on the horizon, waves, and the moon's reflection.
    `bottom` limits the waves and moonlight to the water that is actually visible."""
    bottom = bottom or c.h
    for y in range(horizon, c.h):
        i = min((y - horizon) * len(SEA) // max(1, c.h - horizon), len(SEA) - 1)
        c.rect(0, y, c.w, 1, SEA[i])
    c.rect(0, horizon, c.w, 1, "#2a2a6a")                     # horizon line

    for x0, w, h in islands:
        for i in range(w):
            hh = max(1, int(h * math.sin(math.pi * i / w)))
            c.rect(x0 + i, horizon - hh, 1, hh, "#120f33")

    for _ in range(wave_count):
        x, y = c.rng.randrange(wave_from_x, c.w), c.rng.randrange(horizon + 2, bottom)
        w, color = c.rng.randrange(2, 6), c.rng.choice(WAVES)
        if c.rng.random() < 0.3:
            c.animate(x, y, color, "wave" + str(c.rng.randrange(2)), w)
        else:
            c.rect(x, y, w, 1, color)

    for y in range(horizon + 1, bottom, 2):                    # moonlight on the water
        spread = 1 + (y - horizon) // 6
        for _ in range(2):
            x = moon_x - spread + c.rng.randrange(2 * spread + 1)
            c.animate(x, y, c.rng.choice(MOON_GLINT), "glint" + str(c.rng.randrange(3)), c.rng.randrange(1, 4))


def paint_sword(c, x, ground_y):
    """A sword planted in the ground at (x, ground_y)."""
    for y in range(ground_y - 13, ground_y + 1):
        c.put(x, y, "#e3eaff")                                 # blade
    c.rect(x + 1, ground_y - 12, 1, 10, "#9aa6d6")             # blade shadow
    c.rect(x - 2, ground_y - 14, 5, 1, "#e0b65a")              # crossguard
    c.rect(x, ground_y - 17, 1, 3, "#5a3a1c")                  # grip
    c.put(x, ground_y - 18, "#e0b65a")                         # pommel
    c.animate(x, ground_y - 11, "#ffffff", "tw2")              # glint


def paint_lantern(c, x, ground_y):
    """A small lantern with a flickering glow."""
    c.rect(x, ground_y - 5, 4, 5, "#3a2618")
    c.rect(x + 1, ground_y - 6, 2, 1, "#2a1a10")
    c.animate(x + 1, ground_y - 4, "#ffd27a", "lamp", 2, 3)


def paint_fireflies(c, spots):
    for i, (x, y) in enumerate(spots):
        c.animate(x, y, FIREFLY, "ff f" + str(i % 3))


def paint_tree(c, x, ground_y, leaf="#1f4d34", light="#2f6e48", shadow="#163a27", trunk="#3a2618", trunk_light="#4f3523"):
    c.rect(x + 4, ground_y - 16, 3, 15, trunk)
    c.rect(x + 4, ground_y - 16, 1, 15, trunk_light)
    for dx, dy, w, h, color in [(0, -30, 11, 5, leaf), (-3, -26, 17, 6, leaf), (-1, -21, 14, 5, leaf),
                                (1, -29, 6, 2, light), (-2, -25, 7, 2, light), (9, -20, 4, 1, shadow)]:
        c.rect(x + dx, ground_y + dy, w, h, color)


# ===========================================================================
# Scene 1: homepage banner (side view)
# ===========================================================================
BANNER_W, BANNER_H = 200, 90
BANNER_HORIZON = 64      # y of the ocean surface
BANNER_CLIFF_TOP = 54    # y of the grass on the cliff
BANNER_EDGE = 74         # x where the cliff top ends (the hero sits here)
BANNER_MOON = (160, 14, 7)


def banner_cliff_edge(y):
    """x of the cliff's right edge at height y: juts out, then slopes into the sea."""
    t = y - BANNER_CLIFF_TOP
    return BANNER_EDGE + (1 if 4 < t < 9 else 0) + (2 if 9 <= t < 14 else 0) + max(0, (t - 12) // 2)


def build_banner():
    c = Canvas(BANNER_W, BANNER_H, seed=26)
    top, edge = BANNER_CLIFF_TOP, BANNER_EDGE

    # sky
    paint_sky(c, BANNER_HORIZON)
    paint_milky_way(c, (0, 4), (200, 46), BANNER_HORIZON - 6)
    paint_cloud(c, 46, 14, 10, ["#4a2463", "#5c2c75", "#7a3a8c"])
    paint_cloud(c, 128, 30, 9, ["#1d3f66", "#235078", "#2f6a8c"])
    paint_cloud(c, 178, 40, 7, ["#47245f", "#5c2c75"])
    paint_galaxy(c, 30, 40)
    paint_stars(c, 150, BANNER_HORIZON - 4, [(22, 30), (84, 22), (112, 46), (150, 54), (190, 18), (64, 6), (140, 4)])
    paint_moon(c, *BANNER_MOON)

    # ocean
    paint_ocean(c, BANNER_HORIZON, BANNER_MOON[0], [(118, 14, 3), (128, 6, 5), (184, 16, 2)], wave_from_x=edge + 6)

    # cliff face
    for y in range(top, c.h):
        right = banner_cliff_edge(y)
        for x in range(right):
            depth = right - x
            c.put(x, y, ROCK[min(3, depth // 6)] if depth < 24 else ROCK[3])
        c.put(right - 1, y, "#3a3156")                          # moonlit rim
    for _ in range(60):                                         # cracks
        x, y = c.rng.randrange(4, edge + 4), c.rng.randrange(top + 4, c.h)
        if c.get(x, y) in ROCK:
            c.rect(x, y, c.rng.randrange(2, 5), 1, c.rng.choice(["#352d4f", "#14111f"]))
    for y in range(BANNER_HORIZON, c.h, 3):                     # surf at the base
        x = banner_cliff_edge(y) + 2
        c.animate(x, y, "#c8d6ff", "foam" + str(y % 2), 2)
        c.animate(x + 2, y + 1, "#7f93d6", "foam" + str((y + 1) % 2), 2)

    # grass, flowers, tree
    c.rect(0, top - 1, edge + 1, 2, GRASS["top"])
    c.rect(0, top + 1, edge, 2, GRASS["mid"])
    c.rect(0, top + 3, edge - 1, 1, GRASS["dark"])
    for x in range(edge + 1):
        if c.rng.random() < 0.5:
            c.put(x, top - 2, GRASS["rim"])
        if c.rng.random() < 0.18:
            c.put(x, top - 3, GRASS["rim"])
    for x, color in zip([10, 19, 31, 40], FLOWERS + FLOWERS[:1]):
        c.put(x, top - 3, GRASS["mid"])
        c.put(x, top - 4, color)
    paint_tree(c, 12, top)

    # the hero and his gear
    hx = edge - HERO_SIDE_LEG_COLUMN
    c.sprite(HERO_SIDE, hx, top - HERO_SIDE_SEAT_ROW + 1, HERO_PALETTE)
    paint_sword(c, hx - 4, top)
    c.sprite(SHIELD, hx - 14, top - 7, SHIELD_PALETTE)
    paint_lantern(c, hx - 20, top)
    paint_fireflies(c, [(56, 44), (84, 40), (34, 46), (92, 50), (26, 38), (68, 32)])

    return c.to_svg("Homepage banner (side view).", SCENE_CSS, shooting_star(60, 14))


# ===========================================================================
# Scene 2: contact section (back view: looking out over his shoulders)
# ===========================================================================
CONTACT_W, CONTACT_H = 160, 72   # smaller grid = bigger pixels, so he reads clearly
CONTACT_HORIZON = 44     # the horizon sits at his eye level
CONTACT_LEDGE = 60       # y of the grassy ledge he sits on (foreground)
CONTACT_MOON = (130, 13, 6)
CONTACT_HERO_X = 70      # left edge of the back-view sprite (centered)


def contact_ledge_y(x):
    """Top of the grass in the foreground, column by column (gently uneven)."""
    bump = round(1.2 * math.sin(x / 15.0) + 0.8 * math.sin(x / 6.0))
    return CONTACT_LEDGE + bump


def build_contact_scene():
    c = Canvas(CONTACT_W, CONTACT_H, seed=58)

    # the same night he is looking at in the banner
    paint_sky(c, CONTACT_HORIZON)
    paint_milky_way(c, (0, 6), (160, 28), CONTACT_HORIZON - 4)
    paint_cloud(c, 30, 16, 8, ["#4a2463", "#5c2c75", "#7a3a8c"])
    paint_cloud(c, 96, 10, 7, ["#1d3f66", "#235078", "#2f6a8c"])
    paint_cloud(c, 150, 32, 6, ["#47245f", "#5c2c75"])
    paint_galaxy(c, 14, 34)
    paint_stars(c, 130, CONTACT_HORIZON - 3, [(12, 10), (48, 24), (78, 6), (112, 32), (152, 8), (62, 38), (102, 40)])
    paint_moon(c, *CONTACT_MOON)

    paint_ocean(c, CONTACT_HORIZON, CONTACT_MOON[0], [(22, 13, 2), (33, 5, 3), (140, 12, 2)],
                wave_count=45, bottom=CONTACT_LEDGE - 2)

    # the grassy ledge in the foreground, darker the closer it is to us
    for x in range(c.w):
        ground = contact_ledge_y(x)
        c.put(x, ground - 1, GRASS["rim"])                      # moonlit edge
        for y in range(ground, c.h):
            depth = y - ground
            color = (GRASS["top"] if depth < 2 else GRASS["mid"] if depth < 4 else
                     GRASS["dark"] if depth < 7 else GRASS["deep"] if depth < 10 else GRASS["deepest"])
            c.put(x, y, color)
        if c.rng.random() < 0.45:                               # blades above the edge
            c.put(x, ground - 2, GRASS["rim"])
    for _ in range(70):                                         # grass texture
        x = c.rng.randrange(c.w)
        y = c.rng.randrange(contact_ledge_y(x) + 2, c.h)
        c.put(x, y, c.rng.choice([GRASS["mid"], GRASS["dark"], GRASS["top"]]))
    for x in [16, 28, 46, 112, 122, 136, 150]:                  # flowers
        c.put(x, contact_ledge_y(x) + c.rng.randrange(1, 5), c.rng.choice(FLOWERS))

    # a dark tree framing the left side, close to us
    paint_tree(c, 1, contact_ledge_y(6) + 2, leaf="#123124", light="#1c4733", shadow="#0b2117",
               trunk="#24170f", trunk_light="#33221a")

    # the hero from behind, with his sword, shield, and lantern
    hx = CONTACT_HERO_X
    c.sprite(HERO_BACK, hx, CONTACT_LEDGE - len(HERO_BACK) + 2, HERO_PALETTE)
    paint_sword(c, hx + 23, contact_ledge_y(hx + 23))
    c.sprite(SHIELD, hx - 11, contact_ledge_y(hx - 8) - 6, SHIELD_PALETTE)
    paint_lantern(c, hx - 19, contact_ledge_y(hx - 17))
    paint_fireflies(c, [(54, 48), (102, 46), (42, 40), (116, 52), (64, 36), (92, 34)])

    return c.to_svg("Contact section (back view).", SCENE_CSS, shooting_star(110, 5))


# ===========================================================================
# Scene 3: project page banner (front view, standing guard in a meadow)
# ===========================================================================
PROJECT_W, PROJECT_H = 160, 66   # only a strip of meadow below his feet, so content starts close
PROJECT_HORIZON = 44     # where the sky meets the far mountains
PROJECT_GROUND = 50      # top of the meadow in front of him
PROJECT_FEET = 60        # y of his boots (the CSS places the title 36 rows above the bottom: his head)
PROJECT_MOON = (132, 12, 6)


def build_project_banner():
    c = Canvas(PROJECT_W, PROJECT_H, seed=91)
    cx = c.w // 2

    # sky: the same night, from a new angle
    paint_sky(c, PROJECT_HORIZON)
    paint_milky_way(c, (0, 30), (160, 2), PROJECT_HORIZON - 2)
    paint_cloud(c, 34, 12, 8, ["#4a2463", "#5c2c75", "#7a3a8c"])
    paint_cloud(c, 104, 26, 7, ["#1d3f66", "#235078", "#2f6a8c"])
    paint_galaxy(c, 146, 32)
    paint_stars(c, 120, PROJECT_HORIZON - 2, [(14, 8), (52, 22), (90, 6), (118, 30), (150, 16), (24, 34), (70, 36)])
    paint_moon(c, *PROJECT_MOON)

    # far mountains, then rolling hills
    for x in range(c.w):
        peak = 6 + 4 * math.sin(x / 11.0) + 3 * math.sin(x / 5.3 + 1) + 2 * math.sin(x / 23.0)
        top = int(PROJECT_HORIZON - peak)
        c.rect(x, top, 1, c.h - top, "#21183f")
        c.put(x, top, "#2e2457")                                # moonlit ridge
    for x in range(c.w):
        top = int(PROJECT_GROUND - 4 - 3 * math.sin(x / 14.0 + 0.5) - 2 * math.sin(x / 7.0))
        c.rect(x, top, 1, c.h - top, "#132a2a")
        c.put(x, top, "#1d3f37")
    for x0 in [8, 17, 30, 128, 139, 151]:                       # small pines on the hills
        base = int(PROJECT_GROUND - 4 - 3 * math.sin(x0 / 14.0 + 0.5) - 2 * math.sin(x0 / 7.0))
        for i in range(5):
            c.rect(x0 - i // 2, base - 5 + i, 1 + (i // 2) * 2, 1, "#0f2420")
        c.put(x0, base - 6, "#0f2420")

    # the meadow, darker the closer it is to us; the last rows sink into the
    # page's night color so the banner melts into the page below
    meadow = [(2, GRASS["top"]), (4, GRASS["mid"]), (7, GRASS["dark"]), (10, GRASS["deep"]),
              (12, GRASS["deepest"]), (14, "#0b1a17"), (99, "#0a0f1c")]
    for x in range(c.w):
        ground = PROJECT_GROUND + round(math.sin(x / 9.0))
        c.put(x, ground - 1, GRASS["rim"])
        for y in range(ground, c.h):
            depth = y - ground
            c.put(x, y, next(color for limit, color in meadow if depth < limit))
        if c.rng.random() < 0.45:
            c.put(x, ground - 2, GRASS["rim"])
    for _ in range(80):                                         # grass texture
        x = c.rng.randrange(c.w)
        c.put(x, c.rng.randrange(PROJECT_GROUND + 2, PROJECT_FEET + 4), c.rng.choice([GRASS["mid"], GRASS["dark"], GRASS["top"]]))
    for x in [12, 26, 44, 58, 104, 118, 134, 148]:              # flowers
        c.put(x, PROJECT_GROUND + c.rng.randrange(2, 12), c.rng.choice(FLOWERS))

    # the hero, centered, with a soft shadow at his feet
    c.rect(cx - 9, PROJECT_FEET, 19, 1, GRASS["deep"])
    c.rect(cx - 6, PROJECT_FEET + 1, 13, 1, GRASS["deep"])
    width = len(HERO_FRONT[0])
    c.sprite(HERO_FRONT, cx - width // 2, PROJECT_FEET - len(HERO_FRONT) + 1, HERO_PALETTE)
    c.sprite(SHIELD, cx - 19, PROJECT_FEET - 6, SHIELD_PALETTE)    # shield resting beside him
    paint_lantern(c, cx + 14, PROJECT_FEET)
    paint_fireflies(c, [(cx - 30, 46), (cx + 26, 42), (cx - 46, 52), (cx + 40, 54), (cx - 18, 36), (cx + 20, 32)])

    return c.to_svg("Project page banner (front view).", SCENE_CSS, shooting_star(40, 6))


# ===========================================================================
# Background art: star tile
# ===========================================================================
def build_starfield(size=360, seed=7):
    """A seamless tile of pixel stars and sparkles for the page background."""
    r = random.Random(seed)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}" shape-rendering="crispEdges">',
        "<!-- Page background star tile. Generated by tools/generate_art.py. -->",
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




# ===========================================================================
def write(name, svg):
    path = os.path.join(ASSETS, name)
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote assets/{name} ({os.path.getsize(path) // 1024} KB)")


def main():
    for rows in (HERO_SIDE, HERO_BACK, HERO_FRONT, SHIELD):        # catch typos in the sprites
        assert len({len(r) for r in rows}) == 1, "every sprite row must be the same width"

    os.makedirs(ASSETS, exist_ok=True)
    write("hero-scene.svg", build_banner())
    write("project-scene.svg", build_project_banner())
    write("contact-scene.svg", build_contact_scene())
    write("starfield.svg", build_starfield())


if __name__ == "__main__":
    main()
