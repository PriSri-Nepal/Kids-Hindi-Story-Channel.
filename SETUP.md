# Setup — your voice version ($6/month)

This setup uses:
- **ElevenLabs** to narrate every story in **your own cloned voice** (Starter plan, $6/month)
- **Google Gemini** (free) to write the stories
- **Cloudflare** (free) to draw the pictures
- **GitHub** to run everything and **YouTube's API** to upload, both free

You'll create a few keys and paste **8 secrets** into GitHub. Keep a notes app open to copy codes into.
**Never share these codes with anyone.**

---

## Step 0 — Update the project on GitHub (you've already made the repo)

1. In your repo open `.github/workflows/weekly-video.yml` → click the ✏️ pencil → select everything and delete it.
   Open the new **weekly-video.yml** from the Claude chat, copy all of it, paste it in → **Commit changes**.
2. Go back to the main repo page → **Add file** → **Upload files** → choose the new **kids-story-channel.zip** → **Commit changes**.
   (It unpacks itself on the next run. Even if your download is named `kids-story-channel (1).zip`, that's fine.)

## Step 1 — Gemini key (stories + voice) · 5 min · free

1. Open **aistudio.google.com** and sign in with your Google account.
2. Click **Get API key** → **Create API key** → copy it.
3. **Do NOT click "Set up billing".** Without billing you stay on the free tier and can never be charged.
4. Save in notes as: `GEMINI_API_KEY = AIza...`

## Step 2 — Cloudflare (pictures) · 5 min · free, no card

1. Open **dash.cloudflare.com/sign-up** and create a free account (verify your email).
2. On the dashboard home, find **Account ID** (right side, or under the ⋯ menu next to your account name → *Copy account ID*).
   Save as: `CLOUDFLARE_ACCOUNT_ID = ...`
3. Click your profile icon (top right) → **Profile** → **API Tokens** → **Create Token**.
4. Find the **Workers AI** template → **Use template** → **Continue to summary** → **Create Token** → copy it.
   Save as: `CLOUDFLARE_API_TOKEN = ...`

## Step 2b — Your voice clone (ElevenLabs) · 15 min · $6/month

1. On **elevenlabs.io** choose the **Starter** plan ($6/month). The free plan does not allow using the voice in monetized YouTube videos.
2. Record 2–3 minutes of yourself reading a Hindi story in a quiet room (phone recorder is fine).
3. **Voices** → **Add a new voice** → **Instant Voice Clone** → upload the recording → confirm it's your own voice → **Save**.
4. Open your new voice → **⋯** → **Copy voice ID**. Save as `ELEVENLABS_VOICE_ID`.
   (Make sure it's **your cloned voice**, not a voice from the library.)
5. **elevenlabs.io/app/developers/api-keys** → **Create API key** (allow *Text to Speech* and *Voices: read*). Save as `ELEVENLABS_API_KEY` (starts with `sk_`).

Starter gives 30,000 characters a month ≈ 4 videos. In a month with 5 Saturdays the 5th run may stop with an "out of credits" message — that's expected.

## Step 3 — Your YouTube channel · 5 min

1. In the YouTube app: profile → **Create a channel** (if you don't have one).
2. Visit **youtube.com/verify** and verify your phone number (needed for custom thumbnails).
3. Open **studio.youtube.com** → **Settings** → **Channel** → **Advanced settings** → Audience:
   **"Yes, set this channel as made for kids"** → Save.

## Step 4 — Let the robot upload to YouTube · 20 min

This is the longest step. Go slowly.

**4a. Create a Google Cloud project**
1. Open **console.cloud.google.com** (same Google account as the channel). Accept terms.
2. Top bar → project picker → **New project** → name `kids-story-channel` → **Create**, then select it.

**4b. Turn on the YouTube API**
1. Menu ☰ → **APIs & Services** → **Library**.
2. Search **YouTube Data API v3** → open → **Enable**.

**4c. Consent screen**
1. Menu ☰ → **APIs & Services** → **OAuth consent screen** (may be called *Google Auth Platform*) → **Get started**.
2. App name `Story Uploader`, support email = yours → Next.
3. Audience: **External** → Next → contact email = yours → Next → agree → **Create**.
4. Open **Audience** → under *Publishing status* click **Publish app** → Confirm.
   *(Important: if you skip this, the connection stops working after 7 days.)*

**4d. Create the login keys**
1. **Clients** (or *Credentials* → *Create credentials* → *OAuth client ID*).
2. Application type: **Web application**, name `uploader`.
3. Under **Authorized redirect URIs** → **Add URI** → paste exactly:
   `https://developers.google.com/oauthplayground`
4. **Create** → copy both values. Save as:
   `YT_CLIENT_ID = ....apps.googleusercontent.com`
   `YT_CLIENT_SECRET = GOCSPX-...`

**4e. Get the permanent upload permission (refresh token)**
1. Open **developers.google.com/oauthplayground**.
2. Click the **⚙ gear** (top right) → tick **Use your own OAuth credentials** → paste your Client ID and Client secret → close.
3. In the left box *"Input your own scopes"* paste:
   `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube`
4. **Authorize APIs** → choose your Google account → **choose your channel** if asked.
5. You'll see *"Google hasn't verified this app"* — normal, it's your own app. Click **Advanced** → **Go to Story Uploader (unsafe)** → **Continue / Allow**.
6. Back in the playground click **Exchange authorization code for tokens**.
7. Copy the **Refresh token**. Save as: `YT_REFRESH_TOKEN = 1//...`

## Step 5 — Paste the 8 secrets into GitHub · 5 min

1. Your repo → **Settings** → **Secrets and variables** → **Actions**.
2. For each line tap **New repository secret**, type the *Name* exactly, paste the value, **Add secret**:

| Name | From |
|---|---|
| `GEMINI_API_KEY` | Step 1 |
| `CLOUDFLARE_ACCOUNT_ID` | Step 2 |
| `CLOUDFLARE_API_TOKEN` | Step 2 |
| `ELEVENLABS_API_KEY` | Step 2b |
| `ELEVENLABS_VOICE_ID` | Step 2b |
| `YT_CLIENT_ID` | Step 4d |
| `YT_CLIENT_SECRET` | Step 4d |
| `YT_REFRESH_TOKEN` | Step 4e |

3. Delete those codes from your notes app.

## Step 6 — Make your first video

Install the **GitHub** app on your phone and log in — that's where "video ready" notifications arrive.

1. **First real video, not uploaded:** **Actions** → **Make weekly story video** → **Run workflow** → test mode **OFF**, upload **OFF** → Run. Takes ~20–30 min. When green, open the run → **Artifacts** → download `video-files` → watch `final.mp4`.
2. Happy with it? **Run workflow** again with upload **ON**. You'll get a notification with the YouTube link. It's uploaded privately and goes public 24 hours later.

From then on it runs **every Saturday 8:00 AM Nepal time** and publishes **Sunday 8:00 AM**.

## Your weekly 10 minutes

1. Saturday: GitHub notification "🎬 New video ready".
2. Watch it.
3. Happy → do nothing. Not happy → YouTube Studio app → the video → Visibility → **Private**, and tell Claude what was wrong.
4. Close the GitHub issue.

## Tweaks you can make in `config.yaml` (✏️ pencil)

- **Voice speed / expression:** `voice → speed` (0.9 slower, 1.0 normal) and `voice → style`.
- **Switch to the free AI voice:** `providers → voice: "gemini"`.
- **Channel name** in the intro: `channel → name`.
- **Keep videos private until you publish:** `publish_mode: "private"`.

## Upgrading later (when the channel grows)

| Upgrade | Change in config.yaml | Add secret(s) | Cost |
|---|---|---|---|
| Nicer, more consistent pictures | `artist: "gemini"` | none (but enable billing on your Gemini key) | ~$4/mo |
| Better story writing | `writer: "claude"` | `ANTHROPIC_API_KEY` (console.anthropic.com) | ~$1/mo |

No workflow changes needed — just edit the word and add the secret.

## If something breaks

You'll get a GitHub issue "⚠️ Video run failed". Open the log link, copy the red error lines, and paste them to Claude.
Free services have daily limits; if a run fails with "429" or "quota", just run it again the next day.
