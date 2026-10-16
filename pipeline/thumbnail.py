"""Step 5 — thumbnail: the generated art plus big Hindi title text."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

from .common import FONTS, log

BOLD = FONTS / "NotoSansDevanagari-Bold.ttf"


def _font(size: int) -> ImageFont.FreeTypeFont:
    # RAQM does proper Hindi shaping (matras, conjuncts). Without it Hindi renders wrongly.
    if not features.check("raqm"):
        raise RuntimeError("Pillow is missing RAQM text shaping — install libraqm (apt install libraqm0).")
    return ImageFont.truetype(str(BOLD), size, layout_engine=ImageFont.Layout.RAQM)


def _wrap(draw, words: list[str], font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_thumbnail(story: dict, workdir: Path) -> Path:
    art = Image.open(workdir / "thumb_art.png").convert("RGB").resize((1280, 720))
    # soft dark gradient on the left so text pops
    shade = Image.new("L", (1280, 720), 0)
    sd = ImageDraw.Draw(shade)
    for x in range(700):
        sd.line([(x, 0), (x, 720)], fill=int(170 * (1 - x / 700) ** 1.4))
    art = Image.composite(Image.new("RGB", art.size, (10, 10, 30)), art, shade)

    draw = ImageDraw.Draw(art)
    text = story["thumbnail_text"].strip()
    max_w = 640
    for size in range(150, 60, -6):
        font = _font(size)
        lines = _wrap(draw, text.split(), font, max_w)
        if len(lines) <= 3:
            break
    line_h = int(size * 1.25)
    y = (720 - line_h * len(lines)) // 2 - 10
    colours = [(255, 226, 0), (255, 255, 255), (255, 226, 0)]
    for i, line in enumerate(lines):
        # glow
        glow = Image.new("L", art.size, 0)
        ImageDraw.Draw(glow).text((50, y), line, font=font, fill=255, stroke_width=18, stroke_fill=255)
        art.paste((0, 0, 0), mask=glow.filter(ImageFilter.GaussianBlur(10)))
        draw.text((50, y), line, font=font, fill=colours[i % 3], stroke_width=9, stroke_fill=(0, 0, 0))
        y += line_h

    out = workdir / "thumbnail.jpg"
    art.save(out, "JPEG", quality=90, optimize=True)
    log("Thumbnail ready")
    return out
