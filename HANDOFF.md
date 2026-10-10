# SaveX — Handoff

## 1. What SaveX is
Telegram bot @SaveXStorageBot. A user sends a link and the bot downloads the video / photo / carousel / reel and sends it in Telegram.
Platforms: Instagram (reels, posts, carousels, stories), TikTok (video without watermark, photo slideshows), X/Twitter, Threads, Wikipedia/Wikimedia, Pinterest, CapCut, VK Video, YouTube (video, shorts), plus Facebook, Reddit, Likee, Snapchat Spotlight, Vimeo, Dailymotion, Twitch clips, SoundCloud, Tumblr, and a generic fallback for any site with video or images (including movies, up to 2 GB).
Music: a "🎵 Musiqa" button under every sent video. It recognizes the song, then shows the original plus up to 8 variants (remix, slowed, sped up, cover, live, lyrics, similar tracks by the same artist), each downloadable as MP3 or video. Recognition also works on audio, voice or video the user sends, and there is search by song name.
"🎲 Random musiqa": a 2–3 step taste quiz on first use, about 70% picks from the user's taste and 30% new, 👍/👎 learning, and a full taste reset that reruns the quiz.
Future: SaveX website and app with one unified user ID (savex_id) across bot, web and app. Premium bought in the bot syncs to all three.

## 2. Owner requirements (never violate)
- Do NOT rewrite or redesign the bot. Keep all existing features, commands, handlers, callback_data, DB columns and admin functions. Fix and extend only.
- Very fast and clean, because users pay. One user may send 5–6 links at once, and they must run in parallel.
- Every file is deleted from the server right after it is sent to Telegram, or on error. The disk must never fill up.
- Buttons are uniform in size and style, with short labels.
- Languages: uz (latin), ru, en.
- No referral system.
- Target audience is very large (ads on TikTok/Reels). The architecture must scale by adding workers and servers.

## 3. Plans and payment
- Free: 2 parallel downloads, daily limit, mandatory channel subscription, up to 720p.
- Plus, 5 000 so'm/month: 4 parallel, up to 1080p, no mandatory channels.
- Pro, 15 000 so'm/month: 6 parallel, unlimited, best quality up to 2 GB, priority queue. The owner was choosing between 15 000 and 18 000, so confirm with him.
- Prices and limits live in config. A plans screen clearly lists what each plan includes.
- Payment stays manual: the user picks a plan, the bot shows the owner's card number and the amount, the user sends a receipt photo, and the admin taps ✅ or ❌. Then activation with an expiry date is automatic, with reminders 3 days and 1 day before expiry and an automatic downgrade to Free.

## 4. Tech and infrastructure
- Python, aiogram 3.x, yt-dlp, gallery-dl, SQLAlchemy async. The DB is SQLite at storage/savex.db; a PostgreSQL migration is planned.
- bot.py is the entry point, with venv/ inside the project dir and the systemd service savex-bot (formerly savex).
- A local Telegram Bot API server runs in Docker on 127.0.0.1:8081, which allows uploads up to 2 GB. The bot lowers quality automatically to fit 2 GB.
- Cookies live in cookies/<platform>.txt (Netscape format, gitignored, chmod 600).
- "Music Core" is a music-finding service on the server that belongs only to SaveX. Check its details on the server.
- Repo: github.com/abduraxmonovbobir191-creator/SaveX (currently PUBLIC). CLAUDE.md holds the rules and roadmap, PROGRESS.md the bugs and decisions, DEPLOY.md the Uzbek server guide; deploy.sh does the deploys.
- Server: Contabo VPS, Ubuntu 24.04, accessed via Termius. It hosts many other projects, and SaveX must never affect them.

## 5. Server changes AFTER this code was written (verify first)
- The server was reorganized into /opt/projects/<Name> with per-project systemd slices, and /opt/bots was removed. deploy.sh, DEPLOY.md and CLAUDE.md still say /opt/bots/SaveX: find the real path and service name, then update them. The server map is in /opt/projects/README.md and /opt/projects/HANDOVER.md.
- 2026-10-07: security incident (SSH password guessed, malware, since cleaned). Still to do:
  - Rotate the bot token in @BotFather.
  - Change the Instagram bot account's password and export fresh cookies; treat cookies/instagram.txt as exposed.
  - Rotate the other API keys in .env.
- Do NOT enable UFW. It broke SSH and bot IPv6 twice.

## 6. Status (as of 2026-10-05)
- Phase 0 (audit) is done: 36 bugs listed in PROGRESS.md.
- Phase 1a (high/critical bugs) is done, merged as PR #1 (c13f44e), deployed and running.
- Instagram cookie support is commit e28c8c8 on branch ccr-8d0c370f-wfwxpi. It was NOT merged to main as of 2026-10-05. Check this first, then merge and deploy. Until it is deployed, Instagram image posts fail: yt-dlp says "There is no video in this post", then gallery-dl says "HTTP redirect to login page".
- Music features are not built yet (Phase 5). "Musiqalarim" only shows history.
- Open items:
  - Bug #15, second half: existing channel members are counted as "joined via bot".
  - download.py.backup is still tracked in git.
  - pyrogram is not in requirements (the userbot is paused).
  - The history table has no file_id.
  - Port 8081 is hard-coded.

## 7. Remaining roadmap
- 1b: remaining medium/low bugs, #15, and file_id in history. Global error handler with rate-limited admin alerts. Retries for flood waits, timeouts and network errors. Unify all keyboards.
- 2: PostgreSQL (asyncpg + Alembic) with a one-time SQLite data migration. Containers savex-postgres and savex-redis, with no public ports. users.savex_id (UUID) as the unified ID. A subscriptions table as the single source of truth. A minimal FastAPI skeleton (/v1/me, /v1/subscription, Telegram Login auth).
- 3: Redis queue (arq) with separate workers. Per-plan parallel limits (2/4/6) and Pro priority. yt-dlp concurrent fragments plus aria2c. Choose the format by size before downloading. Upload by local path through the local Bot API. A file_id cache for instant re-sends. Temp cleanup and a disk guard. Queue position and progress messages.
- 4: An extractor registry with the fallback chain yt-dlp → gallery-dl → generic og:video/og:image scraper, covering all platforms in §1. Carousels sent as media groups. Clear messages for private or unsupported links. A smoke test script.
- 5: The music features in §1. Use shazamio now, behind a provider interface so ACRCloud/AudD can be added later. Cache audio file_ids.
- 6: Plans and payment as in §3. i18n in uz/ru/en. Inline mode, an MP3 button, a quality picker and admin stats.

## 8. Workflow (keep it)
- Code is written by Claude Code (Claude app → Code), which is connected to GitHub only, not to the server.
  - One phase per NEW session.
  - Model: Sonnet (Opus only for heavy phases).
  - Every session starts with "Read CLAUDE.md and PROGRESS.md".
  - One complete English prompt per session. The owner answers questions in a single message.
- Claude Code pushes to a branch and opens a PR. The owner merges it into main from a mobile browser, then deploys on the server.
- Server work: the owner uses Termius on a phone and has no desktop.
  - Routine: check first, back up the DB and .env, update, verify the logs.
  - Never run commands that affect other projects.
- The owner speaks Uzbek. Explain things to him in short Uzbek steps with copy-paste commands.
