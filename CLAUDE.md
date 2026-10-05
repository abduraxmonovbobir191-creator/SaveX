# SaveX — @SaveXStorageBot

Telegram bot that downloads media (video, photo, gallery, audio/MP3) from social
networks by link. Has a free daily limit, paid PLUS/PRO tariffs (manual card payment
approved by admins), mandatory-channel gate, favorites, download history and an
admin panel.

Stack: Python 3.10+, aiogram 3.x, yt-dlp (+ gallery-dl fallback), SQLAlchemy 2 async
(SQLite via aiosqlite by default), ffmpeg/ffprobe, optional aria2c (VK).
The bot talks to a **local Telegram Bot API server** at `http://127.0.0.1:8081`
(needed for uploads up to 2 GB).

## Server

SaveX runs at `/opt/bots/SaveX` on a **shared server** that also hosts other bots,
websites and apps. Everything SaveX does on the server must stay inside its own scope:

- Directory `/opt/bots/SaveX`; systemd unit `savex-bot`; docker compose project name `savex`
  (all containers, networks and volumes prefixed `savex-`).
- `deploy.sh` only `cd`s into its own dir and only manages the `savex-*` unit / `savex`
  compose project. Never add global commands to it: no `docker system prune`, no
  `systemctl restart docker`, no killing processes by name, no system-wide `pip install`.
- **Later phases (Postgres/Redis):** the containers must be named `savex-postgres` and
  `savex-redis`, must publish **no public ports** (reachable only on the internal `savex`
  compose network; if host access is ever needed, bind to `127.0.0.1` only), and must not
  clash with other projects (unique container, network and volume names prefixed `savex-`,
  unique compose project name, no reuse of another project's database/Redis).
- The local Bot API server port `8081` is hard-coded in `bot.py`; check it is free of other
  projects before changing anything around it.

## How the bot starts

`python bot.py`:
0. `config.ensure_runtime_dirs()` creates `storage/`, `storage/temp/` and the SQLite DB folder;
   `config.cleanup_stale_temp()` removes temp leftovers older than 1 hour.
1. `Base.metadata.create_all` creates missing tables (no migrations yet — new columns
   on existing tables are NOT added automatically).
2. Creates `Bot` with an `AiohttpSession` pointed at the local Bot API server.
3. `Dispatcher` includes `app.handlers.setup_routers()`.
4. Starts `app.services.scheduler.run_scheduler` (premium expiry warnings, every 30 min).
5. Long polling.

Helper scripts: `init_db.py` (create tables only), `create_session.py` (Pyrogram user
session, currently unused by the bot).

## Folder structure

```
bot.py                     entry point
config.py                  env loading (BOT_TOKEN, ADMIN_IDS, DATABASE_URL), runtime dirs
locales/                   uz.json, ru.json, en.json (so far: download errors, history lists)
app/
  database/
    models.py              User, Order, DownloadHistory, Favorite, MandatoryChannel,
                           ChannelJoinRecord, PriceSetting, MediaCache
    crud.py                all DB access helpers, limits, prices, stats
    session.py             async engine + async_session factory
  handlers/
    __init__.py            router order: admin → start → gate → download → menu →
                           premium → library → favorites → feedback
    admin/                 panel.py (/admin, stats, search, ban, grant, broadcast),
                           channels.py (mandatory channels), prices.py, orders.py
    user/                  start.py (registration FSM), gate.py (channel check),
                           download.py (all download logic — the live code path),
                           menu.py (cabinet, help), premium.py (tariffs, receipts),
                           favorites.py, feedback.py (user ↔ admin relay),
                           library.py (unreachable, see PROGRESS.md)
  keyboards/               inline.py, reply.py, channels.py (+ unused language.py,
                           phone.py, region.py, quality.py)
  services/
    channels.py            mandatory-channel membership check
    i18n.py                t(key, lang, **kw) + get_user_lang (reads locales/*.json)
    scheduler.py           premium expiry loop
    downloader/            errors.py (yt-dlp error → locale key) and gallerydl.py are used; router/common/generic/instagram/* are
                           NOT wired in yet (download.py has its own copies);
                           several files are empty placeholders
storage/                   runtime data (gitignored): savex.db, temp/, cookies.txt
```

## Environment variables (names only — never commit values)

| Name | Used in | Notes |
|---|---|---|
| `BOT_TOKEN` | config.py | required |
| `ADMIN_IDS` | config.py | comma-separated Telegram IDs |
| `DATABASE_URL` | config.py | default `sqlite+aiosqlite:///./storage/savex.db` |
| `API_ID`, `API_HASH` | create_session.py | only for the Pyrogram helper; also needed by the local `telegram-bot-api` server |

Files with secrets (gitignored): `.env`, `storage/cookies.txt`, `cookies/`, `*.session`.

## RULES

- Never remove or rename existing features, commands, handlers, callback_data, DB
  columns or admin functions. Only fix and extend.
- Read only the files needed for the current phase. Do not re-read the whole repo.
- All user-facing text goes through `locales/{uz,ru,en}.json` (`app.services.i18n.t`). All
  keyboards live in one keyboards module. *(Target state — `locales/` exists since Phase 1a
  and holds the download errors and the "Videolarim"/"Musiqalarim" lists; the remaining
  hard-coded Uzbek text moves over gradually and is completed in Phase 6. New text must go
  into the locales from now on.)*
- Every `parse_mode="HTML"` message must `html.escape` all user-provided text (names, titles,
  message text). Prices are never read from `callback_data`; read them from the DB.
- Download jobs use a private temp dir (`_new_job_dir()`) and delete it in `finally`.
- Every downloaded/temp file must be deleted after sending or on error (try/finally).
- Never log or commit secrets. `cookies/` and `.env` are gitignored.
- Don't ask questions unless truly blocked; make sensible decisions and record them in
  PROGRESS.md.
- At the end of each phase: update PROGRESS.md and roadmap status, commit with a clear
  message.

## ROADMAP

| # | Phase | Status |
|---|---|---|
| 0 | Audit: CLAUDE.md, PROGRESS.md, deploy.sh, DEPLOY.md | ✅ Done |
| 1 | Bugs + UI (fix PROGRESS.md bug list, unify keyboards, start locales) | 🔄 1a ✅ HIGH/CRITICAL bugs · 1b ⏳ Medium/Low bugs + UI |
| 2 | PostgreSQL + unified ID (Alembic migrations, one user key across tables) | ⬜ Todo |
| 3 | Speed + parallel + cache (per-job temp dirs, timeouts, worker pool, file_id cache everywhere) | ⬜ Todo |
| 4 | Platforms (wire `services/downloader/router.py`, per-platform modules) | ⬜ Todo |
| 5 | Music (search/recognition, audio-first flows) | ⬜ Todo |
| 6 | Tariffs + i18n + extras (uz/ru/en locales, tariff logic, referrals) | ⬜ Todo |

See PROGRESS.md for the bug list and decisions. Deployment: DEPLOY.md / `deploy.sh`.
