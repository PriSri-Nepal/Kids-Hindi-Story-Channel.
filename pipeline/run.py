"""Make one complete video: story → pictures → voice → video → thumbnail → YouTube.

Usage:
  python -m pipeline.run                 # full run (needs all secrets)
  python -m pipeline.run --no-upload     # make the video but don't upload
  python -m pipeline.run --topic "..."   # suggest a story idea
  python -m pipeline.run --mock          # offline test: fake story, pictures and voice, no API keys
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .common import DATA, ROOT, log, load_config, read_json, run, write_json


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "story"


def _mock_assets(cfg: dict, story: dict, workdir: Path):
    """Offline stand-ins so the video step can be tested without any API."""
    from PIL import Image, ImageDraw

    W, H = cfg["video"]["width"], cfg["video"]["height"]
    images, voices = [], []
    for i, sc in enumerate(story["scenes"], 1):
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        for y in range(H):
            d.line([(0, y), (W, y)], fill=(40 + i * 7 % 200, 90 + y * 100 // H, 160 - i * 5 % 120))
        d.ellipse([W // 2 - 200, H // 2 - 200, W // 2 + 200, H // 2 + 200], fill=(250, 210, 90))
        d.text((60, 60), f"Scene {i}", fill="white")
        p = workdir / f"scene_{i:02d}.png"
        img.save(p)
        images.append(p)
        secs = max(len(sc["narration"]) / 14, 2.0)
        a = workdir / f"voice_{i:02d}.mp3"
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency={300 + i * 20}:duration={secs:.2f}",
             "-af", "volume=0.2", str(a)])
        voices.append(a)
    Image.new("RGB", (1280, 720), (60, 120, 200)).save(workdir / "thumb_art.png")
    return images, voices


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--workdir", default="")
    args = ap.parse_args()

    cfg = load_config()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. story
    if args.mock:
        story = json.loads((ROOT / "tests" / "sample_story.json").read_text(encoding="utf-8"))
    else:
        from .story import generate_story
        story = generate_story(cfg, args.topic.strip() or None)

    workdir = Path(args.workdir) if args.workdir else ROOT / "output" / f"{stamp}-{_slug(story['title_en'])}"
    workdir.mkdir(parents=True, exist_ok=True)
    write_json(workdir / "story.json", story)

    # 2–3. pictures + voice
    if args.mock:
        images, voices = _mock_assets(cfg, story, workdir)
    else:
        from .images import make_images
        from .voice import make_narration
        log("Creating illustrations…")
        images = make_images(cfg, story, workdir)
        voices = make_narration(cfg, story, workdir)

    # 4–5. video + thumbnail
    from .thumbnail import make_thumbnail
    from .video import make_video
    log("Assembling video…")
    video = make_video(cfg, story, images, voices, workdir)
    thumb = make_thumbnail(story, workdir)

    # 6. upload
    result = {}
    if not (args.no_upload or args.mock):
        from .upload import upload
        result = upload(cfg, story, video, thumb)

    # remember this story so it's never repeated
    if not args.mock:
        hist = read_json(DATA / "stories_done.json", [])
        hist.append({"date": stamp, "series": story["series"], "title_hi": story["title_hi"],
                     "title_en": story["title_en"], "summary_en": story["summary_en"],
                     "moral_hi": story["moral_hi"], **{k: result.get(k) for k in ("video_id", "url")}})
        write_json(DATA / "stories_done.json", hist)

    # summary for the notification
    lines = [f"## {story['title_hi']} — {story['title_en']}", "",
             f"**Moral:** {story['moral_hi']}", f"**Series:** {story['series']}", ""]
    if result:
        lines += [f"▶️ Watch: {result['url']}", f"✏️ Edit / publish in YouTube Studio: {result['studio_url']}"]
        if result.get("publish_at"):
            lines.append(f"⏰ Goes public automatically at **{result['publish_at']}** (UTC). "
                         "Watch it first — to stop it, open YouTube Studio → this video → Visibility → Private.")
        else:
            lines.append("🔒 Uploaded as **private** — publish it from the YouTube Studio app when you're happy.")
        if not result.get("thumbnail_set"):
            lines.append("⚠️ Thumbnail not set — verify your channel's phone number at youtube.com/verify, "
                         "then upload thumbnail.jpg from the run's files.")
    else:
        lines.append("Video was made but not uploaded (download it from this run's files).")
    (workdir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "output").mkdir(exist_ok=True)
    (ROOT / "output" / "LATEST").write_text(str(workdir.resolve()))
    log("All done ✔")


if __name__ == "__main__":
    main()
