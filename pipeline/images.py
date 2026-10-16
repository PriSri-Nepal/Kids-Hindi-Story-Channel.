"""Step 2 — illustrations with Google Gemini, kept consistent with a saved character sheet."""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

from .common import DATA, env, http, log

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
SHEET = DATA / "character_sheet.png"


def _call(cfg: dict, prompt: str, refs: list[Path], aspect: str) -> bytes:
    key = env("GEMINI_API_KEY")
    parts = [{"text": prompt}]
    for ref in refs:
        parts.append({"inline_data": {"mime_type": "image/png",
                                      "data": base64.b64encode(ref.read_bytes()).decode()}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"],
                                 "imageConfig": {"aspectRatio": aspect}}}
    models = [cfg["images"]["model"]] + cfg["images"].get("fallback_models", [])
    last = ""
    for model in models:
        for attempt in range(3):
            r = http("POST", API.format(model=model), json=body,
                     headers={"x-goog-api-key": key, "content-type": "application/json"}, timeout=300)
            if r.status_code in (400, 404) and ("not found" in r.text.lower() or "not supported" in r.text.lower()):
                last = f"{model}: {r.text[:200]}"
                break  # try next model
            if r.status_code != 200:
                last = f"{model}: HTTP {r.status_code} {r.text[:300]}"
                continue
            for cand in r.json().get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    blob = part.get("inline_data") or part.get("inlineData")
                    if blob and blob.get("data"):
                        return base64.b64decode(blob["data"])
            last = f"{model}: no image returned (maybe blocked) — {str(r.json())[:300]}"
            body["contents"][0]["parts"][0]["text"] = prompt + "\nKeep it gentle and child-friendly."
    raise RuntimeError(f"Image generation failed: {last}")


def _save(png: bytes, out: Path, size: tuple[int, int]) -> Path:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    # cover-crop to exact size
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - tw) // 2, (img.height - th) // 2
    img.crop((left, top, left + tw, top + th)).save(out, "PNG")
    return out


def _cast_text(cfg: dict, story: dict, text: str) -> str:
    looks = dict(cfg["images"]["cast"])
    looks.update({c["name"]: c["look"] for c in story.get("extra_characters", [])})
    used = [f"{n}: {l}" for n, l in looks.items() if n.lower() in text.lower()]
    return ("Characters (keep exactly these looks): " + "; ".join(used)) if used else ""


def ensure_character_sheet(cfg: dict) -> None:
    """Made once, saved in the repo, then used as the style reference for every future video."""
    if SHEET.exists():
        return
    log("Creating the channel's character sheet (one-time)…")
    cast = "; ".join(f"{n}: {l}" for n, l in cfg["images"]["cast"].items())
    prompt = (f"{cfg['images']['style']}. A character reference sheet on a plain cream background "
              f"showing each of these characters standing side by side, full body, front view: {cast}. "
              "No names, no labels, no text.")
    _save(_call(cfg, prompt, [], "16:9"), SHEET, (1920, 1080))


def make_images(cfg: dict, story: dict, workdir: Path) -> list[Path]:
    ensure_character_sheet(cfg)
    W, H = cfg["video"]["width"], cfg["video"]["height"]
    style = cfg["images"]["style"]
    out = []
    for i, sc in enumerate(story["scenes"], 1):
        path = workdir / f"scene_{i:02d}.png"
        if not path.exists():
            log(f"  image {i}/{len(story['scenes'])}")
            prompt = (f"{style}. Match the art style and character designs of the reference sheet. "
                      f"{_cast_text(cfg, story, sc['image_prompt'])}\nScene: {sc['image_prompt']}")
            _save(_call(cfg, prompt, [SHEET], cfg["images"]["aspect_ratio"]), path, (W, H))
        out.append(path)

    thumb_art = workdir / "thumb_art.png"
    if not thumb_art.exists():
        log("  thumbnail art")
        prompt = (f"{style}, extra vibrant colours, high contrast, YouTube thumbnail. Match the reference sheet's "
                  f"character designs. {_cast_text(cfg, story, story['thumbnail_prompt'])}\n{story['thumbnail_prompt']}. "
                  "Leave the left third fairly plain for a title. No text.")
        _save(_call(cfg, prompt, [SHEET], "16:9"), thumb_art, (1280, 720))
    return out
