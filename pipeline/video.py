"""Step 4 — assemble the video: slow zoom on each picture, narration, music, Hindi subtitles."""
from __future__ import annotations

import json
import random
import re
import subprocess
from pathlib import Path

from .common import ASSETS, FONTS, duration, log, run

MOVES = ["zoom_in", "pan_right", "zoom_out", "pan_left"]


def _ts(t: float) -> str:
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _chunks(text: str, max_len: int = 70) -> list[str]:
    """Split narration into short subtitle lines at sentence/comma boundaries."""
    parts = [p.strip() for p in re.split(r"(?<=[।!?\.])\s+", text) if p.strip()]
    out = []
    for p in parts:
        while len(p) > max_len:
            cut = max(p.rfind(",", 0, max_len), p.rfind(" ", 0, max_len))
            cut = cut if cut > 15 else max_len
            out.append(p[: cut + 1].strip())
            p = p[cut + 1:].strip()
        if p:
            out.append(p)
    return out


def _ass_escape(s: str) -> str:
    return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def _write_ass(cfg: dict, story: dict, timings: list[tuple[float, float]], path: Path) -> None:
    W, H = cfg["video"]["width"], cfg["video"]["height"]
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Sub,Noto Sans Devanagari,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,60,1",
        "Style: Title,Noto Sans Devanagari,110,&H0000E6FF,&H00FFFFFF,&H00301000,&H96000000,-1,0,0,0,100,100,0,0,1,7,4,8,80,80,90,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    lines.append(f"Dialogue: 1,{_ts(0.3)},{_ts(4.5)},Title,,0,0,0,,{{\\fad(400,500)}}{_ass_escape(story['title_hi'])}")
    if cfg["video"].get("subtitles", True):
        for sc, (start, speech) in zip(story["scenes"], timings):
            chunks = _chunks(sc["narration"])
            total = sum(len(c) for c in chunks) or 1
            t = start
            for c in chunks:
                d = speech * len(c) / total
                lines.append(f"Dialogue: 0,{_ts(t)},{_ts(t + d)},Sub,,0,0,0,,{_ass_escape(c)}")
                t += d
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _segment(cfg: dict, img: Path, seconds: float, move: str, out: Path) -> None:
    v = cfg["video"]
    W, H, fps, z = v["width"], v["height"], v["fps"], v["zoom"]
    n = max(int(round(seconds * fps)), 1)
    zexpr = {"zoom_in": f"1+{z}*on/{n}", "zoom_out": f"1+{z}*(1-on/{n})"}.get(move, f"1+{z}")
    if move == "pan_right":
        xexpr = f"(iw-iw/zoom)*on/{n}"
    elif move == "pan_left":
        xexpr = f"(iw-iw/zoom)*(1-on/{n})"
    else:
        xexpr = "(iw-iw/zoom)/2"
    fade_out = max(seconds - 0.35, 0)
    vf = (f"scale={W * 2}:{H * 2},zoompan=z='{zexpr}':x='{xexpr}':y='(ih-ih/zoom)/2':d={n}:s={W}x{H}:fps={fps},"
          f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out:.2f}:d=0.35,format=yuv420p")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(img), "-vf", vf, "-frames:v", str(n),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(fps), str(out)])


def _pick_music() -> Path | None:
    tracks = sorted(p for p in (ASSETS / "music").glob("*") if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg"))
    return random.choice(tracks) if tracks else None


def make_video(cfg: dict, story: dict, images: list[Path], voices: list[Path], workdir: Path) -> Path:
    pause = cfg["voice"]["pause_between_scenes"]
    segs, auds, timings = [], [], []
    t = 0.0
    lead_in = 0.8  # small breath before the first words
    for i, (img, voice) in enumerate(zip(images, voices), 1):
        speech = duration(voice)
        pre = lead_in if i == 1 else 0.0
        seg_len = pre + speech + pause
        timings.append((t + pre, speech))

        wav = workdir / f"a_{i:02d}.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(voice), "-af",
             f"adelay={int(pre * 1000)}:all=1,apad=whole_dur={seg_len:.3f}", "-t", f"{seg_len:.3f}",
             "-ar", "44100", "-ac", "2", str(wav)])
        auds.append(wav)

        shots = img if isinstance(img, (list, tuple)) else [img]
        # never keep one picture on screen too long: split long shots further
        max_shot = float(cfg["video"].get("max_shot_seconds", 8))
        n_parts = max(len(shots), int(-(-seg_len // max_shot)))
        part = seg_len / n_parts
        log(f"  rendering scene {i}/{len(images)} ({seg_len:.1f}s, {n_parts} shots)")
        for k in range(n_parts):
            seg = workdir / f"v_{i:02d}_{k:02d}.mp4"
            move = MOVES[(i + k) % len(MOVES)]
            _segment(cfg, shots[k % len(shots)], part, move, seg)
            segs.append(seg)
        t += seg_len

    for name, items in (("video_list.txt", segs), ("audio_list.txt", auds)):
        (workdir / name).write_text("".join(f"file '{p.resolve()}'\n" for p in items))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(workdir / "video_list.txt"),
         "-c", "copy", str(workdir / "silent.mp4")])
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(workdir / "audio_list.txt"),
         "-c", "pcm_s16le", str(workdir / "narration.wav")])

    # Even out and raise the narration volume (YouTube plays at about -14 LUFS)
    voice_chain = ("highpass=f=70,acompressor=threshold=0.08:ratio=3:attack=5:release=150:makeup=2,"
                   "loudnorm=I=-14:TP=-1.0:LRA=7")
    res = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(workdir / "narration.wav"), "-af",
                          voice_chain + ":print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    try:
        m = json.loads(res.stderr[res.stderr.rindex("{"): res.stderr.rindex("}") + 1])
        voice_chain += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
                        f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    except (ValueError, KeyError):
        pass
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(workdir / "narration.wav"), "-af", voice_chain,
         "-ar", "44100", "-ac", "2", str(workdir / "narration_loud.wav")])

    ass = workdir / "subs.ass"
    _write_ass(cfg, story, timings, ass)

    out = workdir / "final.mp4"
    music = _pick_music()
    vol = cfg["video"].get("music_volume", 0.08)
    # complex shaping = correct Hindi matras and conjuncts
    sub_filter = f"ass=filename='{ass.resolve()}':fontsdir='{FONTS.resolve()}':shaping=complex"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(workdir / "silent.mp4"),
           "-i", str(workdir / "narration_loud.wav")]
    if music and vol > 0:
        log(f"  background music: {music.name}")
        cmd += ["-stream_loop", "-1", "-i", str(music), "-filter_complex",
                f"[0:v]{sub_filter}[v];[2:a]volume={vol},afade=t=in:d=2,afade=t=out:st={max(t - 3, 0):.2f}:d=3[m];"
                f"[1:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]"]
    else:
        cmd += ["-filter_complex", f"[0:v]{sub_filter}[v];[1:a]anull[a]"]
    cmd += ["-map", "[v]", "-map", "[a]", "-t", f"{t:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart", str(out)]
    log("  final render (this takes a few minutes)…")
    run(cmd)
    log(f"Video ready: {out.name} — {t / 60:.1f} minutes")
    return out
