"""Shared helpers: config, paths, HTTP with retries, ffmpeg/ffprobe wrappers."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
FONTS = ASSETS / "fonts"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def env(name: str, required: bool = True) -> str:
    val = os.environ.get(name, "").strip()
    if not val and os.environ.get("ALL_SECRETS"):
        # the workflow passes every GitHub secret at once, so new services need no workflow edits
        try:
            val = str(json.loads(os.environ["ALL_SECRETS"]).get(name, "")).strip()
        except json.JSONDecodeError:
            pass
    if required and not val:
        sys.exit(f"Missing secret/env var: {name}. Add it in GitHub → Settings → Secrets → Actions.")
    return val


def http(method: str, url: str, *, retries: int = 4, timeout: int = 180, **kw) -> requests.Response:
    """HTTP request with retries on network errors, 429 and 5xx."""
    last = None
    for attempt in range(retries):
        try:
            r = requests.request(method, url, timeout=timeout, **kw)
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}: {r.text[:300]}"
                wait = 10 * (attempt + 1)
                log(f"  retrying in {wait}s ({last})")
                time.sleep(wait)
                continue
            return r
        except requests.RequestException as e:  # network hiccup
            last = str(e)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Request failed after {retries} tries: {url} — {last}")


def run(cmd: list[str]) -> None:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd[:6])}…\n{res.stderr[-2000:]}")


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def read_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
