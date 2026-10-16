"""Step 3 — narration in your cloned voice with ElevenLabs."""
from __future__ import annotations

from pathlib import Path

from .common import env, http, log

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"


def make_narration(cfg: dict, story: dict, workdir: Path) -> list[Path]:
    v = cfg["voice"]
    scenes = story["scenes"]
    total = sum(len(s["narration"]) for s in scenes)
    if total > v["max_chars_per_video"]:
        raise RuntimeError(f"Story is {total} characters, above the safety cap of {v['max_chars_per_video']} "
                           "(config.yaml → voice.max_chars_per_video). Not spending credits.")
    log(f"Narrating {len(scenes)} scenes ({total} characters of ElevenLabs credit)")

    key, voice_id = env("ELEVENLABS_API_KEY"), env("ELEVENLABS_VOICE_ID")
    out = []
    for i, sc in enumerate(scenes):
        path = workdir / f"voice_{i + 1:02d}.mp3"
        if not path.exists():
            body = {
                "text": sc["narration"],
                "model_id": v["model"],
                "language_code": "hi",
                "voice_settings": {"stability": v["stability"], "similarity_boost": v["similarity_boost"],
                                   "style": v["style"], "use_speaker_boost": True, "speed": v["speed"]},
                # neighbouring text keeps the tone continuous between scenes
                "previous_text": scenes[i - 1]["narration"] if i > 0 else None,
                "next_text": scenes[i + 1]["narration"] if i + 1 < len(scenes) else None,
            }
            r = http("POST", API.format(voice=voice_id), json=body,
                     headers={"xi-api-key": key, "content-type": "application/json", "accept": "audio/mpeg"})
            if r.status_code == 400 and "language_code" in r.text:
                body.pop("language_code")
                r = http("POST", API.format(voice=voice_id), json=body,
                         headers={"xi-api-key": key, "content-type": "application/json", "accept": "audio/mpeg"})
            if r.status_code != 200:
                raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:400]}")
            path.write_bytes(r.content)
        out.append(path)
    return out
