"""Step 6 — upload to YouTube (Made for Kids, private or scheduled)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .common import env, log


def _youtube():
    creds = Credentials(
        token=None,
        refresh_token=env("YT_REFRESH_TOKEN"),
        client_id=env("YT_CLIENT_ID"),
        client_secret=env("YT_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"],
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(cfg: dict, story: dict, video: Path, thumb: Path) -> dict:
    y = cfg["youtube"]
    description = (
        f"{story['youtube_description'].strip()}\n\n"
        f"सीख (Moral): {story['moral_hi']}\n\n"
        "#HindiKahani #MoralStories #HindiStories #KidsStories"
    )
    status = {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": bool(y["made_for_kids"]),
        "containsSyntheticMedia": bool(y.get("contains_synthetic_media", True)),
        "embeddable": True,
        "license": "youtube",
    }
    publish_at = None
    if y.get("publish_mode") == "schedule":
        publish_at = (datetime.now(timezone.utc) + timedelta(hours=y.get("schedule_delay_hours", 24))) \
            .replace(minute=0, second=0, microsecond=0)
        status["publishAt"] = publish_at.isoformat().replace("+00:00", "Z")

    body = {
        "snippet": {
            "title": story["youtube_title"][:100],
            "description": description[:4900],
            "tags": story["tags"][:25],
            "categoryId": y["category_id"],
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": status,
    }
    yt = _youtube()
    log("Uploading to YouTube…")
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=16 * 1024 * 1024, resumable=True,
                                                        mimetype="video/mp4"))
    resp = None
    while resp is None:
        prog, resp = req.next_chunk()
        if prog:
            log(f"  {int(prog.progress() * 100)}%")
    vid = resp["id"]
    log(f"Uploaded: https://youtu.be/{vid}")

    thumb_ok = True
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
    except HttpError as e:
        thumb_ok = False
        log(f"  Could not set thumbnail (verify your channel's phone number in YouTube to allow custom thumbnails): {e}")

    return {"video_id": vid, "url": f"https://youtu.be/{vid}",
            "studio_url": f"https://studio.youtube.com/video/{vid}/edit",
            "publish_at": status.get("publishAt"), "thumbnail_set": thumb_ok}
