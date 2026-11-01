#!/usr/bin/env python3
"""
device_art.py — builds the art for the ESP32-C5 resume badge (device/ folder).

    pip install pillow fonttools brotli
    python3 tools/device_art.py

Uses the SAME hero sprites, palette, and scene painters as the website
(tools/generate_art.py), so the hero on the badge is identical to the one on
the portfolio.

Outputs
-------
  device/resume_badge/scenes_flash.h   all badge screens, compiled INTO the
                                       firmware, so screensavers and resume
                                       pages work with no SD card at all:
      The Shore   side view on the cliff over the ocean
      The Plains  from behind, sitting in a grassy plain
      The Vigil   facing you, hands on his planted sword
      Cover       the "RESUME" start page (portrait homepage banner)
  device/sd/                           only what the phone page needs
                                       (resume PDF, art, fonts, photo)
  device/previews/*.png                exactly what the badge will draw

How the scenes are stored
-------------------------
Each scene is an 80 x 107 grid of art pixels (shown 3x3 on the 240x320 screen):
  palette  up to 255 RGB565 colors
  rle      (count, palette index) byte pairs, row by row
  anim     the pixels that twinkle/glow, like the website's animations,
           12 bytes each: x, y, w, h (art pixels), on, off (RGB565),
           period_ms, offset_ms. The badge shows "on" for the first half
           of each period and "off" for the second.
The cover's title text is stored as 1-bit masks drawn on top in one color each.
"""

import os
import random
import struct
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import generate_art as ga  # noqa: E402  (shared hero sprites + painters)

OUT_SD = os.path.join(ROOT, "device", "sd")
OUT_HEADER = os.path.join(ROOT, "device", "resume_badge", "scenes_flash.h")
OUT_PREVIEW = os.path.join(ROOT, "device", "previews")

SCREEN_W, SCREEN_H = 240, 320
SCALE = 3                                  # 1 art pixel = 3x3 screen pixels
ART_W, ART_H = SCREEN_W // SCALE, -(-SCREEN_H // SCALE)   # 80 x 107

