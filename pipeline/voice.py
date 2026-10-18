"""Step 3 — narration.

Two options (config.yaml → providers.voice):
  "gemini"     free Google Hindi AI voice
  "elevenlabs" your own cloned voice (paid)
Both produce one audio file per scene.
"""
from __future__ import annotations

import base64
import re
import struct
import subprocess
from pathlib import Path

from .common import duration, env, http, log, run

# ───────────────────────── ElevenLabs (your cloned voice) ─────────────────────────
EL_API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"


def _elevenlabs(cfg: dict, story: dict, workdir: Path) -> list[Path]:
    v = cfg["voice"]
    scenes = story["scenes"]
    total = sum(len(s["narration"]) for s in scenes)
    if total > v["max_chars_per_video"]:
        raise RuntimeError(f"Story is {total} characters, above the safety cap of {v['max_chars_per_video']} "
                           "(config.yaml → voice.max_chars_per_video). Not spending credits.")
    log(f"Narrating {len(scenes)} scenes with ElevenLabs ({total} characters of credit)")
    key, voice_id = env("ELEVENLABS_API_KEY"), env("ELEVENLABS_VOICE_ID")
    headers = {"xi-api-key": key, "content-type": "application/json", "accept": "audio/mpeg"}
    out = []
    for i, sc in enumerate(scenes):
        path = workdir / f"voice_{i + 1:02d}.mp3"
        if not path.exists():
            body = {
                "text": sc["narration"], "model_id": v["model"], "language_code": "hi",
                "voice_settings": {"stability": v["stability"], "similarity_boost": v["similarity_boost"],
                                   "style": v["style"], "use_speaker_boost": True, "speed": v["speed"]},
                "previous_text": scenes[i - 1]["narration"] if i > 0 else None,
                "next_text": scenes[i + 1]["narration"] if i + 1 < len(scenes) else None,
            }
            r = http("POST", EL_API.format(voice=voice_id), json=body, headers=headers)
            if r.status_code == 400 and "language_code" in r.text:
                body.pop("language_code")
                r = http("POST", EL_API.format(voice=voice_id), json=body, headers=headers)
            if r.status_code != 200:
                raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:400]}")
            path.write_bytes(r.content)
        out.append(path)
    return out


# ───────────────────────── Gemini TTS (free) ─────────────────────────
GEM_API = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _wav_from(data: bytes, rate: int = 24000) -> bytes:
    if data[:4] == b"RIFF":
        return data
    # raw 16-bit mono PCM → add a WAV header
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack(
        "<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) + b"data" + struct.pack("<I", len(data))
    return hdr + data


def _find_audio(obj) -> str | None:
    """Find the base64 audio in the response (steps[].content[] with type 'audio')."""
    if isinstance(obj, dict):
        if obj.get("type") == "audio" and isinstance(obj.get("data"), str):
            return obj["data"]
        inline = obj.get("inlineData") or obj.get("inline_data")
        if isinstance(inline, dict) and str(inline.get("mimeType", inline.get("mime_type", ""))).startswith("audio"):
            return inline.get("data")
        found = None
        for v in obj.values():
            found = _find_audio(v) or found
        return found
    if isinstance(obj, list):
        found = None
        for v in obj:
            found = _find_audio(v) or found  # keep the last audio part
        return found
    return None


def _gemini_tts(cfg: dict, text: str) -> bytes:
    g = cfg["gemini_voice"]
    key = env("GEMINI_API_KEY")
    last = ""
    for model in g["models"]:
        body = {
            "model": model,
            "input": [{"type": "user_input", "content": [{
                "type": "text", "text": text,
                "annotations": [{"type": "speech_metadata", "style": g["style"]}]}]}],
            "response_format": {"type": "audio"},
            "generation_config": {"speech_config": [{"voice": g["voice"]}]},
        }
        r = http("POST", GEM_API, json=body, headers={"x-goog-api-key": key, "content-type": "application/json"},
                 timeout=300, retries=8)
        if r.status_code == 200:
            b64 = _find_audio(r.json())
            if b64:
                return _wav_from(base64.b64decode(b64))
            last = f"{model}: no audio in answer {r.text[:200]}"
        else:
            last = f"{model}: HTTP {r.status_code} {r.text[:300]}"
    raise RuntimeError(f"Gemini voice failed: {last}")


def _chunks(scenes: list[dict], limit: int) -> list[list[int]]:
    groups, cur, size = [], [], 0
    for i, sc in enumerate(scenes):
        n = len(sc["narration"])
        if cur and size + n > limit:
            groups.append(cur)
            cur, size = [], 0
        cur.append(i)
        size += n
    if cur:
        groups.append(cur)
    return groups


def _silences(path: Path) -> list[float]:
    """Midpoints of pauses in the audio."""
    res = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "silencedetect=noise=-35dB:d=0.25",
                          "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", res.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", res.stderr)]
    return [(s + e) / 2 for s, e in zip(starts, ends)]


def split_points(total: float, lengths: list[int], pauses: list[float], window: float = 2.5) -> list[float]:
    """Where each scene ends: proportional to text length, snapped to the nearest real pause."""
    cuts, acc, prev = [], 0, 0.0
    whole = sum(lengths) or 1
    for n in lengths[:-1]:
        acc += n
        guess = total * acc / whole
        near = [p for p in pauses if abs(p - guess) <= window and p > prev + 0.5]
        cut = min(near, key=lambda p: abs(p - guess)) if near else max(guess, prev + 0.5)
        cuts.append(cut)
        prev = cut
    return cuts + [total]


def _gemini(cfg: dict, story: dict, workdir: Path) -> list[Path]:
    scenes = story["scenes"]
    groups = _chunks(scenes, cfg["gemini_voice"]["max_chars_per_request"])
    log(f"Narrating {len(scenes)} scenes with the free Gemini voice ({len(groups)} requests)")
    out: list[Path | None] = [None] * len(scenes)
    for gi, idx in enumerate(groups, 1):
        if all((workdir / f"voice_{i + 1:02d}.wav").exists() for i in idx):
            out = [workdir / f"voice_{i + 1:02d}.wav" if i in idx else o for i, o in enumerate(out)]
            continue
        log(f"  voice part {gi}/{len(groups)}")
        text = "\n\n".join(scenes[i]["narration"] for i in idx)
        part = workdir / f"voicepart_{gi:02d}.wav"
        part.write_bytes(_gemini_tts(cfg, text))
        total = duration(part)
        cuts = split_points(total, [len(scenes[i]["narration"]) for i in idx], _silences(part))
        start = 0.0
        for i, end in zip(idx, cuts):
            dest = workdir / f"voice_{i + 1:02d}.wav"
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(part), "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                 "-af", "silenceremove=start_periods=1:start_threshold=-40dB,areverse,"
                        "silenceremove=start_periods=1:start_threshold=-40dB,areverse",
                 "-ar", "44100", "-ac", "1", str(dest)])
            out[i] = dest
            start = end
    return [p for p in out if p]


def make_narration(cfg: dict, story: dict, workdir: Path) -> list[Path]:
    if cfg.get("providers", {}).get("voice", "elevenlabs") == "gemini":
        return _gemini(cfg, story, workdir)
    return _elevenlabs(cfg, story, workdir)
