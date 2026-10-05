# SaveX — Progress

## Phase 1a — HIGH/CRITICAL bugs (done)

Verified by code-level smoke tests only (aiogram 3.31, yt-dlp 2026.8.19, a local HTTP server
serving an mp4, ffmpeg). **Nothing was run against live Telegram, Instagram, YouTube or
TikTok**, so the real-platform behavior (Instagram carousels via gallery-dl, YouTube cookies)
still needs a check on the server.

Fixed (bug numbers from the table below; marked in the table too):

| # | What changed |
|---|---|
| 1 | `admin/channels.py`: reads `message.forward_origin` (`MessageOriginChannel`), `forward_from_chat` kept only as a fallback. |
| 2 | `config.ensure_runtime_dirs()` (storage/, storage/temp/, SQLite DB folder) runs in `bot.py` and `init_db.py`. `cleanup_stale_temp()` drops temp leftovers older than 1 h at start. CSV export also creates the folder and removes the file in `finally`. |
| 3 | `gallery-dl>=1.30.0` added. Also `sqlalchemy[asyncio]`: SQLAlchemy 2.1 no longer pulls in `greenlet`, so a fresh `pip install -r requirements.txt` crashed at import. |
| 4 | "🎬 Videolarim" / "🎵 Musiqalarim" handled in `library.py` from `DownloadHistory` (types `video` / `audio`, last 15, title + link + date). |
| 6 | `ignoreerrors` removed. `services/downloader/errors.py` maps errors to locale keys: `err_private`, `err_login`, `err_unsupported`, `err_too_large`, `err_no_media`, `err_unavailable`, `err_generic`. Texts in `locales/{uz,ru,en}.json`, language from `User.language`. yt-dlp skips files over `max_filesize` silently, so a missing output file is raised as `TooLargeError`. |
| 7 | `noplaylist=True` always; only a `youtube.com/playlist?...` link is a playlist. `playlistend=10` caps every extraction/download. |
| 8, 9 | Each job gets a private dir `storage/temp/<uuid>/` removed in `finally` (video, audio, gallery, gallery-dl, quality picker). The gallery send also handles the 1-file case (Telegram rejects 1-item albums). |
| 10 | `html.escape` on all user text in HTML messages (feedback, admin reply, receipts, cabinet, user card, top users, channel titles, quality picker, Wikipedia). Non-text feedback no longer renders as `None` (uses caption or `—`). |
| 13 | Buy button carries `buy:<plan>:<months>`; the price is read from `crud.get_plan_prices` when the order is created. Old `buy:plan:months:price` buttons still work but their price is ignored. Unknown plan/months → alert, no order. |
| 15 | `get_chat_member` errors skip the channel (logged) instead of blocking the user. |
| 34 | `download.py.bak` and `ig.json` removed from the index and added to `.gitignore`. |

Also done (infra): `deploy.sh` / `DEPLOY.md` now use `/opt/bots/SaveX`, see Decisions.

Not touched in 1a (Medium/Low, planned for 1b): #5, #11, #12, #14, #16-#33, #35, #36 and the
second half of #15 (users who were already members are counted as "joined via bot").

## Phase 1a-2 — Instagram login (cookies) (done)

Cause of the server log (`There is no video in this post` from yt-dlp, then `HTTP redirect to
login page` from gallery-dl): the Instagram image/carousel path had no login cookies. The only
cookie support was `storage/cookies.txt`, passed to yt-dlp only (and to gallery-dl only when
present), and its failure was shown as a generic "no media" message.

Tested with code-level smoke tests (fake bot/message, mocked gallery-dl and yt-dlp errors, a
local HTTP server for the real yt-dlp path). **Not run against live Instagram**: a real login
session is needed on the server to confirm images/carousels end to end.

- **One mechanism, `app/services/cookies.py`.** `cookies/<platform>.txt` for instagram,
  youtube, tiktok, twitter, pinterest; env `<PLATFORM>_COOKIES` overrides the path
  (`INSTAGRAM_COOKIES`, ...). Default dir is `<project>/cookies/`, i.e.
  `/opt/bots/SaveX/cookies/instagram.txt` on the server. No platform file → legacy
  `storage/cookies.txt` still works for every URL. A file without the Netscape header is ignored
  with a warning (path only).
- **yt-dlp and gallery-dl both use it.** gallery-dl gets `--cookies <file>` (read-only). yt-dlp
  gets a private copy in the job dir (mode 600, deleted with it): yt-dlp saves the cookie jar back
  on exit, so a shared file could be corrupted by parallel jobs. Side effect: yt-dlp's refreshed
  cookies are not kept, the file is refreshed manually (see DEPLOY.md).
