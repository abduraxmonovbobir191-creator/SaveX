# SaveX — @SaveXStorageBot

Telegram bot that downloads media (video, photo, gallery, audio/MP3) from social
networks by link. Has a free daily limit, paid PLUS/PRO tariffs (manual card payment
approved by admins), mandatory-channel gate, favorites, download history and an
admin panel.

Stack: Python 3.10+, aiogram 3.x, yt-dlp (+ gallery-dl fallback), SQLAlchemy 2 async
(SQLite via aiosqlite by default), ffmpeg/ffprobe, optional aria2c (VK).
The bot talks to a **local Telegram Bot API server** at `http://127.0.0.1:8081`
(needed for uploads up to 2 GB).

## How the bot starts

`python bot.py`:
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
config.py                  env loading (BOT_TOKEN, ADMIN_IDS, DATABASE_URL)
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
    scheduler.py           premium expiry loop
    downloader/            gallerydl.py is used; router/common/generic/instagram/* are
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
- All user-facing text goes through `locales/{uz,ru,en}.json`. All keyboards live in
  one keyboards module. *(Target state — locales/ does not exist yet; introduced in
  Phase 1 and completed in Phase 6.)*
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
| 1 | Bugs + UI (fix PROGRESS.md bug list, unify keyboards, start locales) | ⏳ Next |
| 2 | PostgreSQL + unified ID (Alembic migrations, one user key across tables) | ⬜ Todo |
| 3 | Speed + parallel + cache (per-job temp dirs, timeouts, worker pool, file_id cache everywhere) | ⬜ Todo |
| 4 | Platforms (wire `services/downloader/router.py`, per-platform modules) | ⬜ Todo |
| 5 | Music (search/recognition, audio-first flows) | ⬜ Todo |
| 6 | Tariffs + i18n + extras (uz/ru/en locales, tariff logic, referrals) | ⬜ Todo |

See PROGRESS.md for the bug list and decisions. Deployment: DEPLOY.md / `deploy.sh`.
