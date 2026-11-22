"""MOLNecon house style: tokens + drawing helpers shared by every short.

Everything visual in a MOLNecon short should come from here, so the look stays
identical from Day 1 to Day 365. Numbers are taken from STYLE.md.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- canvas
W, H, FPS = 1080, 1920, 30
SAFE_TOP = int(H * 0.15)      # 288 px: YouTube title / search UI
SAFE_BOTTOM = int(H * 0.80)   # 1536 px: channel name, caption, buttons
SAFE_RIGHT = W - 150          # like/comment/share column (lower half)
MARGIN = 72
CONTENT_BOTTOM = 1250         # pictures live in SAFE_TOP..1250
CAPTION_Y = int(H * 0.70)     # 1344: captions live in the 1250..1536 band

# ---------------------------------------------------------------- colour
# No pure black, no pure white. Dark parts are lifted and tinted.
INK = (28, 26, 25)            # #1C1A19 brand near-black
PAPER = (245, 240, 232)       # #F5F0E8 brand white
ORANGE = (242, 154, 46)       # #F29A2E brand orange: current word, key numbers
ORANGE_DEEP = (201, 115, 26)  # #C9731A orange in shadow
HIGHLIGHT = (255, 214, 130)   # #FFD682 warm key light
CREAM = (252, 236, 210)       # #FCECD2 setup background (warm, bright)
NIGHT = (24, 34, 66)          # #182242 "You see" background
NIGHT_DEEP = (15, 21, 44)     # #0F152C bottom of the night gradient
VIOLET = (78, 66, 128)        # #4E4280 cool shadow
SKY = (88, 150, 220)          # #5896DC chart blue / cool accent
GREEN = (63, 179, 127)        # #3FB37F money / growth
RED = (228, 87, 76)           # #E4574C loss / crash
GREY = (138, 130, 122)        # #8A827A secondary text

HEX = {k: "#%02X%02X%02X" % v for k, v in dict(
    INK=INK, PAPER=PAPER, ORANGE=ORANGE, ORANGE_DEEP=ORANGE_DEEP,
    HIGHLIGHT=HIGHLIGHT, CREAM=CREAM, NIGHT=NIGHT, NIGHT_DEEP=NIGHT_DEEP,
    VIOLET=VIOLET, SKY=SKY, GREEN=GREEN, RED=RED, GREY=GREY).items()}

# The three lighting states. The light follows the story.
MOODS = {
    #           top colour     bottom colour    text   glow       glow strength
    "setup":   (CREAM,         (246, 214, 170), INK,   HIGHLIGHT, 110),
    "explain": (NIGHT,         NIGHT_DEEP,      PAPER, SKY,       70),
    "payoff":  ((44, 30, 40),  (22, 20, 30),    PAPER, ORANGE,    55),
}

# ---------------------------------------------------------------- type
_FONT_DIR = "/usr/share/fonts/opentype/inter/"
FONTS = {
    "display": _FONT_DIR + "InterDisplay-Black.otf",      # headlines, big words
    "bold": _FONT_DIR + "Inter-ExtraBold.otf",            # captions, labels
    "medium": _FONT_DIR + "Inter-SemiBold.otf",           # small text
    "mono": "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf",  # counters
    "emoji": "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
}
SIZES = {"hero": 210, "keyword": 150, "headline": 110, "caption": 92,
         "label": 60, "small": 40, "badge": 34}

_cache: dict = {}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(FONTS[kind], size)
    return _cache[key]


# ---------------------------------------------------------------- motion
CREEP = 0.0025        # zoom per frame on every hold (0.15-0.35 %)
CREEP_PUNCH = 0.006   # zoom per frame on punch words
GLIDE = 24            # frames for a camera/element move (18-40)
SHAKE_FRAMES = 7      # impact shake, flips sign every frame, decays
SHAKE_PX = 18
XFADE = 7             # crossfade only when place/time changes (6-8)
FLASH = 4             # white flash after the hook
POP = 8               # frames for an icon to pop in (overshoot)


def smootherstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def back_out(t: float, s: float = 1.7) -> float:
    """Overshoot ease for pops (icons, numbers)."""
    t = max(0.0, min(1.0, t)) - 1
    return t * t * ((s + 1) * t + s) + 1


def shake(frame_since_impact: int) -> tuple[int, int]:
    f = frame_since_impact
    if f < 0 or f >= SHAKE_FRAMES:
        return 0, 0
    amp = SHAKE_PX * (1 - f / SHAKE_FRAMES)
    sign = 1 if f % 2 == 0 else -1
    return int(sign * amp), int(-sign * amp * 0.5)


def creep_zoom(frames_into_hold: int, punch: bool = False) -> float:
    return 1 + (CREEP_PUNCH if punch else CREEP) * frames_into_hold


# ---------------------------------------------------------------- drawing
def background(mood: str) -> Image.Image:
    """Vertical gradient + soft radial glow + light grain. Never flat."""
    top, bot, _, glow, strength = MOODS[mood]
    t = np.linspace(0, 1, H)[:, None, None]
    grad = np.array(top)[None, None, :] * (1 - t) + np.array(bot)[None, None, :] * t
    img = Image.fromarray(np.repeat(grad, W, axis=1).astype(np.uint8), "RGB")
    g = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(g)
    gd.ellipse((W * 0.5 - 560, H * 0.36 - 560, W * 0.5 + 560, H * 0.36 + 560), fill=strength)
    g = g.filter(ImageFilter.GaussianBlur(240))
    img = Image.composite(Image.new("RGB", (W, H), glow), img, g)
    return add_grain(img, 6)


def add_grain(img: Image.Image, amount: float = 5.0, seed: int = 7) -> Image.Image:
    """Paper grain: +/- `amount` levels of monochrome noise so flats never band."""
    rng = np.random.default_rng(seed)
    n = rng.normal(0, amount, (H // 2, W // 2)).repeat(2, 0).repeat(2, 1)[..., None]
    a = np.asarray(img, dtype=np.float32) + n
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def text_size(d: ImageDraw.ImageDraw, s: str, f) -> tuple[int, int]:
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1]


def draw_text(img: Image.Image, xy, s: str, f, fill, anchor="mm",
              stroke=0, stroke_fill=INK, shadow=True):
    """Text with an optional cast shadow (cool, offset down-right) like a key light."""
    d = ImageDraw.Draw(img)
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.text((xy[0] + 10, xy[1] + 14), s, font=f, fill=VIOLET + (150,), anchor=anchor,
                stroke_width=stroke, stroke_fill=VIOLET + (150,))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        img.paste(sh, (0, 0), sh)
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke,
           stroke_fill=stroke_fill)


def marker(img: Image.Image, box, color=ORANGE, alpha=235):
    """The MOLNecon signature: a slightly tilted marker swipe behind a keyword."""
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    sk = (y1 - y0) * 0.12
    d.polygon([(x0 - 18, y0 + sk), (x1 + 22, y0 - sk), (x1 + 14, y1 - sk * 0.3),
               (x0 - 10, y1 + sk)], fill=color + (alpha,))
    img.paste(layer, (0, 0), layer)


def emoji(img: Image.Image, center, ch: str, size: int, shadow=True):
    """Noto colour emoji, rendered at 109 px and scaled, with a soft violet shadow."""
    f = font("emoji", 109)
    tile = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
    tile = tile.crop(tile.getbbox()).resize((size, size), Image.LANCZOS)
    cx, cy = center
    if shadow:
        a = tile.split()[3].point(lambda v: v * 0.55)
        sh = Image.new("RGBA", tile.size, VIOLET + (0,))
        sh.putalpha(a)
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        img.paste(sh, (cx - size // 2 + 14, cy - size // 2 + 22), sh)
    img.paste(tile, (cx - size // 2, cy - size // 2), tile)


def day_badge(img: Image.Image, day: int):
    """Top-left series badge, present for the whole video."""
    d = ImageDraw.Draw(img)
    f1, f2 = font("bold", SIZES["badge"]), font("medium", 28)
    label = f"DAY {day}"
    tw, _ = text_size(d, label, f1)
    x, y = MARGIN, 150
    d.rounded_rectangle((x, y, x + tw + 44, y + 58), 29, fill=ORANGE)
    d.text((x + 22, y + 29), label, font=f1, fill=INK, anchor="lm")
    d.text((x + tw + 62, y + 29), "Economics in 60s", font=f2, fill=PAPER,
           anchor="lm", stroke_width=3, stroke_fill=INK)


def caption(img: Image.Image, words: list[str], current: int, y: int | None = None):
    """One word (max 3) at a time; the current word is orange. Lower-middle."""
    y = y or CAPTION_Y
    f = font("bold", SIZES["caption"])
    d = ImageDraw.Draw(img)
    gap = 26
    widths = [text_size(d, w, f)[0] for w in words]
    x = (W - (sum(widths) + gap * (len(words) - 1))) // 2
    for i, w in enumerate(words):
        col = ORANGE if i == current else PAPER
        d.text((x, y), w, font=f, fill=col, anchor="lm", stroke_width=7, stroke_fill=INK)
        x += widths[i] + gap


def wobbly_line(d: ImageDraw.ImageDraw, pts, width=7, color=INK, seed=1, passes=2):
    """Hand-drawn stroke for style B: jittered double pass, like a felt pen."""
    rnd = random.Random(seed)
    for p in range(passes):
        out = []
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 18))
            for k in range(n):
                t = k / n
                out.append((x0 + (x1 - x0) * t + rnd.uniform(-2.2, 2.2),
                            y0 + (y1 - y0) * t + rnd.uniform(-2.2, 2.2)))
        out.append(pts[-1])
        d.line(out, fill=color, width=width - p * 2, joint="curve")


def wobbly_circle(d, cx, cy, r, width=7, color=INK, seed=2, fill=None):
    rnd = random.Random(seed)
    pts = []
    for k in range(0, 380, 8):
        a = math.radians(k)
        rr = r + rnd.uniform(-3, 3)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    if fill:
        d.polygon(pts, fill=fill)
    wobbly_line(d, pts, width, color, seed)


def zoomed(img: Image.Image, z: float, cx=W / 2, cy=H / 2) -> Image.Image:
    """Camera creep: crop-and-scale about (cx, cy)."""
    if abs(z - 1) < 1e-4:
        return img
    w, h = W / z, H / z
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return img.resize((W, H), Image.BICUBIC, box=box)


@dataclass
class Word:
    text: str
    start: float  # seconds
    end: float
