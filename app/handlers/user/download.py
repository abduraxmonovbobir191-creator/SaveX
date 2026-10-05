import asyncio
import html
import inspect
import json
import logging
import os
import shutil
import subprocess
import urllib.request
import uuid
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from aiogram import Router, F, Bot
from aiogram.types import Message, FSInputFile, CallbackQuery, InputMediaPhoto, InputMediaVideo
import yt_dlp
from app.database.session import async_session
from app.database import crud
from app.keyboards.inline import quality_kb, mp3_kb
from app.keyboards.channels import channels_gate_kb
from app.services.channels import get_missing_channels
from app.handlers.user.favorites import register_favorite_item, favorite_button
from app.services.downloader.router import detect_platform, get_downloader
from app.services.downloader.errors import TooLargeError, classify_error
from app.services.i18n import t, get_user_lang
from config import TEMP_DIR

router = Router()
log = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 1950 * 1024 * 1024
SHORT_VIDEO_SECONDS = 180
MAX_GALLERY_ITEMS = 10
PHOTO_EXT = (".jpg", ".jpeg", ".png", ".webp")
EXECUTOR = ThreadPoolExecutor(max_workers=8)
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(5)
PENDING = {}
COOKIES_PATH = "storage/cookies.txt"

NO_VIDEO_SIGNALS = ["no video", "no video formats", "requested format is not available"]


def _is_playlist_url(url: str) -> bool:
    """Only an explicit YouTube playlist link counts as a playlist request.
    `watch?v=...&list=...` is a single video."""
    p = urlparse(url)
    host = p.netloc.lower()
    return "youtube.com" in host and p.path.rstrip("/") == "/playlist"


def _new_job_dir() -> str:
    """Private temp folder per job, so concurrent jobs never share/delete each other's files."""
    path = os.path.join(TEMP_DIR, uuid.uuid4().hex)
    os.makedirs(path, exist_ok=True)
    return path


def _cleanup(path: str):
    shutil.rmtree(path, ignore_errors=True)


def _base_opts(playlist: bool = False):
    opts = {"quiet": True, "no_warnings": True, "noplaylist": not playlist,
            "socket_timeout": 25, "retries": 2, "playlistend": MAX_GALLERY_ITEMS}
    if os.path.exists(COOKIES_PATH):
        opts["cookiefile"] = COOKIES_PATH
    opts["max_filesize"] = MAX_UPLOAD_BYTES
    return opts


def _extract_info_sync(url: str, playlist: bool = False):
    opts = _base_opts(playlist)
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def _estimate_size(info: dict, height=None, audio_only=False):
    """Yuklashdan oldin fayl hajmini taxmin qiladi."""
    if audio_only:
        candidates = [
            f for f in info.get("formats", [])
            if f.get("acodec") != "none"
        ]
        if not candidates:
            return info.get("filesize") or info.get("filesize_approx")
        candidates.sort(
            key=lambda f: (
                f.get("abr") or 0,
                f.get("filesize") or f.get("filesize_approx") or 0
            ),
            reverse=True
        )
        f = candidates[0]
        return f.get("filesize") or f.get("filesize_approx")

    formats = info.get("formats", [])
    if not formats:
        return info.get("filesize") or info.get("filesize_approx")

    if height:
        video = [
            f for f in formats
            if f.get("vcodec") != "none"
            and (f.get("height") or 0) <= height
        ]
    else:
        video = [
            f for f in formats
            if f.get("vcodec") != "none"
            and (f.get("height") or 0) <= 1080
        ]

    audio = [
        f for f in formats
        if f.get("acodec") != "none"
        and f.get("vcodec") == "none"
    ]

    video.sort(
        key=lambda f: (
            f.get("height") or 0,
            f.get("fps") or 0,
            f.get("filesize") or f.get("filesize_approx") or 0
        ),
        reverse=True
    )
    audio.sort(
        key=lambda f: (
            f.get("abr") or 0,
            f.get("filesize") or f.get("filesize_approx") or 0
        ),
        reverse=True
    )

    if video and audio:
        vs = video[0].get("filesize") or video[0].get("filesize_approx")
        aus = audio[0].get("filesize") or audio[0].get("filesize_approx")
        if vs is not None and aus is not None:
            return vs + aus

    if video:
        return video[0].get("filesize") or video[0].get("filesize_approx")

    return info.get("filesize") or info.get("filesize_approx")