- **Instagram "no video in this post"** goes straight to gallery-dl (yt-dlp errors other than
  login/private always fall back to it). `gallerydl.download_sync` now raises `GalleryDlError`
  (stderr tail, no cookie data) when it fails with no files, so the reason is known.
  `classify_error` maps "HTTP redirect to login page", `login`, `checkpoint` to `err_login`.
  If gallery-dl says login/private, that reason replaces yt-dlp's generic "no media".
- **Missing/expired cookies.** On `err_login` for a cookie platform the user gets `err_cookies`
  ("the bot's {platform} session (cookies) is missing or expired, admin notified", uz/ru/en) and
  the admins get `⚠️ Instagram cookies expired` (or `cookies missing` when no file exists), at most
  once per 10 minutes per platform (in memory, so it resets on restart). This also applies to
  YouTube "sign in to confirm you're not a bot" and the other cookie platforms.
- **Carousels.** gallery-dl fetches up to 20 files, yt-dlp up to 20 items for Instagram (10 for
  everything else, e.g. YouTube playlists). `_send_group` sends albums of 10 and splits larger
  sets (1 s pause between albums; a lone leftover file is sent as a single photo/video).
- **Secrets.** Cookie files are only read to check the first line; contents are never logged
  (the test asserts a sentinel value never reaches the logs). `deploy.sh` never touches `cookies/`
  and refuses to deploy a revision that tracks files under it (`git fetch` + `merge --ff-only`
  instead of `git pull`, same effect). `cookies/` is created at startup with mode 700.
- **DEPLOY.md (Uzbek)** has a new "Cookies" section: files, adding the first time, refreshing,
  manual check, security.

## Phase 0 — Audit (done)

Audit was done by reading the code only. The bot was not run, so nothing below is
confirmed against live Telegram or live sites. Line numbers refer to commit `4b76f3b`.

Severity: **Critical** = feature broken / data loss / bot can't start ·
**High** = common user-facing failure or abuse · **Medium** = edge case / leak ·
**Low** = cleanup / cosmetic.

### Bugs