# CSS animation class -> (period ms, delay ms), matching generate_art.SCENE_CSS
ANIM_TIMING = {
    "tw0": (2600, 0), "tw1": (3400, 600), "tw2": (2000, 1100),
    "wave0": (3000, 0), "wave1": (3000, 1500),
    "glint0": (1600, 0), "glint1": (2100, 400), "glint2": (1300, 900),
    "foam0": (1800, 0), "foam1": (1800, 900),
    "lamp": (1400, 0), "ff": (3200, 0),
}
LAMP_GLOW = "#ffb45e"
MAX_ANIM = 320                             # must match MAX_ANIM in the sketch
# Screen rows where the badge prints text (caption at the top, Wi-Fi name at
# the bottom). Animated pixels there would flicker over the text, so they're skipped.
TEXT_ROWS = [(0, 15), (302, 320)]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb565(hex_color):
    r, g, b = rgb(hex_color)
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def art_grid(c, include_animated):
    """The scene as a list of rows of hex colors (art pixels)."""
    grid = [[c.get(x, y) or ga.SKY[min(y * len(ga.SKY) // c.h, 7)] for x in range(c.w)] for y in range(c.h)]
    if include_animated:
        for i, (x, y, w, h, color, _cls) in enumerate(c.animated):
            if i in c.covered:
                continue
            for yy in range(y, min(y + h, c.h)):
                for xx in range(x, min(x + w, c.w)):
                    if xx >= 0 and yy >= 0:
                        grid[yy][xx] = color
    return grid


def darken_for_title(grid, bottom_row):
    """Blocky version of the homepage's dark glow behind the title."""
    out = []
    for y, row in enumerate(grid):
        new = []
        for x, color in enumerate(row):
            dx, dy = (x - ART_W / 2) / (ART_W * 0.8), y / bottom_row
            a = max(0.0, 1 - (dx * dx + dy * dy) ** 0.5) * 0.75
            r, g, b = rgb(color)
            r, g, b = (round(v * (1 - a) + t * a) for v, t in zip((r, g, b), (5, 4, 15)))
            # quantize so the palette stays small
            new.append("#%02x%02x%02x" % (r & 0xF8, g & 0xFC, b & 0xF8))
        out.append(new)
    return out


def grid_image(grid):
    """Render an art grid to the 240x320 screen image, the same way the badge does."""
    img = Image.new("RGB", (ART_W, ART_H))
    img.putdata([rgb(v) for row in grid for v in row])
    return img.resize((ART_W * SCALE, ART_H * SCALE), Image.NEAREST).crop((0, 0, SCREEN_W, SCREEN_H))


def encode_scene(grid):
    """Palette + run-length encoding of an art grid."""
    flat = [v for row in grid for v in row]
    palette = sorted(set(flat))
    assert len(palette) <= 255, f"too many colors ({len(palette)})"
    index = {v: i for i, v in enumerate(palette)}
    rle, i = bytearray(), 0
    while i < len(flat):
        j = i
        while j < len(flat) and flat[j] == flat[i] and j - i < 255:
            j += 1
        rle += bytes((j - i, index[flat[i]]))
        i = j
    return [rgb565(v) for v in palette], bytes(rle)


def anim_records(c, seed):
    """The scene's animated pixels as packed 12-byte records (see the docstring)."""
    r = random.Random(seed)
    records = []
    for i, (x, y, w, h, color, cls) in enumerate(c.animated):
        if i in c.covered or not (0 <= x < c.w and 0 <= y < c.h):
            continue
        w, h = min(w, c.w - x), min(h, c.h - y)
        top, bottom = y * SCALE, (y + h) * SCALE
        if any(top < b and bottom > a for a, b in TEXT_ROWS):
            continue
        name = cls.split()[0]
        period, delay = ANIM_TIMING[name]
        if name == "ff":                     # firefly delay lives in its 2nd class
            delay = {"f0": 0, "f1": 1100, "f2": 2200}.get(cls.split()[1], 0)
        off = LAMP_GLOW if name == "lamp" else (c.get(x, y) or ga.SKY[min(y * len(ga.SKY) // c.h, 7)])
        offset = (delay + r.randrange(period)) % period   # de-sync identical stars
        records.append(struct.pack("<BBBBHHHH", x, y, w, h, rgb565(color), rgb565(off), period, offset))
    assert len(records) <= MAX_ANIM, f"{len(records)} animated pixels > MAX_ANIM"
    return b"".join(records), len(records)


# ---------------------------------------------------------------------------
# Scenes (portrait 80 x 107 art pixels)
# ---------------------------------------------------------------------------
def paint_cliff_over_sea(c, cliff_top, edge, horizon):
    """Rock cliff on the left that slopes into the sea, with grass, flowers, surf."""
    def edge_x(y):
        t = y - cliff_top
        return edge + (1 if 4 < t < 9 else 0) + (2 if 9 <= t < 14 else 0) + max(0, (t - 12) // 2)

    for y in range(cliff_top, c.h):
        right = edge_x(y)
        for x in range(right):
            depth = right - x
            c.put(x, y, ga.ROCK[min(3, depth // 6)] if depth < 24 else ga.ROCK[3])
        c.put(right - 1, y, "#3a3156")                          # moonlit rim
    for _ in range(30):                                         # cracks
        x, y = c.rng.randrange(2, edge + 6), c.rng.randrange(cliff_top + 4, c.h)
        if c.get(x, y) in ga.ROCK:
            c.rect(x, y, c.rng.randrange(2, 4), 1, c.rng.choice(["#352d4f", "#14111f"]))
    for y in range(horizon, c.h, 3):                            # surf
        x = edge_x(y) + 2
        c.animate(x, y, "#c8d6ff", "foam" + str(y % 2), 2)
        c.animate(x + 2, y + 1, "#7f93d6", "foam" + str((y + 1) % 2), 2)

    c.rect(0, cliff_top - 1, edge + 1, 2, ga.GRASS["top"])      # grass
    c.rect(0, cliff_top + 1, edge, 2, ga.GRASS["mid"])
    c.rect(0, cliff_top + 3, edge - 1, 1, ga.GRASS["dark"])
    for x in range(edge + 1):
        if c.rng.random() < 0.5:
            c.put(x, cliff_top - 2, ga.GRASS["rim"])
    for x, color in zip([3, 12, 27], ga.FLOWERS):
        c.put(x, cliff_top - 3, ga.GRASS["mid"])
        c.put(x, cliff_top - 4, color)


def paint_side_hero(c, cliff_top, edge):
    """Side-view hero sitting on the cliff edge with sword, shield, lantern."""
    hx = edge - ga.HERO_SIDE_LEG_COLUMN
    c.sprite(ga.HERO_SIDE, hx, cliff_top - ga.HERO_SIDE_SEAT_ROW + 1, ga.HERO_PALETTE)
    ga.paint_sword(c, hx - 4, cliff_top)
    c.sprite(ga.SHIELD, hx - 14, cliff_top - 7, ga.SHIELD_PALETTE)
    ga.paint_lantern(c, hx - 20, cliff_top)


def build_shore():
    """The Shore: side view on the cliff over the ocean, looking up at the moon."""
    c = ga.Canvas(ART_W, ART_H, seed=101)
    horizon, cliff_top, edge = 70, 62, 35
    ga.paint_sky(c, horizon)
    ga.paint_milky_way(c, (0, 46), (80, 6), horizon - 4)
    ga.paint_cloud(c, 16, 20, 7, ["#4a2463", "#5c2c75", "#7a3a8c"])
    ga.paint_cloud(c, 54, 44, 6, ["#1d3f66", "#235078", "#2f6a8c"])
    ga.paint_galaxy(c, 12, 50)
    ga.paint_stars(c, 75, horizon - 3, [(8, 8), (30, 30), (46, 12), (72, 34), (40, 54)])
    ga.paint_moon(c, 63, 17, 6)
    ga.paint_ocean(c, horizon, 63, [(50, 10, 2), (68, 9, 1)], wave_from_x=edge + 6, wave_count=40)
    paint_cliff_over_sea(c, cliff_top, edge, horizon)
    paint_side_hero(c, cliff_top, edge)
    ga.paint_fireflies(c, [(44, 56), (52, 48), (26, 50), (58, 60)])
    return c


def build_plains():
    """The Plains: the hero from behind, sitting in a grassy plain under the stars."""
    c = ga.Canvas(ART_W, ART_H, seed=202)
    horizon, ground = 74, 86
    ga.paint_sky(c, horizon)
    ga.paint_milky_way(c, (0, 14), (80, 40), horizon - 4)
    ga.paint_cloud(c, 58, 18, 7, ["#4a2463", "#5c2c75", "#7a3a8c"])
    ga.paint_cloud(c, 18, 48, 6, ["#1d3f66", "#235078", "#2f6a8c"])
    ga.paint_galaxy(c, 66, 50)
    ga.paint_stars(c, 85, horizon - 3, [(10, 30), (36, 8), (50, 34), (74, 10), (28, 56), (66, 62)])
    ga.paint_moon(c, 22, 16, 6)

    for x in range(c.w):                                        # far hills
        top = int(horizon - 5 - 3 * ga.math.sin(x / 9.0) - 2 * ga.math.sin(x / 4.3 + 1))
        c.rect(x, top, 1, c.h - top, "#21183f")
        c.put(x, top, "#2e2457")
    for x in range(c.w):                                        # near hills
        top = int(ground - 6 - 2 * ga.math.sin(x / 11.0 + 0.5) - 1.5 * ga.math.sin(x / 5.0))
        c.rect(x, top, 1, c.h - top, "#132a2a")
        c.put(x, top, "#1d3f37")
    for x0 in [6, 14, 64, 73]:                                  # pines
        base = int(ground - 6 - 2 * ga.math.sin(x0 / 11.0 + 0.5) - 1.5 * ga.math.sin(x0 / 5.0))
        for i in range(5):
            c.rect(x0 - i // 2, base - 5 + i, 1 + (i // 2) * 2, 1, "#0f2420")
        c.put(x0, base - 6, "#0f2420")

    def ledge_y(x):
        return ground + round(1.2 * ga.math.sin(x / 9.0) + 0.6 * ga.math.sin(x / 4.0))

    for x in range(c.w):                                        # grass, darker up close
        g = ledge_y(x)
        c.put(x, g - 1, ga.GRASS["rim"])
        for y in range(g, c.h):
            d = y - g
            c.put(x, y, ga.GRASS["top"] if d < 2 else ga.GRASS["mid"] if d < 5 else
                  ga.GRASS["dark"] if d < 9 else ga.GRASS["deep"] if d < 13 else ga.GRASS["deepest"])
        if c.rng.random() < 0.45:
            c.put(x, g - 2, ga.GRASS["rim"])
    for _ in range(45):
        x = c.rng.randrange(c.w)
        c.put(x, c.rng.randrange(ledge_y(x) + 2, c.h), c.rng.choice([ga.GRASS["mid"], ga.GRASS["dark"]]))
    for x in [6, 15, 58, 66, 75]:
        c.put(x, ledge_y(x) + c.rng.randrange(1, 5), c.rng.choice(ga.FLOWERS))

    hx = 30                                                     # hero from behind
    c.sprite(ga.HERO_BACK, hx, ground - len(ga.HERO_BACK) + 2, ga.HERO_PALETTE)
    ga.paint_sword(c, hx + 23, ledge_y(hx + 23))
    c.sprite(ga.SHIELD, hx - 11, ledge_y(hx - 8) - 6, ga.SHIELD_PALETTE)
    ga.paint_lantern(c, hx - 19, ledge_y(hx - 17))
    ga.paint_fireflies(c, [(22, 74), (58, 72), (12, 66), (68, 80), (40, 60)])
    return c


def build_vigil():
    """The Vigil: the hero facing us, hands on a sword planted in the meadow."""
    c = ga.Canvas(ART_W, ART_H, seed=303)
    horizon, ground, feet = 70, 78, 98
    ga.paint_sky(c, horizon)
    ga.paint_milky_way(c, (0, 40), (80, 4), horizon - 2)
    ga.paint_cloud(c, 20, 14, 7, ["#4a2463", "#5c2c75", "#7a3a8c"])
    ga.paint_cloud(c, 60, 40, 6, ["#1d3f66", "#235078", "#2f6a8c"])
    ga.paint_stars(c, 75, horizon - 2, [(8, 34), (34, 10), (52, 26), (74, 44), (14, 56)])
    ga.paint_moon(c, 64, 15, 6)
    for x in range(c.w):                                        # mountains
        peak = 6 + 4 * ga.math.sin(x / 8.0) + 2 * ga.math.sin(x / 3.7 + 1)
        top = int(horizon - peak)
        c.rect(x, top, 1, c.h - top, "#21183f")
        c.put(x, top, "#2e2457")
    for x in range(c.w):                                        # hills
        top = int(ground - 4 - 2 * ga.math.sin(x / 9.0 + 0.5) - 1.5 * ga.math.sin(x / 4.6))
        c.rect(x, top, 1, c.h - top, "#132a2a")
        c.put(x, top, "#1d3f37")
    meadow = [(2, ga.GRASS["top"]), (5, ga.GRASS["mid"]), (10, ga.GRASS["dark"]), (16, ga.GRASS["deep"]),
              (22, ga.GRASS["deepest"]), (99, "#0b1a17")]
    for x in range(c.w):
        g = ground + round(ga.math.sin(x / 7.0))
        c.put(x, g - 1, ga.GRASS["rim"])
        for y in range(g, c.h):
            c.put(x, y, next(col for limit, col in meadow if y - g < limit))
        if c.rng.random() < 0.45:
            c.put(x, g - 2, ga.GRASS["rim"])
    for _ in range(50):
        x = c.rng.randrange(c.w)
        c.put(x, c.rng.randrange(ground + 2, c.h), c.rng.choice([ga.GRASS["mid"], ga.GRASS["dark"]]))
    for x in [6, 14, 64, 72, 30, 50]:
        c.put(x, ground + c.rng.randrange(3, 18), c.rng.choice(ga.FLOWERS))

    cx = c.w // 2
    c.rect(cx - 9, feet, 19, 1, ga.GRASS["deep"])               # shadow at his feet
    c.rect(cx - 6, feet + 1, 13, 1, ga.GRASS["deep"])
    width = len(ga.HERO_FRONT[0])
    c.sprite(ga.HERO_FRONT, cx - width // 2, feet - len(ga.HERO_FRONT) + 1, ga.HERO_PALETTE)
    c.sprite(ga.SHIELD, cx - 20, feet - 6, ga.SHIELD_PALETTE)
    ga.paint_lantern(c, cx + 15, feet)
    ga.paint_fireflies(c, [(12, 76), (66, 74), (20, 88), (60, 92), (8, 62)])
    return c


def build_cover_art():
    """Portrait version of the homepage banner: sky on top for the title."""
    c = ga.Canvas(ART_W, ART_H, seed=404)
    horizon, cliff_top, edge = 80, 72, 35
    ga.paint_sky(c, horizon)
    ga.paint_milky_way(c, (0, 62), (80, 24), horizon - 4)
    ga.paint_cloud(c, 14, 56, 6, ["#4a2463", "#5c2c75", "#7a3a8c"])
    ga.paint_cloud(c, 60, 50, 5, ["#1d3f66", "#235078", "#2f6a8c"])
    ga.paint_stars(c, 70, horizon - 3, [(6, 46), (26, 64), (48, 70), (74, 44)])
    ga.paint_moon(c, 66, 60, 5)
    ga.paint_ocean(c, horizon, 66, [(50, 10, 2)], wave_from_x=edge + 6, wave_count=30)
    paint_cliff_over_sea(c, cliff_top, edge, horizon)
    paint_side_hero(c, cliff_top, edge)
    return c


# ---------------------------------------------------------------------------
# Cover text (same fonts and colors as the homepage banner)
# ---------------------------------------------------------------------------
def load_fonts():
    """Convert the website's woff2 fonts to TTF (PIL can't read woff2)."""
    from fontTools.ttLib import TTFont
    tmp = tempfile.mkdtemp()
    paths = {}
    for name in ("pixelify-500", "pixelify-700"):
        f = TTFont(os.path.join(ROOT, "fonts", name + ".woff2"))
        f.flavor = None
        paths[name] = os.path.join(tmp, name + ".ttf")
        f.save(paths[name])
    return paths


def fit_font(path, text, max_w, start):
    size = start
    while size > 6:
        font = ImageFont.truetype(path, size)
        if font.getlength(text) <= max_w:
            return font
        size -= 1
    return ImageFont.truetype(path, 6)


def text_mask(draw_fn):
    """Draw something on a blank 240x320 1-bit canvas; return (x, y, w, h, packed bits)."""
    m = Image.new("L", (SCREEN_W, SCREEN_H), 0)
    d = ImageDraw.Draw(m)
    d.fontmode = "1"                                   # crisp pixels, no anti-aliasing
    draw_fn(d)
    m = m.point(lambda v: 255 if v >= 128 else 0)
    box = m.getbbox()
    if not box:
        return None
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    bits = bytearray()
    px = m.load()
    for y in range(y0, y1):
        for bx in range(0, w, 8):
            byte = 0
            for k in range(8):
                if bx + k < w and px[x0 + bx + k, y]:
                    byte |= 0x80 >> k
            bits.append(byte)
    return x0, y0, w, h, bytes(bits)


def cover_layers(fonts):
    """The cover's title as (mask, color) layers, drawn in order (shadows first)."""
    gold, head, sky = "#f2d98a", "#fff3c4", "#8fbbe8"
    shadow, dark = "#2a1d57", "#05040f"

    rib_font = ImageFont.truetype(fonts["pixelify-700"], 15)
    label = "R E S U M E"
    rw = rib_font.getlength(label) + 52
    ribbon = (int((SCREEN_W - rw) / 2), 14, int((SCREEN_W + rw) / 2), 40)

    name_font = fit_font(fonts["pixelify-700"], "Shrivastava", 214, 40)
    tagline = "Hardware · Embedded · Robotics"
    tag_font = fit_font(fonts["pixelify-500"], tagline, 220, 15)
    hint_font = ImageFont.truetype(fonts["pixelify-500"], 13)

    def text(d, y, t, font, dy=0):
        d.text(((SCREEN_W - font.getlength(t)) / 2, y + dy), t, font=font, fill=255)

    def sparkles(d):
        cy = (ribbon[1] + ribbon[3]) / 2
        for sx in (ribbon[0] + 14, ribbon[2] - 14):
            d.polygon([(sx, cy - 6), (sx + 2, cy - 2), (sx + 6, cy), (sx + 2, cy + 2),
                       (sx, cy + 6), (sx - 2, cy + 2), (sx - 6, cy), (sx - 2, cy - 2)], fill=255)

    y_name2 = 50 + name_font.size
    y_tag = 58 + 2 * name_font.size
    layers = [
        (lambda d: (text(d, 50, "Rohan", name_font, 3), text(d, y_name2, "Shrivastava", name_font, 3)), shadow),
        (lambda d: (text(d, 50, "Rohan", name_font), text(d, y_name2, "Shrivastava", name_font)), head),
        (lambda d: text(d, y_tag, tagline, tag_font, 2), dark),
        (lambda d: text(d, y_tag, tagline, tag_font), "#e6e2f8"),
        (lambda d: text(d, ribbon[1] + 4, label, rib_font), gold),
        (sparkles, head),
        (lambda d: text(d, 276, "Tap BOOT to explore  >", hint_font, 2), dark),
        (lambda d: text(d, 276, "Tap BOOT to explore  >", hint_font), sky),
    ]
    return ribbon, [(text_mask(fn), color) for fn, color in layers]


def paint_layers(img, ribbon, layers):
    """Draw the ribbon and text layers onto a preview image, like the badge does."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = ribbon
    d.rectangle(ribbon, fill=(10, 8, 30))
    d.rectangle(ribbon, outline=(160, 144, 104), width=2)
    for mask, color in layers:
        if not mask:
            continue
        mx, my, w, h, bits = mask
        stride = (w + 7) // 8
        for y in range(h):
            for x in range(w):
                if bits[y * stride + x // 8] & (0x80 >> (x % 8)):
                    img.putpixel((mx + x, my + y), rgb(color))
    return img


def c_array(ctype, name, values, per_line=24):
    """Format a C array; values are ints."""
    fmt = "0x%04X" if "16" in ctype else "%d"
    body = ",\n  ".join(",".join(fmt % v for v in values[i:i + per_line]) for i in range(0, len(values), per_line))
    return f"static const {ctype} {name}[] = {{\n  {body}\n}};\n"


# ---------------------------------------------------------------------------
def copy_web_assets():
    """Files the phone page loads from the SD card."""
    import shutil
    web = os.path.join(OUT_SD, "web")
    os.makedirs(web, exist_ok=True)
    shutil.copy(os.path.join(ROOT, "assets", "hero-scene.svg"), os.path.join(web, "hero.svg"))
    shutil.copy(os.path.join(ROOT, "assets", "starfield.svg"), os.path.join(web, "stars.svg"))
    for name in ("pixelify-500", "pixelify-700", "inter-400"):
        shutil.copy(os.path.join(ROOT, "fonts", name + ".woff2"), os.path.join(web, name + ".woff2"))
    photo = Image.open(os.path.join(ROOT, "media", "profile.jpeg")).convert("RGB")
    side = min(photo.size)
    photo = photo.crop(((photo.width - side) // 2, (photo.height - side) // 2,
                        (photo.width + side) // 2, (photo.height + side) // 2)).resize((240, 240), Image.LANCZOS)
    photo.save(os.path.join(web, "profile.jpg"), quality=82)
    shutil.copy(os.path.join(ROOT, "files", "Rohan_Shrivastava_Resume.pdf"),
                os.path.join(OUT_SD, "Rohan_Shrivastava_Resume.pdf"))


def main():
    os.makedirs(OUT_PREVIEW, exist_ok=True)
    out = ["// AUTO-GENERATED by tools/device_art.py - edit that script, not this file.",
           "// Badge screens stored in flash (see the docstring there for the format).",
           "#pragma once", "#include <stdint.h>", "",
           f"#define ART_W {ART_W}", f"#define ART_H {ART_H}", f"#define ART_SCALE {SCALE}", "",
           "struct FlashScene { const uint16_t* palette; const uint8_t* rle; uint32_t rleLen;",
           "                    const uint8_t* anim; uint16_t animCount; };",
           "struct TextMask   { int16_t x, y, w, h; uint16_t color; const uint8_t* bits; };", ""]
    total = 0

    for name, builder in (("shore", build_shore), ("plains", build_plains), ("vigil", build_vigil)):
        c = builder()
        palette, rle = encode_scene(art_grid(c, include_animated=False))
        anim, n = anim_records(c, seed=len(name))
        out.append(c_array("uint16_t", f"{name}_palette", palette))
        out.append(c_array("uint8_t", f"{name}_rle", list(rle)))
        out.append(c_array("uint8_t", f"{name}_anim", list(anim)) if n else "")
        anim_ref = f"{name}_anim" if n else "nullptr"
        out.append(f"static const FlashScene SCENE_{name.upper()} = "
                   f"{{ {name}_palette, {name}_rle, sizeof({name}_rle), {anim_ref}, {n} }};\n")
        grid_image(art_grid(c, include_animated=True)).save(os.path.join(OUT_PREVIEW, name + ".png"))
        total += len(palette) * 2 + len(rle) + len(anim)
        print(f"{name}: {len(palette)} colors, {len(rle)} bytes of pixels, {n} animated pixels")

    # cover: homepage banner in portrait, darkened behind the title, plus text masks
    grid = darken_for_title(art_grid(build_cover_art(), include_animated=True), bottom_row=52)
    palette, rle = encode_scene(grid)
    out.append(c_array("uint16_t", "cover_palette", palette))
    out.append(c_array("uint8_t", "cover_rle", list(rle)))
    out.append("static const FlashScene SCENE_COVER = { cover_palette, cover_rle, sizeof(cover_rle), nullptr, 0 };\n")
    ribbon, layers = cover_layers(load_fonts())
    out.append(f"static const int16_t COVER_RIBBON[4] = {{ {', '.join(map(str, ribbon))} }};  // x0, y0, x1, y1\n")
    entries = []
    for i, (mask, color) in enumerate(layers):
        if not mask:
            continue
        x, y, w, h, bits = mask
        out.append(c_array("uint8_t", f"cover_text{i}", list(bits)))
        entries.append(f"  {{ {x}, {y}, {w}, {h}, 0x{rgb565(color):04X}, cover_text{i} }},")
        total += len(bits)
    out.append("static const TextMask COVER_TEXT[] = {\n" + "\n".join(entries) + "\n};")
    out.append("static const int COVER_TEXT_COUNT = sizeof(COVER_TEXT) / sizeof(COVER_TEXT[0]);\n")
    paint_layers(grid_image(grid), ribbon, layers).save(os.path.join(OUT_PREVIEW, "cover.png"))
    total += len(palette) * 2 + len(rle)

    with open(OUT_HEADER, "w") as f:
        f.write("\n".join(out))
    print(f"wrote {os.path.relpath(OUT_HEADER, ROOT)} (~{total // 1024} KB of flash)")

    copy_web_assets()
    print("phone-page files + resume copied to device/sd/")


if __name__ == "__main__":
    main()