def _run_download(opts: dict, url: str):
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            raise yt_dlp.utils.DownloadError("no video formats: requested format is not available")
        filename = ydl.prepare_filename(info)
        if info.get("requested_downloads"):
            real = info["requested_downloads"][0].get("filepath")
            if real and os.path.exists(real):
                filename = real
        return info, filename


def _ensure_file(info: dict, filename: str):
    """yt-dlp silently skips files over max_filesize, so a missing file means 'too large'."""
    if not os.path.exists(filename):
        raise TooLargeError(filename)
    return info, filename


def _download_sync(url: str, height, audio_only: bool, output: str):
    """Video/rasmni yuklaydi. Agar 'video' deb hisoblangan post aslida rasm bo'lsa,
    avtomatik oddiy 'best' formatga o'tib, baribir yuklab beradi."""
    opts = _base_opts()
    opts["outtmpl"] = output
    opts["postprocessor_args"] = {"merger": ["-movflags", "+faststart"]}
    if "vk.com" in url or "vkvideo.ru" in url:
        opts["external_downloader"] = {"http": "aria2c"}
        opts["external_downloader_args"] = {"aria2c": ["-x16", "-s16", "-k1M", "--file-allocation=none"]}

    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
        info, filename = _run_download(opts, url)
        base = os.path.splitext(filename)[0]
        filename = base + ".mp3"
        return _ensure_file(info, filename)

    
    opts["merge_output_format"] = "mp4"
    if height:
        opts["format"] = (f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                           f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/bv*+ba/b")
    else:
        opts["format"] = ("bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
                           "bestvideo[height<=1080]+bestaudio/best[height<=1080]/bv*+ba/b")

    try:
        return _ensure_file(*_run_download(opts, url))
    except yt_dlp.utils.DownloadError as e:
        msg = str(e).lower()
        if not any(s in msg for s in NO_VIDEO_SIGNALS):
            raise
        # Bu aslida rasm ekan — oddiy 'best' bilan qayta urinamiz
        opts2 = _base_opts()
        opts2["outtmpl"] = output
        opts2["format"] = "bv*+ba/b"
        opts2["merge_output_format"] = "mp4"
        return _ensure_file(*_run_download(opts2, url))


def _download_gallery_sync(url: str, job_dir: str, playlist: bool = False):
    opts = _base_opts(playlist)
    opts["outtmpl"] = os.path.join(job_dir, "%(playlist_index)s_%(id)s.%(ext)s")
    opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        entries = info.get("entries") or [info]
        files = []
        for entry in entries:
            if not entry:
                continue
            fn = ydl.prepare_filename(entry)
            if entry.get("requested_downloads"):
                real = entry["requested_downloads"][0].get("filepath")
                if real and os.path.exists(real):
                    fn = real
            if os.path.exists(fn):
                files.append(fn)
        return files


def _probe_size(f):
    size = f.get("filesize") or f.get("filesize_approx")
    if size:
        return size
    url = f.get("url")
    if not url or not str(f.get("protocol", "")).startswith("http"):
        return None
    headers = dict(f.get("http_headers") or {})
    headers["Range"] = "bytes=0-0"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            total = r.headers.get("Content-Range", "").rsplit("/", 1)[-1]
            if total.isdigit():
                return int(total)
            cl = r.headers.get("Content-Length") or ""
            return int(cl) if cl.isdigit() and int(cl) > 1024 else None
    except Exception:
        return None


def _fit_height(url: str, height: int) -> int:
    """Highest height <= requested whose video+audio fits MAX_UPLOAD_BYTES."""
    formats = (_extract_info_sync(url) or {}).get("formats") or []
    audio = [f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"]
    audio.sort(key=lambda f: f.get("abr") or 0, reverse=True)
    audio_size = (_probe_size(audio[0]) or 0) if audio else 0
    heights = sorted({f["height"] for f in formats
                      if f.get("vcodec") != "none" and f.get("height") and f["height"] <= height}, reverse=True)
    for h in heights:
        sizes = [x for x in (_probe_size(f) for f in formats
                             if f.get("vcodec") != "none" and f.get("height") == h) if x]
        if not sizes or max(sizes) + audio_size <= MAX_UPLOAD_BYTES:
            return h
    return heights[-1] if heights else height


_THUMB_OK = "thumbnail" in inspect.signature(Message.answer_video).parameters


def _video_meta(filename: str) -> dict:
    """duration/width/height (+thumbnail) for answer_video."""
    meta = {}
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height:format=duration", "-of", "json", filename],
            capture_output=True, timeout=20).stdout
        d = json.loads(out or b"{}")
        st = (d.get("streams") or [{}])[0]
        if st.get("width") and st.get("height"):
            meta["width"], meta["height"] = int(st["width"]), int(st["height"])
        dur = (d.get("format") or {}).get("duration")
        if dur:
            meta["duration"] = int(float(dur))
        if _THUMB_OK:
            thumb = filename + ".thumb.jpg"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", filename, "-frames:v", "1",
                 "-vf", "scale=320:320:force_original_aspect_ratio=decrease", "-q:v", "5", thumb],
                capture_output=True, timeout=30)
            if os.path.exists(thumb) and os.path.getsize(thumb) < 200 * 1024:
                meta["thumbnail"] = FSInputFile(thumb)
    except Exception as e:
        log.warning("[video meta] %r", e)
    return meta