| # | File:line | Description | Severity |
|---|---|---|---|
| 1 | app/handlers/admin/channels.py:54,58 | Adding a channel filters on `F.forward_from_chat`. Bot API 7.0 replaced that field with `forward_origin` (`MessageOriginChannel`), so Telegram no longer sends it and forwarded posts always land in `ch_add_invalid`. **Admins cannot add mandatory channels.** | Critical · ✅ fixed 1a |
| 2 | config.py:8, app/handlers/admin/panel.py:226-228 | Default DB is `./storage/savex.db`, but nothing creates `storage/`, which is gitignored. On a fresh clone aiosqlite fails at startup. CSV export `open()`s `storage/temp/...` and fails until some download has created the folder. | Critical · ✅ fixed 1a |
| 3 | requirements.txt | Missing `gallery-dl` (called via `python -m gallery_dl` in services/downloader/gallerydl.py:25) and `pyrogram` (create_session.py). System tools ffmpeg/ffprobe/aria2c and the local `telegram-bot-api` server are not documented anywhere. | High · ✅ fixed 1a (gallery-dl; pyrogram still not listed) |
| 4 | app/keyboards/reply.py:6 | The main-menu buttons "🎬 Videolarim" and "🎵 Musiqalarim" have no handlers, so tapping them does nothing. `crud.get_history_by_type` exists for them but is never used. | High · ✅ fixed 1a |
| 5 | app/handlers/user/library.py:12 | Calls `crud.get_history`, which doesn't exist (AttributeError). The "📋 Kutubxona" trigger isn't on any keyboard. | Medium |
| 6 | app/handlers/user/download.py:34 | `ignoreerrors: True` makes `extract_info` return `None` instead of raising. The error branches at :449-462 (YouTube cookies, unsupported URL, text-only post) therefore never run, and the user always gets the generic "Media topilmadi". | High · ✅ fixed 1a |
| 7 | app/handlers/user/download.py:33,171-190 | `noplaylist: False`. A YouTube link containing `&list=` is treated as a gallery, and `_download_gallery_sync` downloads **every** entry of the playlist even though only 10 are sent. This is slow and can fill the disk or block a worker for a long time. | High · ✅ fixed 1a |
| 8 | app/handlers/user/download.py:293-316, 547-566, 603-645 | Temp files are deleted only on the success path. If `answer_video`/`answer_audio` raises, or `_run_download` fails partway, files and `.thumb.jpg` stay in `storage/temp`. Gallery downloads that fail also leave partial files. This breaks the try/finally rule. | High · ✅ fixed 1a |
| 9 | app/handlers/user/download.py:550,601 | Output template `storage/temp/{chat_id}_%(id)s.%(ext)s` is shared between concurrent jobs. If the same user asks for two qualities of one video, the jobs overwrite or delete each other's file. | Medium · ✅ fixed 1a (per-job dirs) |
| 10 | app/handlers/user/feedback.py:39, premium.py:76-79, menu.py:28, admin/panel.py:257-264,153, download.py:359,530 | User-controlled text (message text, names, titles, Wikipedia extract) goes into `parse_mode="HTML"` without `html.escape`. A `<` or `&` causes TelegramBadRequest. In feedback.py the error is swallowed, so the admin silently never gets the message. | High · ✅ fixed 1a |
| 11 | app/handlers/user/feedback.py:39,72 | Only text is handled. A photo, voice or sticker relays as "💬 None", and an admin reply that isn't text sends "None" to the user. | Medium |
| 12 | app/handlers/user/premium.py:63 | `@router.message(F.photo)` catches **every** photo. Feedback and admin-reply photos are swallowed: premium runs before feedback in the router order, and the handler returns without passing the update on. | Medium |
| 13 | app/keyboards/inline.py:26, premium.py:44-45 | The price is stored inside `callback_data` (`buy:plan:months:price`) and trusted. Old buttons keep old prices after an admin changes them, and a crafted callback can create an order at any price. The admin sees the amount, but this is still fragile. | High · ✅ fixed 1a |
| 14 | app/handlers/user/premium.py:10, feedback.py:14, favorites.py:9, download.py:26 | `AWAITING_RECEIPT`, `REPLY_MAP`, `FAV_CACHE` and `PENDING` exist only in memory. They never shrink (memory leak) and are lost on restart, so receipts are ignored, admin replies go nowhere and buttons report "eskirgan". | Medium |
| 15 | app/services/channels.py:31-35 | If `get_chat_member` raises (for example, the bot was removed as admin of a channel), the user counts as not joined and is blocked forever. Users who were already members are also counted as "joined via bot" (:37-38, :45). | High · ◐ 1a: lookup errors no longer block users; "already member counted as joined" still open |
| 16 | app/handlers/user/download.py:424 | The ban is checked only in `handle_link`. Banned users can still use the Wikipedia handler, menu, premium, favorites and feedback. | Medium |
| 17 | app/database/crud.py:71-72,81 | The daily reset compares `date.today()` (server local time) with `utcnow()`, so the day boundary is off. The limit is spent before the download, so failed downloads still use it. The quality picker and MP3 button don't spend it, so one link can produce unlimited files. | Medium |
| 18 | app/handlers/user/menu.py:19-22,30 | The cabinet shows limits hard-coded as "7"/"30" instead of `crud.FREE_LIMIT`/`PLUS_LIMIT`. `daily_downloads` from a previous day is shown until the next download resets it. | Low |
| 19 | app/handlers/user/start.py:67, admin/channels.py:83, admin/prices.py:55, admin/panel.py:285 | `message.text` is used without a None check. A sticker, photo or contact sent in these FSM states raises AttributeError. | Medium |
| 20 | app/handlers/admin/channels.py:90 | `MandatoryChannel.chat_id` is unique, so re-adding a channel that was removed (deactivated) raises IntegrityError. | Medium |
| 21 | app/handlers/admin/panel.py:80-87 (and other `edit_text` callbacks) | The user card is sent as a photo (:271). Its "⬅️ Panelga qaytish" button calls `edit_text` on a photo message, which raises. The callback is never answered and the button spins. | Medium |
| 22 | app/services/scheduler.py:18,38-39 | `user.premium_type.upper()` crashes if the type is None. The outer `except: pass` hides every error and skips all remaining users in that run. | Medium |
| 23 | app/handlers/user/download.py:417-419 | Only messages that **start** with `http` are handled. "look https://…", `HTTPS://` and multi-line texts either fail or pass the whole text to yt-dlp as the URL. | Medium |
| 24 | app/handlers/user/download.py:511-566 | No live-stream guard (`is_live`) and no overall download timeout. A live or hung download holds a semaphore slot or worker indefinitely. | Medium |
| 25 | app/handlers/user/download.py:214-227, 595 | `_fit_height` runs a second full `extract_info` plus one sequential HTTP Range probe per format, outside the semaphore, before every quality download. This is slow. | Low |
| 26 | app/database/crud.py:31 | `"x.com" in u` also matches `netflix.com` and similar hosts, so platform stats are wrong. The two `detect_platform` functions (crud.py:27, services/downloader/router.py:4) disagree. | Low |
| 27 | bot.py:18,24 | The local Bot API URL is hard-coded. The scheduler task reference isn't kept and isn't cancelled on shutdown. The session isn't closed. There's no clear error when `BOT_TOKEN` is missing. | Low |
| 28 | app/database/models.py | `create_all` only; no migrations. Naive `utcnow()` datetimes. No unique constraint on `ChannelJoinRecord(channel_id,user_id)` or `PriceSetting(plan,months)`. `user_id` columns store the telegram_id while `User.id` is a separate PK (mixed IDs, which Phase 2 addresses). `DownloadHistory.url` is String(500), which will fail on PostgreSQL for long URLs. | Medium |
| 29 | app/handlers/admin/panel.py:396-412 | Broadcast doesn't handle `TelegramRetryAfter`, so flood-wait users are counted as failed. | Low |
| 30 | app/handlers/admin/panel.py:334-350, orders.py:24-25 | Granting to an unknown ID still reports success. `approve_order` crashes if the user row is missing. | Low |
| 31 | app/handlers/user/premium.py:83-97 | If every send to the admins fails (wrong `ADMIN_IDS`), the user is still told "Chekingiz adminga yuborildi". | Low |
| 32 | app/handlers/user/favorites.py:45-56 | Sends **all** favorites one by one with no pagination (flood risk). The same file can be added to favorites any number of times. | Low |
| 33 | app/handlers/user/download.py:18,47, services/downloader/* | Dead or duplicate code. `detect_platform`/`get_downloader` are imported but unused. `_estimate_size` is unused. `common.py`, `generic.py` and `instagram/*` duplicate download.py, and `instagram/image.py` has a different signature. Nine downloader files are empty. | Low |
| 34 | app/handlers/user/download.py.bak, ig.json | Backup file and a stray `ig.json` (content `null`) are committed. `.gitignore` already has `*.bak*`, but these files were tracked before that line was added. | Low · ◐ 1a: .bak and ig.json untracked; `download.py.backup` still tracked |
| 35 | app/handlers/user/premium.py:9 | The card number is hard-coded and should be an env var or admin setting. | Low |
| 36 | various | Logging uses `print`/`traceback.print_exc` and silent `except: pass` instead of `logging`. `asyncio.get_event_loop()` is deprecated. | Low |

### Platforms (from code reading, untested)

| Platform | State |
|---|---|
| Instagram reels/video | Works via yt-dlp. Usually needs `storage/cookies.txt`. |
| Instagram photo / carousel | yt-dlp has no image support, so these go to the gallery-dl fallback. That fallback breaks on a fresh server because gallery-dl isn't in requirements (#3). |
| TikTok, Twitter/X, Facebook, Pinterest, Reddit, etc. | Generic yt-dlp path. Image-only posts depend on gallery-dl. |
| YouTube | Often blocked without cookies ("sign in / not a bot"), and the specific error message never shows (#6). Playlist links download whole playlists (#7). |
| VK / vkvideo.ru | Uses aria2c as the external downloader. Fails if aria2c isn't installed. |
| Threads | Listed in Help. yt-dlp support is weak, so it relies on gallery-dl. |
| Wikipedia | Custom REST-summary handler. HTML escaping bug (#10). |
| Telegram (t.me), LinkedIn, CapCut, Canva, Edits, "toki" | Detected in `services/downloader/router.py`, but no dedicated code exists and the router isn't wired in. They fall to generic yt-dlp, which mostly doesn't support them. |
| Music services (Spotify, Apple Music, Shazam-style recognition) | Not supported (Phase 5). |

### UI / keyboard inconsistencies

- Keyboards are spread across many files: `keyboards/inline.py`, `keyboards/reply.py`,
  `keyboards/channels.py`, plus inline builders inside `handlers/admin/panel.py`,
  `admin/channels.py`, `admin/prices.py`, `user/favorites.py`, `user/start.py` and
  `services/channels.py`.
- There are two versions of the registration keyboards. `start.py` has its own language
  keyboard (uz/ru only), phone keyboard and region keyboard (14 regions, with `'`).
  The unused `keyboards/language.py` (6 languages), `keyboards/phone.py` and
  `keyboards/region.py` (13 regions, `‘`, "Toshkent" instead of "Toshkent shahri/viloyati")
  differ from them.
- `keyboards/quality.py` is unused. Its `q:*` callback_data has no handler, while the
  live quality keyboard uses `dl:*`.
- Main-menu "🎬 Videolarim" / "🎵 Musiqalarim" do nothing (#4). "📋 Kutubxona" is
  handled but isn't on any keyboard (#5).
- The language is saved at registration, but all text is hard-coded Uzbek (no locales).
- The Help text lists Instagram/TikTok/X/Threads/Wikipedia/Pinterest but leaves out
  YouTube, VK and Facebook, which the code also handles.
- Back buttons are worded differently: "⬅️ Ortga", "⬅️ Orqaga", "⬅️ Panelga qaytish"
  and "⬅️ Bekor qilish".
- An unknown text gets no reply at all (no fallback handler).

### Decisions

- **Phase 0 changes no bot behavior.** The only non-doc change is adding `cookies/` and
  `.deploy_prev_commit` to `.gitignore`.
- The tracked `download.py.bak` and `ig.json` are left as they are and listed (#34).
  Deleting them is cleanup for Phase 1.
- `deploy.sh` runs `mkdir -p storage/temp` before restarting. This is a deploy step, not a
  code change, and it works around #2 on servers until Phase 1 fixes it in code.
- `deploy.sh` saves the previous commit to `.deploy_prev_commit`, so
  `./deploy.sh rollback` can go back one deploy.
- Alembic doesn't exist yet. `deploy.sh` runs `alembic upgrade head` only when
  `alembic.ini` is present, which will start working once Phase 2 adds it.
- There's no `docker-compose.yml`, so `deploy.sh` restarts the systemd unit `savex`.
  It switches to Docker automatically if a compose file is added.
- The locales rule is recorded as the target state. Text moves into
  `locales/{uz,ru,en}.json` gradually, starting in Phase 1.

### Decisions — Phase 1a

- **Locales started.** `locales/{uz,ru,en}.json` + `app/services/i18n.py` (`t(key, lang)`,
  falls back to `uz`, then to the key). Only the new/changed texts live there so far (download
  errors, history lists); the rest stays hard-coded Uzbek until Phase 6. Registration only
  stores `uz`/`ru`, so `en` is used only once a user has that value.
- **Error handling.** For `err_login` / `err_private` gallery-dl is not tried (same cookies,
  it can't help). Any other yt-dlp failure still falls back to gallery-dl first, then shows the
  mapped message of the original yt-dlp error.
- **Playlists.** An explicit YouTube playlist link still goes through the old "gallery" path
  (max 10 items sent as an album). `watch?v=…&list=…` is a single video.
- **Videolarim / Musiqalarim** show links, not files: `DownloadHistory` has no `file_id`, and
  adding one needs a schema change (Phase 2). To get the file again the user re-sends the link
  (the file_id cache makes that fast).
- **`callback_data`.** The `buy:` format changed on purpose (security); the old format is still
  parsed. No other callback_data was renamed.
- **Service name.** systemd unit is now `savex-bot` (was `savex`) so it can't clash with other
  projects on the shared server. `deploy.sh` refuses to manage a unit not starting with
  `savex`. On a server that still has the old `savex` unit: `systemctl disable --now savex`,
  then create `savex-bot` (DEPLOY.md).
- **deploy.sh isolation.** Runs only inside its own checkout (checks `git rev-parse
  --show-toplevel`), only `venv/bin/python -m pip` (creates `venv` if missing; no system-wide
  install any more), docker only as `docker compose -p savex …` (no `--remove-orphans`), only
  `systemctl restart <savex-unit>`. No global docker/systemctl/kill commands.
- **ig.json.** Nothing in the repo reads it (content was `null`), so I couldn't tell what the
  server expects of it. `deploy.sh` moves the server's `ig.json` to `storage/ig.json`
  (gitignored) before `git pull` and leaves a symlink at the old path, because the pull that
  stops tracking the file would otherwise delete it. If something expects it elsewhere, say so.
- **Left as is:** `app/handlers/user/download.py.backup` is also tracked (covered by `*.bak*`
  in `.gitignore`, but still in the index); remove it with `git rm --cached` in 1b if wanted.
  `pyrogram` is still not in requirements (only the unused `create_session.py` needs it).
  Port 8081 for the local Bot API is still hard-coded (DEPLOY.md tells you to check it).
- **Rule recorded in CLAUDE.md:** later Postgres/Redis containers are `savex-postgres` /
  `savex-redis`, no public ports, no clashes with other projects.
