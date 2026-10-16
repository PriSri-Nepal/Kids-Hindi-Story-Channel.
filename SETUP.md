# One-time setup (about 1 hour, all on your phone)

You'll create 4 keys, clone your voice, and paste 7 "secrets" into GitHub. After that, everything runs by itself.

Keep a notes app open — you'll copy several codes. **Never share these codes with anyone or post them publicly.**

---

## Step 0 — Put the project on GitHub · 10 min

Tip: in your phone browser, turn on **Desktop site** for github.com — the buttons are easier to find.

1. Download **kids-story-channel.zip** and **weekly-video.yml** from the Claude chat to your phone.
2. On github.com tap **+** → **New repository** → name `kids-story-channel` → **Private** → tick **Add a README file** → **Create repository**.
3. In the repo tap **Add file** → **Upload files** → choose **kids-story-channel.zip** → **Commit changes**. (Don't unzip it — GitHub will do that.)
4. Tap **Add file** → **Create new file**. In the name box type exactly
   `.github/workflows/weekly-video.yml`
   (each `/` makes a folder). Open **weekly-video.yml** on your phone, **Select all → Copy**, paste it into the big box → **Commit changes**.

The zip unpacks itself the first time the workflow runs (Step 7).

## Step 1 — Claude API key (writes the stories) · 5 min

> This is separate from your Claude app subscription.

1. Open **console.anthropic.com** and sign up / log in.
2. **Billing** → add a card and buy **$5** of credit (lasts months).
3. **API Keys** → **Create Key** → name it `story-channel` → copy it.
4. Save in notes as: `ANTHROPIC_API_KEY = sk-ant-...`

## Step 2 — Gemini API key (draws the pictures) · 5 min

1. Open **aistudio.google.com** and sign in with your Google account.
2. Tap **Get API key** → **Create API key** → copy it.
3. Image generation isn't free, so tap **Set up billing** next to the key and add a card (expect about $4/month).
4. Save as: `GEMINI_API_KEY = AIza...`

## Step 3 — Your voice clone (ElevenLabs) · 15 min

**Record your voice first** (phone voice-recorder app is fine):
- Quiet room, no fan, no music, phone 20 cm from your mouth.
- Read any Hindi story aloud for **2–3 minutes** in your warm storytelling voice — the exact tone you want in the videos.
- Pause naturally, change expression for different characters.

Then:
1. Open **elevenlabs.io** → sign up → choose the **Starter** plan ($6/month — needed for commercial use on YouTube).
2. **Voices** → **Add a new voice** → **Instant Voice Clone**.
3. Upload your recording, name it `My Story Voice`, tick the box confirming it's your own voice → **Save**.
4. Tap the voice's **⋯** menu → **Copy voice ID**. Save as: `ELEVENLABS_VOICE_ID = ...`
5. Profile icon → **API Keys** → **Create API key** (allow *Text to Speech* and *Voices: read*) → copy. Save as: `ELEVENLABS_API_KEY = sk_...`
6. Try it: type a Hindi sentence in **Text to Speech** with your voice. If it sounds off, add another clean recording to the voice.

## Step 4 — Your YouTube channel · 5 min

1. In the YouTube app: profile → **Create a channel** (if you don't have one). Use your channel name.
2. Visit **youtube.com/verify** and verify your phone number (needed for custom thumbnails).
3. Open **studio.youtube.com** (desktop-site mode in your phone browser) → **Settings** → **Channel** → **Advanced settings** → Audience: **"Yes, set this channel as made for kids"** → Save.

## Step 5 — Let the robot upload to YouTube · 20 min

This is the longest step. Go slowly; tip: switch your phone browser to **Desktop site**.

**5a. Create a Google Cloud project**
1. Open **console.cloud.google.com** (same Google account as the channel). Accept terms.
2. Top bar → project picker → **New project** → name `kids-story-channel` → **Create**, then select it.

**5b. Turn on the YouTube API**
1. Menu ☰ → **APIs & Services** → **Library**.
2. Search **YouTube Data API v3** → open → **Enable**.

**5c. Consent screen**
1. Menu ☰ → **APIs & Services** → **OAuth consent screen** (may be called *Google Auth Platform*) → **Get started**.
2. App name `Story Uploader`, support email = yours → Next.
3. Audience: **External** → Next → contact email = yours → Next → agree → **Create**.
4. Open **Audience** → under *Publishing status* tap **Publish app** → Confirm.
   *(Important: if you skip this, the connection stops working after 7 days.)*

**5d. Create the login keys**
1. **Clients** (or *Credentials* → *Create credentials* → *OAuth client ID*).
2. Application type: **Web application**, name `uploader`.
3. Under **Authorized redirect URIs** → **Add URI** → paste exactly:
   `https://developers.google.com/oauthplayground`
4. **Create** → copy both values. Save as:
   `YT_CLIENT_ID = ....apps.googleusercontent.com`
   `YT_CLIENT_SECRET = GOCSPX-...`

**5e. Get the permanent upload permission (refresh token)**
1. Open **developers.google.com/oauthplayground**.
2. Tap the **⚙ gear** (top right) → tick **Use your own OAuth credentials** → paste your Client ID and Client secret → close.
3. In the left box *"Input your own scopes"* paste:
   `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube`
4. **Authorize APIs** → choose your Google account → **choose your channel** if asked.
5. You'll see *"Google hasn't verified this app"* — that's normal, it's your own app. Tap **Advanced** → **Go to Story Uploader (unsafe)** → **Continue / Allow**.
6. Back in the playground tap **Exchange authorization code for tokens**.
7. Copy the **Refresh token**. Save as: `YT_REFRESH_TOKEN = 1//...`

## Step 6 — Paste the 7 secrets into GitHub · 10 min

1. Open your repo on **github.com** → **Settings** → **Secrets and variables** → **Actions**.
2. For each line below tap **New repository secret**, type the *Name* exactly, paste the value, **Add secret**:

| Name | Value from |
|---|---|
| `ANTHROPIC_API_KEY` | Step 1 |
| `GEMINI_API_KEY` | Step 2 |
| `ELEVENLABS_API_KEY` | Step 3 |
| `ELEVENLABS_VOICE_ID` | Step 3 |
| `YT_CLIENT_ID` | Step 5d |
| `YT_CLIENT_SECRET` | Step 5d |
| `YT_REFRESH_TOKEN` | Step 5e |

3. Now delete those codes from your notes app.

## Step 7 — Test it · 30 min (mostly waiting)

Install the **GitHub** app on your phone and log in — that's where you'll get "video ready" notifications.

1. **Test the engine (free):** repo → **Actions** → **Make weekly story video** → **Run workflow** → turn **test mode ON** → Run. In ~3 minutes it should turn green ✅.
2. **First real video:** Run workflow again with test mode **OFF** and upload **OFF**. Takes ~20–30 min. When green, open the run → **Artifacts** → download `video-files` and watch `final.mp4`. Check the voice, pictures and story.
3. **Go live:** Run once more with upload **ON**. You'll get a notification with the YouTube link. It's uploaded privately and goes public 24 hours later.

From now on it runs **every Saturday 8:00 AM Nepal time** and publishes **Sunday 8:00 AM**.

## Your weekly 10 minutes

1. Saturday: GitHub notification "🎬 New video ready".
2. Watch it (link in the notification).
3. Happy → do nothing, it publishes Sunday. Not happy → YouTube Studio app → the video → Visibility → **Private**, and tell Claude what was wrong.
4. Close the GitHub issue.

## Optional

- **Background music:** YouTube Studio → **Audio Library** → download 2–3 calm instrumental tracks → in GitHub open `assets/music` → **Add file** → **Upload files**.
- **More videos per month:** ElevenLabs Starter covers ~4 videos. For 2 a week, upgrade to Creator ($22) and add a second `cron` line.
