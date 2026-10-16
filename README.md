# Kahani Ghar — automated Hindi kids' story channel

Every Saturday this repo makes a complete 8–10 minute Hindi moral-story video and uploads it to YouTube:

1. **Claude** writes a new story (Akbar-Birbal, Panchatantra, Tenali Raman or village tale — rotating, never repeating)
2. **Gemini** draws ~24 storybook illustrations in a consistent style
3. **ElevenLabs** narrates it in **your cloned voice**
4. The video is assembled with gentle zoom, music and Hindi subtitles, plus a thumbnail
5. It's uploaded to YouTube as **Made for Kids**, scheduled to go public 24 hours later
6. You get a GitHub notification with the link — watch it on your phone, done

**Your job:** ~10 minutes a week to watch the video before it goes public.

👉 **First time? Follow [SETUP.md](SETUP.md).**

## Everyday things

| I want to… | Do this |
|---|---|
| Make a video right now | **Actions** tab → *Make weekly story video* → **Run workflow** |
| Suggest a story idea | Same, and type the idea in the *topic* box |
| Change channel name, story types, schedule delay, voice speed | Edit `config.yaml` (pencil ✏️ icon) |
| Keep videos private until I publish them | `config.yaml` → `publish_mode: "private"` |
| Add background music | Upload `.mp3` files into `assets/music/` |
| Change the day/time | `.github/workflows/weekly-video.yml` → the `cron` line |
| See all stories made | `data/stories_done.json` |
| Fix an error | Open the ⚠️ issue, copy the red error lines from the log, paste to Claude |

## Monthly cost (4 videos)

| Service | Cost |
|---|---|
| ElevenLabs Starter (your voice) | $6 |
| Gemini illustrations (~25 × $0.034 per video) | ~$4 |
| Claude API (story writing) | ~$1 |
| GitHub, YouTube API | free |
| **Total** | **~$11/month** |
