"""Step 1 — Claude writes a new Hindi moral story, split into illustrated scenes."""
from __future__ import annotations

import re

from .common import DATA, env, http, log, read_json

API_URL = "https://api.anthropic.com/v1/messages"

STORY_TOOL = {
    "name": "save_story",
    "description": "Save the finished children's story and its YouTube metadata.",
    "input_schema": {
        "type": "object",
        "properties": {
            "series": {"type": "string"},
            "title_hi": {"type": "string", "description": "Short catchy Hindi title (Devanagari)"},
            "title_en": {"type": "string", "description": "English translation of the title"},
            "moral_hi": {"type": "string", "description": "The moral in one simple Hindi sentence"},
            "summary_en": {"type": "string", "description": "One-line English plot summary (used to avoid repeats)"},
            "extra_characters": {
                "type": "array",
                "description": "Characters not in the fixed cast, with a FIXED visual description used for every scene",
                "items": {"type": "object",
                          "properties": {"name": {"type": "string"}, "look": {"type": "string"}},
                          "required": ["name", "look"]},
            },
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "narration": {"type": "string", "description": "Hindi narration for this scene, 35-65 words, Devanagari"},
                        "image_prompt": {"type": "string", "description": "English description of ONE illustration for this scene: who is there (by name), what they do, setting, mood, camera framing"},
                    },
                    "required": ["narration", "image_prompt"],
                },
            },
            "thumbnail_text": {"type": "string", "description": "2-4 punchy Hindi words for the thumbnail"},
            "thumbnail_prompt": {"type": "string", "description": "English prompt for a bright, eye-catching thumbnail illustration (close-up faces, strong emotion, empty space on the left for text, no text in image)"},
            "youtube_title": {"type": "string", "description": "Under 90 characters: Hindi title | short English | Hindi Kahani"},
            "youtube_description": {"type": "string", "description": "Hindi + English description, 120-200 words, include the moral, no links"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "12-18 tags, Hindi and English"},
        },
        "required": ["series", "title_hi", "title_en", "moral_hi", "summary_en", "extra_characters",
                     "scenes", "thumbnail_text", "thumbnail_prompt", "youtube_title",
                     "youtube_description", "tags"],
    },
}


def _prompt(cfg: dict, series: str, history: list[dict], topic: str | None) -> str:
    s, ch = cfg["story"], cfg["channel"]
    cast = "\n".join(f"- {k}: {v}" for k, v in cfg["images"]["cast"].items())
    done = "\n".join(f"- {h['summary_en']} (moral: {h.get('moral_hi','')})" for h in history[-60:]) or "(none yet)"
    topic_line = f"\nThe channel owner asked for this specific idea: {topic}\n" if topic else ""
    return f"""You write stories for "{ch['name']}", a Hindi YouTube channel of moral stories for {s['audience']}.

Write ONE brand-new story in the style: **{series}**.{topic_line}
Moral themes we like: {', '.join(ch['moral_themes'])}.

STORIES ALREADY PUBLISHED — do NOT repeat these plots or morals closely:
{done}

Requirements
- Original telling. Traditional folk characters (Akbar, Birbal, Tenali Raman, Panchatantra animals) are fine, but write fresh plots and fresh wording; do not copy any existing book or video.
- Simple, warm, spoken Hindi (Devanagari) that a 6-year-old understands. Short sentences. Some light humour, a little suspense, a clear ending.
- Total narration {s['words_min']}-{s['words_max']} Hindi words (about {s['minutes_target']} minutes read aloud).
- {s['scenes_min']}-{s['scenes_max']} scenes. Each scene's narration is 35-65 words and matches its picture.
- Scene 1 opens with a greeting like: "{s['intro_hint']}" and names the story.
- The last scene states the moral clearly and closes like: "{s['outro_hint']}"
- Completely child-safe: no violence beyond mild cartoon mischief, nothing scary, no bad words, no mocking of any religion, caste, region, body type or disability.
- Write numbers as Hindi words. No English words inside the narration unless very common.

Image prompts (English)
- One clear moment per scene; vary framing (wide shot, close-up, over-the-shoulder).
- Always refer to characters by NAME. Fixed cast looks (do not redescribe them):
{cast}
- Any other recurring character must be listed in extra_characters with a fixed look (clothes, colours, age, animal species/colour).
- Never ask for text, letters or signs in the image.

Call save_story with the result."""


def generate_story(cfg: dict, topic: str | None = None) -> dict:
    history = read_json(DATA / "stories_done.json", [])
    series_list = cfg["channel"]["series"]
    series = series_list[len(history) % len(series_list)]
    log(f"Writing story — series: {series}")

    body = {
        "model": cfg["claude"]["model"],
        "max_tokens": cfg["claude"]["max_tokens"],
        "tools": [STORY_TOOL],
        "tool_choice": {"type": "tool", "name": "save_story"},
        "messages": [{"role": "user", "content": _prompt(cfg, series, history, topic)}],
    }
    headers = {"x-api-key": env("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01",
               "content-type": "application/json"}

    for attempt in range(3):
        r = http("POST", API_URL, json=body, headers=headers, timeout=600)
        if r.status_code != 200:
            raise RuntimeError(f"Claude API error {r.status_code}: {r.text[:500]}")
        story = next(b["input"] for b in r.json()["content"] if b["type"] == "tool_use")
        problems = check_story(cfg, story)
        if not problems:
            words = count_words(story)
            log(f"Story ready: {story['title_hi']} ({story['title_en']}) — {len(story['scenes'])} scenes, {words} words")
            return story
        log(f"  story needs fixing ({'; '.join(problems)}), asking Claude to revise…")
        body["messages"] = body["messages"][:1] + [
            {"role": "assistant", "content": r.json()["content"]},
            {"role": "user", "content": [{
                "type": "tool_result",
                "tool_use_id": next(b["id"] for b in r.json()["content"] if b["type"] == "tool_use"),
                "content": "Please fix and call save_story again with the full corrected story: " + "; ".join(problems),
                "is_error": True}]},
        ]
    raise RuntimeError("Could not get a story that meets the requirements after 3 tries.")


def count_words(story: dict) -> int:
    return sum(len(sc["narration"].split()) for sc in story["scenes"])


def check_story(cfg: dict, story: dict) -> list[str]:
    s = cfg["story"]
    p = []
    w, n = count_words(story), len(story.get("scenes", []))
    if w < s["words_min"]:
        p.append(f"narration is only {w} words; it must be {s['words_min']}-{s['words_max']} words (add more scenes/detail)")
    if w > s["words_max"] * 1.1:
        p.append(f"narration is {w} words; trim it to at most {s['words_max']} words")
    if n < s["scenes_min"] or n > s["scenes_max"]:
        p.append(f"there are {n} scenes; use {s['scenes_min']}-{s['scenes_max']}")
    for i, sc in enumerate(story.get("scenes", []), 1):
        if not re.search(r"[ऀ-ॿ]", sc.get("narration", "")):
            p.append(f"scene {i} narration is not in Hindi Devanagari")
    return p