async def _send_cached(target, cache_key, variant, url, user_id):
    """Resend a previously uploaded file by file_id. Returns media_type or None."""
    try:
        async with async_session() as session:
            row = await crud.get_cached_media(session, cache_key, variant)
        if not row:
            return None
        title = row.title or "Media"
        if row.media_type == "photo":
            sent = await target.answer_photo(row.file_id, caption=f"✅ {title}")
        elif row.media_type == "audio":
            sent = await target.answer_audio(row.file_id, caption=f"✅ {title}")
        else:
            sent = await target.answer_video(row.file_id, caption=f"✅ {title}", supports_streaming=True)
        try:
            fav_token = register_favorite_item(row.file_id, row.media_type, title)
            await sent.edit_reply_markup(reply_markup=favorite_button(fav_token))
        except Exception:
            pass
        async with async_session() as session:
            await crud.add_to_history(session, user_id, url, title, row.media_type)
        return row.media_type
    except Exception as e:
        log.warning("[cache send] %r", e)
        return None


async def get_loop_run(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(EXECUTOR, func, *args)


async def _send_downloaded(target, filename, title, cache=None, lang="uz"):
    """Fayl kengaytmasiga qarab rasm yoki video sifatida yuboradi, hajmni tekshiradi,
    sevimlilar tugmasini qo'shadi. Yuborilgan media turini qaytaradi.
    Faylni o'chirish chaqiruvchining (job papkasi) vazifasi."""
    ext = os.path.splitext(filename)[1].lower()
    size = os.path.getsize(filename)

    if size > MAX_UPLOAD_BYTES:
        await target.answer(t("err_too_large", lang))
        return None

    file = FSInputFile(filename)
    if ext in PHOTO_EXT:
        sent = await target.answer_photo(file, caption=f"✅ {title}")
        media_type = "photo"
        fid = sent.photo[-1].file_id
    else:
        sent = await target.answer_video(file, caption=f"✅ {title}", supports_streaming=True, **(await get_loop_run(_video_meta, filename)))
        media_type = "video"
        fid = sent.video.file_id

    if cache:
        try:
            async with async_session() as session:
                await crud.save_cached_media(session, cache[0], cache[1], fid, media_type, title)
        except Exception as e:
            log.warning("[cache save] %r", e)
    try:
        fav_token = register_favorite_item(fid, media_type, title)
        await sent.edit_reply_markup(reply_markup=favorite_button(fav_token))
    except Exception:
        pass

    return media_type


async def _send_group(message: Message, files: list[str]) -> bool:
    """Rasm/video fayllarni (10 tagacha) albom yoki bitta media sifatida yuboradi."""
    group = []
    for f in files[:MAX_GALLERY_ITEMS]:
        if os.path.getsize(f) > MAX_UPLOAD_BYTES:
            continue
        if os.path.splitext(f)[1].lower() in PHOTO_EXT:
            group.append(InputMediaPhoto(media=FSInputFile(f)))
        else:
            group.append(InputMediaVideo(media=FSInputFile(f)))
    if not group:
        return False

    if len(group) == 1:
        m = group[0]
        if isinstance(m, InputMediaPhoto):
            await message.answer_photo(m.media)
        else:
            await message.answer_video(m.media)
    else:
        await message.answer_media_group(group)
    return True


@router.message(F.text.contains("wikipedia.org"))
async def handle_wikipedia(message: Message):
    import re, urllib.request, urllib.parse, json

    match = re.search(r"wikipedia\.org/wiki/([^\s?#]+)", message.text)
    if not match:
        await message.answer("❌ Wikipedia havolasi tushunarsiz")
        return

    title = urllib.parse.unquote(match.group(1))
    lang_match = re.search(r"https?://([a-z]+)\.wikipedia\.org", message.text)
    lang = lang_match.group(1) if lang_match else "en"

    status = await message.answer("⏳ Maqola yuklanmoqda...")
    api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"

    try:
        def fetch():
            req = urllib.request.Request(api_url, headers={"User-Agent": "SaveXBot/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())

        data = await get_loop_run(fetch)
        extract = data.get("extract", "Matn topilmadi")
        page_title = data.get("title", title)
        image_url = data.get("thumbnail", {}).get("source")

        caption = f"📖 <b>{html.escape(page_title)}</b>\n\n{html.escape(extract[:900])}"
        if image_url:
            await message.answer_photo(image_url, caption=caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")
        await status.delete()
    except Exception:
        await status.edit_text("❌ Maqola topilmadi yoki yuklab bo'lmadi")


async def _try_gallerydl(message, status, url) -> bool:
    # yt-dlp topa olmagan rasm/galereya havolalarini gallery-dl bilan urinib ko'radi
    from app.services.downloader.gallerydl import download_sync as gallerydl_sync

    job_dir = _new_job_dir()
    try:
        await status.edit_text("⏳ Rasm/galereya yuklanmoqda...")
        async with DOWNLOAD_SEMAPHORE:
            files = await get_loop_run(gallerydl_sync, url, message.chat.id, job_dir)
        if not files:
            return False

        if not await _send_group(message, files):
            return False

        async with async_session() as session:
            await crud.add_to_history(session, message.from_user.id, url, "Galereya", "gallery")
        await status.delete()
        return True
    except Exception as e:
        log.warning("[gallerydl] %r", e)
        return False
    finally:
        _cleanup(job_dir)


@router.message(F.text.startswith("http"))
async def handle_link(message: Message, bot: Bot):
    url = message.text.strip()

    async with async_session() as session:
        user = await crud.get_or_create_user(session, message.from_user.id, message.from_user.username,
                                              message.from_user.first_name, message.from_user.last_name)
        if user.is_banned:
            return
        lang = user.language

    missing = await get_missing_channels(bot, message.from_user.id)
    if missing:
        await message.answer(
            "📡 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n\n"
            "💎 Yoki Premium xarid qilib, kanallarsiz foydalaning!",
            reply_markup=channels_gate_kb(missing)
        )
        return

    async with async_session() as session:
        user = await crud.get_user(session, message.from_user.id)
        allowed, used, limit = await crud.check_and_use_limit(session, user)

    if not allowed:
        await message.answer(f"🚫 Kunlik limitingiz tugadi ({limit} ta).\n\n💎 Premium xarid qilib, limitni oshiring.")
        return

    status = await message.answer("🔍 Havola tekshirilmoqda...")
    playlist = _is_playlist_url(url)

    try:
        async with DOWNLOAD_SEMAPHORE:
            info = await get_loop_run(_extract_info_sync, url, playlist)
    except Exception as e:
        err_key = classify_error(e)
        log.info("[extract] %s: %r", err_key, e)
        # Login/private xatolarida gallery-dl ham yordam bermaydi (bir xil cookies)
        if err_key not in ("err_login", "err_private"):
            if await _try_gallerydl(message, status, url):
                return
        await status.edit_text(t(err_key, lang))
        return

    if not info:
        if await _try_gallerydl(message, status, url):
            return
        await status.edit_text(t("err_no_media", lang))
        return

    is_gallery = info.get("_type") == "playlist" or (info.get("entries") and len(info.get("entries", [])) > 1)
    if is_gallery:
        await status.edit_text("⏳ Galereya yuklanmoqda...")
        job_dir = _new_job_dir()
        try:
            try:
                async with DOWNLOAD_SEMAPHORE:
                    files = await get_loop_run(_download_gallery_sync, url, job_dir, playlist)
            except Exception as e:
                err_key = classify_error(e)
                log.info("[gallery] %s: %r", err_key, e)
                if err_key not in ("err_login", "err_private") and await _try_gallerydl(message, status, url):
                    return
                await status.edit_text(t(err_key, lang))
                return

            if not files:
                if await _try_gallerydl(message, status, url):
                    return
                await status.edit_text(t("err_no_media", lang))
                return

            try:
                sent = await _send_group(message, files)
            except Exception as e:
                log.warning("[gallery send] %r", e)
                await status.edit_text(t("err_generic", lang))
                return
            if not sent:
                await status.edit_text(t("err_too_large", lang))
                return
            async with async_session() as session:
                await crud.add_to_history(session, message.from_user.id, url,
                                           info.get("title") or "Galereya", "gallery")
            await status.delete()
        finally:
            _cleanup(job_dir)
        return

    duration = info.get("duration") or 0
    ckey = (info.get("extractor_key") or "") + ":" + str(info.get("id")) if info.get("id") else None

    # Uzun video (>3 daqiqa) — sifat tanlash tugmalari
    if duration > SHORT_VIDEO_SECONDS:
        heights = set()
        for f in info.get("formats", []):
            h = f.get("height")
            if h:
                for target in (240, 360, 480, 720, 1080):
                    if h >= target:
                        heights.add(target)
        if not heights:
            heights = {360, 480}

        token = uuid.uuid4().hex[:10]
        PENDING[token] = {"url": url, "chat_id": message.chat.id, "user_id": message.from_user.id, "ckey": ckey}

        await status.edit_text(
            f"🎬 <b>{html.escape((info.get('title') or 'Video')[:60])}</b>\n\n⬇️ Sifatni tanlang:",
            parse_mode="HTML",
            reply_markup=quality_kb(token, sorted(heights))
        )
        return

    # Qisqa video YOKI rasm — avtomatik yuklab, turini aniqlab yuboradi
    if ckey:
        hit = await _send_cached(message, ckey, "auto", url, message.from_user.id)
        if hit:
            await status.delete()
            if hit == "video":
                mp3_token = uuid.uuid4().hex[:10]
                PENDING[mp3_token] = {"url": url, "chat_id": message.chat.id, "user_id": message.from_user.id, "ckey": ckey}
                await message.answer("🎵 Audio kerakmi?", reply_markup=mp3_kb(mp3_token))
            return
    await status.edit_text("⏳ Yuklab olinmoqda...")
    job_dir = _new_job_dir()
    try:
        async with DOWNLOAD_SEMAPHORE:
            info2, filename = await get_loop_run(
                _download_sync, url, None, False, os.path.join(job_dir, "%(id)s.%(ext)s"))
        title = (info2.get("title") or "Media")[:50]
        media_type = await _send_downloaded(message, filename, title, cache=(ckey, "auto") if ckey else None, lang=lang)
        if media_type:
            async with async_session() as session:
                await crud.add_to_history(session, message.from_user.id, url, title, media_type)
        await status.delete()
        if filename.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
            try:
                mp3_token = uuid.uuid4().hex[:10]
                PENDING[mp3_token] = {"url": url, "chat_id": message.chat.id, "user_id": message.from_user.id, "ckey": ckey}
                await message.answer("🎵 Audio kerakmi?", reply_markup=mp3_kb(mp3_token))
            except Exception as e:
                log.warning("[mp3 btn] %r", e)
    except Exception as e:
        err_key = classify_error(e)
        log.warning("[download] %s: %r", err_key, e, exc_info=err_key == "err_generic")
        try:
            await status.edit_text(t(err_key, lang))
        except Exception:
            pass
    finally:
        _cleanup(job_dir)


@router.callback_query(F.data.startswith("dl:"))
async def handle_quality_choice(callback: CallbackQuery):
    _, token, choice = callback.data.split(":")
    data = PENDING.get(token)
    if not data:
        await callback.answer("Bu so'rov eskirgan, qaytadan link yuboring", show_alert=True)
        return

    lang = await get_user_lang(callback.from_user.id)
    url = data["url"]
    if data.get("ckey"):
        hit = await _send_cached(callback.message, data["ckey"], choice, url, data["user_id"])
        if hit:
            PENDING.pop(token, None)
            await callback.answer()
            try:
                await callback.message.delete()
            except Exception:
                pass
            return
    await callback.message.edit_text("⏳ Yuklab olinmoqda...")
    await callback.answer()

    audio_only = choice == "audio"
    height = None if audio_only else int(choice)
    if height:
        try:
            fit = await get_loop_run(_fit_height, url, height)
            if fit and fit < height:
                await callback.message.edit_text(f"⏳ {height}p 2 GB dan katta, {fit}p yuklanmoqda...")
                height = fit
        except Exception:
            pass

    job_dir = _new_job_dir()
    output = os.path.join(job_dir, "%(id)s.%(ext)s")
    try:
        try:
            async with DOWNLOAD_SEMAPHORE:
                info, filename = await get_loop_run(_download_sync, url, height, audio_only, output)
        except Exception as e:
            err_key = classify_error(e)
            log.warning("[download] %s: %r", err_key, e, exc_info=err_key == "err_generic")
            await callback.message.edit_text(t("err_generic_quality" if err_key == "err_generic" else err_key, lang))
            return

        title = (info.get("title") or "Media")[:50]

        if audio_only:
            if os.path.getsize(filename) > MAX_UPLOAD_BYTES:
                await callback.message.edit_text(t("err_too_large", lang))
                return
            try:
                sent = await callback.message.answer_audio(FSInputFile(filename, filename=f"{title}.mp3"), title=title, performer=info.get("uploader") or "SaveX", caption=f"✅ {title}")
                if data.get("ckey"):
                    try:
                        async with async_session() as session:
                            await crud.save_cached_media(session, data["ckey"], "audio", sent.audio.file_id, "audio", title)
                    except Exception as e:
                        log.warning("[cache save] %r", e)
                try:
                    fav_token = register_favorite_item(sent.audio.file_id, "audio", title)
                    await sent.edit_reply_markup(reply_markup=favorite_button(fav_token))
                except Exception:
                    pass
                async with async_session() as session:
                    await crud.add_to_history(session, data["user_id"], url, title, "audio")
                await callback.message.delete()
            except Exception:
                await callback.message.edit_text("❌ Yuborishda xatolik yuz berdi")
            return

        media_type = await _send_downloaded(callback.message, filename, title, cache=(data["ckey"], choice) if data.get("ckey") else None, lang=lang)
        if media_type:
            async with async_session() as session:
                await crud.add_to_history(session, data["user_id"], url, title, media_type)
            try:
                await callback.message.delete()
            except Exception:
                pass
    finally:
        _cleanup(job_dir)
        PENDING.pop(token, None)
