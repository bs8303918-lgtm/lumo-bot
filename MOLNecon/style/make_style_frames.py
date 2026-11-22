"""Render the MOLNecon style board: sample stills + a 5-second motion test.

    python3 MOLNecon/style/make_style_frames.py            # stills + contact sheet
    python3 MOLNecon/style/make_style_frames.py --motion   # also motion_test.mp4

The sample topic (the 2010 bitcoin pizza) is only a placeholder to show the look.
"""
from __future__ import annotations

import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from molnstyle import *  # noqa: E402,F403

OUT = os.path.join(os.path.dirname(__file__), "frames")
os.makedirs(OUT, exist_ok=True)
_bg: dict = {}


def bg(mood):
    if mood not in _bg:
        _bg[mood] = background(mood)
    return _bg[mood].copy()


# ------------------------------------------------------------ scenes (frame-driven)
HOOK_WORDS = [("A", 0), ("man", 6), ("paid", 11), ("10,000", 17), ("bitcoin", 26),
              ("for", 35), ("two", 39), ("pizzas.", 45)]
HOOK_LEN = 66


def current_word(words, f):
    idx = 0
    for i, (_, start) in enumerate(words):
        if f >= start - 2:          # visual lands 2 frames before the word
            idx = i
    return idx


def scene_hook(f: int, day: int = 1) -> Image.Image:
    img = bg("setup")
    # number glides up from below over GLIDE frames, starting on "10,000"
    t = smootherstep((f - 15) / GLIDE)
    if f >= 15:
        y = int(860 + (1 - t) * 220)
        hero = font("display", SIZES["hero"])
        draw_text(img, (W // 2, y), "10,000", hero, INK)
    if f >= 24:
        kw = font("display", SIZES["keyword"])
        d = ImageDraw.Draw(img)
        tw, th = text_size(d, "BITCOIN", kw)
        reveal = smootherstep((f - 24) / 10)
        x0 = W // 2 - tw // 2
        marker(img, (x0, 950, x0 + int((tw + 10) * reveal), 950 + th + 40))
        draw_text(img, (W // 2, 1020), "BITCOIN", kw, INK, shadow=False)
    # pizzas pop in on "two" / "pizzas"
    for i, start in enumerate((37, 43)):
        if f >= start:
            s = back_out((f - start) / POP)
            emoji(img, (W // 2 - 150 + i * 300, 560), "\U0001F355", max(1, int(250 * s)))
    img = zoomed(img, creep_zoom(f, punch=f > 43))
    dx, dy = shake(f - 45)
    if dx or dy:
        img = img.transform(img.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy))
    w = current_word(HOOK_WORDS, f)
    caption(img, [HOOK_WORDS[w][0].upper()], 0)
    day_badge(img, day)
    return img


EXPLAIN_WORDS = [("You", 0), ("see,", 5), ("every", 14), ("choice", 20), ("has", 28),
                 ("a", 32), ("price", 35), ("tag.", 42)]


def scene_explain(f: int, day: int = 1) -> Image.Image:
    img = bg("explain")
    d = ImageDraw.Draw(img)
    draw_text(img, (W // 2, 400), "You see,", font("display", SIZES["headline"]), PAPER)
    # chart: axes + a rising line that draws itself over 40 frames
    x0, y0, x1, y1 = 150, 1200, 930, 640
    d.line([(x0, y1 - 40), (x0, y0), (x1 + 20, y0)], fill=(120, 132, 170), width=6)
    pts = [(x0, y0 - 20), (300, y0 - 40), (420, y0 - 30), (540, y0 - 130), (640, y0 - 110),
           (760, y0 - 330), (840, y0 - 290), (920, y1 + 40)]
    prog = smootherstep(f / 40)
    n = max(2, int(len(pts) * prog + 0.999))
    shown = pts[:n]
    d.line(shown, fill=SKY, width=14, joint="curve")
    ex, ey = shown[-1]
    d.ellipse((ex - 22, ey - 22, ex + 22, ey + 22), fill=ORANGE, outline=PAPER, width=5)
    emoji(img, (300, y0 - 120), "\U0001F355", 110)
    if f >= 30:
        s = back_out((f - 30) / POP)
        lab = font("bold", SIZES["label"])
        tw, th = text_size(d, "OPPORTUNITY COST", lab)
        sc = max(0.01, s)
        tile = Image.new("RGBA", (tw + 60, th + 50), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        td.rounded_rectangle((0, 0, tw + 59, th + 49), 22, fill=ORANGE)
        td.text(((tw + 60) // 2, (th + 50) // 2), "OPPORTUNITY COST", font=lab, fill=INK,
                anchor="mm")
        tile = tile.resize((max(1, int(tile.width * sc)), max(1, int(tile.height * sc))))
        img.paste(tile, (W // 2 - tile.width // 2, 530 - tile.height // 2), tile)
    img = zoomed(img, creep_zoom(f))
    w = current_word(EXPLAIN_WORDS, f)
    caption(img, [EXPLAIN_WORDS[w][0].upper()], 0)
    day_badge(img, day)
    return img


def scene_payoff(f: int = 30, day: int = 1) -> Image.Image:
    img = bg("payoff")
    emoji(img, (W // 2, 520), "\U0001F355", 260)
    draw_text(img, (W // 2, 790), "The most expensive", font("bold", 72), PAPER)
    draw_text(img, (W // 2, 960), "PIZZA", font("display", 240), ORANGE)
    draw_text(img, (W // 2, 1130), "in history.", font("bold", 72), PAPER)
    img = zoomed(img, creep_zoom(f, punch=True))
    caption(img, ["HISTORY."], 0)
    day_badge(img, day)
    return img


def scene_hand(day: int = 1) -> Image.Image:
    """Style B: felt-pen ink on paper, one orange accent fill, simple stick figures."""
    img = Image.new("RGB", (W, H), PAPER)
    img = add_grain(img, 4)
    d = ImageDraw.Draw(img)
    # stick figure
    cx, top = 330, 620
    wobbly_circle(d, cx, top, 70, seed=3, fill=PAPER)
    d.ellipse((cx - 28, top - 12, cx - 14, top + 2), fill=INK)
    d.ellipse((cx + 14, top - 12, cx + 28, top + 2), fill=INK)
    wobbly_line(d, [(cx - 25, top + 28), (cx, top + 40), (cx + 25, top + 28)], 6, seed=4)
    wobbly_line(d, [(cx, top + 70), (cx, top + 330)], seed=5)
    wobbly_line(d, [(cx, top + 130), (cx + 170, top + 190)], seed=6)
    wobbly_line(d, [(cx, top + 130), (cx - 120, top + 230)], seed=7)
    wobbly_line(d, [(cx, top + 330), (cx - 90, top + 520)], seed=8)
    wobbly_line(d, [(cx, top + 330), (cx + 90, top + 520)], seed=9)
    # pizza box with orange accent
    bx, by = cx + 160, top + 120
    d.polygon([(bx, by), (bx + 220, by - 10), (bx + 230, by + 120), (bx + 6, by + 130)],
              fill=ORANGE)
    wobbly_line(d, [(bx, by), (bx + 220, by - 10), (bx + 230, by + 120), (bx + 6, by + 130),
                    (bx, by)], seed=10)
    d.text((bx + 115, by + 60), "PIZZA", font=font("bold", 44), fill=INK, anchor="mm")
    # arrow to a big coin
    wobbly_line(d, [(560, 600), (700, 520), (800, 500)], seed=11)
    wobbly_line(d, [(770, 470), (805, 500), (765, 530)], seed=12)
    wobbly_circle(d, 870, 470, 95, seed=13, fill=HIGHLIGHT)
    d.text((870, 470), "₿", font=font("display", 120), fill=INK, anchor="mm")
    d.text((870, 620), "x 10,000", font=font("bold", 64), fill=INK, anchor="mm")
    # hand-lettered style title with underline
    d.text((W // 2, 1120), "Worth it?", font=font("display", 130), fill=INK, anchor="mm")
    wobbly_line(d, [(300, 1200), (560, 1208), (790, 1194)], 10, ORANGE, seed=14)
    caption(img, ["WORTH", "IT?"], 1)
    day_badge(img, day)
    return img


def spec_layout() -> Image.Image:
    img = scene_hook(60)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle((0, 0, W, SAFE_TOP), fill=RED + (70,))
    d.rectangle((0, SAFE_BOTTOM, W, H), fill=RED + (70,))
    d.rectangle((SAFE_RIGHT, int(H * 0.5), W, SAFE_BOTTOM), fill=RED + (50,))
    d.rectangle((MARGIN, SAFE_TOP, W - MARGIN, CONTENT_BOTTOM), outline=GREEN + (255,), width=4)
    d.rectangle((MARGIN, CONTENT_BOTTOM, W - MARGIN, SAFE_BOTTOM), outline=SKY + (255,), width=4)
    img.paste(ov, (0, 0), ov)
    d = ImageDraw.Draw(img)
    f = font("bold", 34)
    d.text((W // 2, 60), "TOP 15 %  -  keep clear (YouTube UI)", font=f, fill=PAPER,
           anchor="mm", stroke_width=4, stroke_fill=INK)
    d.text((W // 2, H - 180), "BOTTOM 20 %  -  keep clear", font=f, fill=PAPER, anchor="mm",
           stroke_width=4, stroke_fill=INK)
    d.text((W - 75, int(H * 0.62)), "buttons", font=font("bold", 28), fill=PAPER, anchor="mm",
           stroke_width=4, stroke_fill=INK)
    d.text((W // 2, SAFE_TOP + 36), "picture zone", font=font("medium", 30), fill=INK, anchor="mm")
    d.text((W // 2, CAPTION_Y + 90), "caption band  (y = 70 %)", font=font("medium", 30),
           fill=INK, anchor="mm")
    return img


def palette_sheet() -> Image.Image:
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    d.text((MARGIN, 120), "MOLNecon", font=font("display", 120), fill=ORANGE)
    d.text((MARGIN, 270), "house style  v1", font=font("bold", 54), fill=PAPER)
    sw = [("INK", INK), ("PAPER", PAPER), ("ORANGE", ORANGE), ("ORANGE_DEEP", ORANGE_DEEP),
          ("HIGHLIGHT", HIGHLIGHT), ("CREAM", CREAM), ("NIGHT", NIGHT), ("VIOLET", VIOLET),
          ("SKY", SKY), ("GREEN", GREEN), ("RED", RED), ("GREY", GREY)]
    for i, (name, c) in enumerate(sw):
        col, row = i % 3, i // 3
        x, y = MARGIN + col * 320, 420 + row * 250
        d.rounded_rectangle((x, y, x + 290, y + 160), 24, fill=c, outline=(70, 66, 62), width=3)
        d.text((x, y + 175), name, font=font("bold", 32), fill=PAPER)
        d.text((x, y + 212), HEX[name], font=font("mono", 28), fill=GREY)
    y = 1450
    d.text((MARGIN, y), "Inter Display Black", font=font("display", 76), fill=PAPER)
    d.text((MARGIN, y + 100), "INTER EXTRABOLD CAPTION", font=font("bold", 56), fill=ORANGE,
           stroke_width=5, stroke_fill=INK)
    d.text((MARGIN, y + 190), "JetBrains Mono 10,000 $1.2B", font=font("mono", 52), fill=SKY)
    d.text((MARGIN, y + 290), "setup = cream   explain = night   payoff = ink + orange",
           font=font("medium", 34), fill=GREY)
    return img


def contact_sheet(paths, cols=3, scale=0.3) -> Image.Image:
    tiles = [Image.open(p).resize((int(W * scale), int(H * scale)), Image.LANCZOS)
             for p in paths]
    tw, th = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    pad = 24
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, rows * th + (rows + 1) * pad), INK)
    for i, t in enumerate(tiles):
        sheet.paste(t, (pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + pad)))
    return sheet


def motion_test(path):
    """Hook -> 4-frame flash -> crossfade -> 'You see' explanation. ~5 s."""
    frames = []
    for f in range(HOOK_LEN):
        frames.append(scene_hook(f))
    flash = Image.new("RGB", (W, H), PAPER)
    last = frames[-1]
    for k in range(FLASH):
        frames.append(Image.blend(flash, last, k / FLASH * 0.3))
    ex_len = 84
    first_ex = scene_explain(0)
    for k in range(XFADE):
        frames.append(Image.blend(flash, first_ex, smootherstep((k + 1) / XFADE)))
    for f in range(ex_len):
        frames.append(scene_explain(f))
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for fr in frames:
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    p.wait()
    return len(frames)


if __name__ == "__main__":
    stills = {
        "01_A_hook_setup.png": scene_hook(52),
        "02_A_explain_night.png": scene_explain(48),
        "03_A_payoff.png": scene_payoff(),
        "04_B_handdrawn.png": scene_hand(),
        "05_layout_safe_zones.png": spec_layout(),
        "06_palette_type.png": palette_sheet(),
    }
    paths = []
    for name, im in stills.items():
        p = os.path.join(OUT, name)
        im.save(p, optimize=True)
        paths.append(p)
        print("wrote", p)
    contact_sheet(paths).save(os.path.join(OUT, "00_style_board.png"), optimize=True)
    print("wrote style board")
    if "--motion" in sys.argv:
        n = motion_test(os.path.join(OUT, "motion_test.mp4"))
        print("wrote motion_test.mp4,", n, "frames")
