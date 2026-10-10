# SaveX — Serverga joylash (Deploy)

Barcha buyruqlar serverda, loyiha papkasida bajariladi: **`/opt/bots/SaveX`**.

> ⚠️ Bu serverda boshqa botlar, saytlar va ilovalar ham ishlaydi. SaveX faqat o'z papkasi
> (`/opt/bots/SaveX`), o'z systemd servisi (`savex-bot`) va o'z docker compose loyihasi
> (`savex`) bilan ishlaydi. Hech qachon global buyruq ishlatmang: `docker system prune`,
> `systemctl restart docker`, `pkill python`, tizim bo'yicha `pip install` va hokazo.

## 1. Birinchi marta o'rnatish

```bash
# Tizim paketlari
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg aria2

# Kodni yuklab olish
sudo mkdir -p /opt/bots
cd /opt/bots
sudo git clone https://github.com/abduraxmonovbobir191-creator/SaveX.git
sudo chown -R $USER:$USER /opt/bots/SaveX
cd /opt/bots/SaveX

# Virtual muhit va kutubxonalar (faqat shu papkadagi venv ga; tizim Python'iga tegmang)
python3 -m venv venv
venv/bin/pip install -r requirements.txt     # gallery-dl ham shu yerda

# Sozlamalar
cp .env.example .env
nano .env                       # BOT_TOKEN, ADMIN_IDS, DATABASE_URL ni kiriting
# storage/ va storage/temp bot ishga tushganda o'zi yaratiladi
# Instagram/YouTube va boshqalar uchun cookies: 7-bo'limga qarang (cookies/instagram.txt)

chmod +x deploy.sh
```

### Lokal Telegram Bot API server

Bot `http://127.0.0.1:8081` dagi lokal Bot API serverga ulanadi (2 GB gacha fayl
yuborish uchun). U alohida ishga tushirilgan bo'lishi kerak. Port `8081` kodda qattiq
yozilgan, shuning uchun boshlashdan oldin u band emasligini tekshiring (boshqa loyiha
ishlatayotgan bo'lishi mumkin):

```bash
ss -ltnp | grep ':8081' || echo "8081 bo'sh"
```

```bash
telegram-bot-api --local --api-id=<API_ID> --api-hash=<API_HASH> --http-port=8081
```

(`API_ID` va `API_HASH` ni https://my.telegram.org dan olasiz. Ularni hech qayerga
commit qilmang.)

### systemd servisi `savex-bot`

Servis nomi boshqa loyihalar bilan to'qnashmasligi uchun `savex-bot`. (Agar oldin `savex`
nomli servis bo'lgan bo'lsa: `sudo systemctl disable --now savex`, so'ng uning unit faylini
o'chiring.) `/etc/systemd/system/savex-bot.service` faylini yarating:

```ini
[Unit]
Description=SaveX Telegram bot (@SaveXStorageBot)
After=network-online.target

[Service]
Type=simple
User=<server_foydalanuvchisi>
WorkingDirectory=/opt/bots/SaveX
ExecStart=/opt/bots/SaveX/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now savex-bot
```

## 2. Yangilash (har safar)

```bash
cd /opt/bots/SaveX
./deploy.sh
```

`deploy.sh` faqat SaveX'ga tegadi va quyidagilarni bajaradi:
1. O'zi turgan papkaga (`/opt/bots/SaveX`) `cd` qiladi va bu SaveX git papkasi ekanini tekshiradi.
2. Hozirgi commitni `.deploy_prev_commit` ga saqlaydi (orqaga qaytish uchun).
3. `ig.json` (git'da endi yo'q, lokal fayl) ni `storage/ig.json` ga ko'chiradi va eski joyda
   symlink qoldiradi, shunda `git pull` uni o'chirib yubormaydi.
4. `git fetch` + `git merge --ff-only` (yangilanish `cookies/` ichida fayl bo'lgan versiya bo'lsa,
   rad etiladi; `cookies/` ga deploy hech qachon tegmaydi, 6-bo'limga qarang).
5. Kutubxonalarni **faqat** `/opt/bots/SaveX/venv` ga o'rnatadi (`venv` bo'lmasa yaratadi).
6. `alembic.ini` bo'lsa, `alembic upgrade head` bilan migratsiyalarni bajaradi.
7. `docker-compose.yml` bo'lsa, `docker compose -p savex up -d` (loyiha nomi `savex`,
   konteynerlar `savex-*`); aks holda `sudo systemctl restart savex-bot`.

Servis nomini `SAVEX_SERVICE=...` bilan o'zgartirish mumkin, lekin u `savex` bilan
boshlanishi shart.

## 3. Loglarni ko'rish

```bash
# Jonli loglar
sudo journalctl -u savex-bot -f

# Oxirgi 200 qator
sudo journalctl -u savex-bot -n 200 --no-pager

# Bugungi xatolar
sudo journalctl -u savex-bot --since today -p err --no-pager

# Servis holati
sudo systemctl status savex-bot
```

Docker ishlatilsa (loyiha nomi doim `savex`):

```bash
docker compose -p savex logs -f --tail=200
```

## 4. Orqaga qaytish (Rollback)

Oxirgi deploydan oldingi versiyaga qaytish:

```bash
cd /opt/bots/SaveX
./deploy.sh rollback
```

Ma'lum bir commitga qaytish:

```bash
cd /opt/bots/SaveX
git log --oneline -n 20          # kerakli commitni toping
git reset --hard <commit_hash>
sudo systemctl restart savex-bot
```

Keyin yana eng so'nggi versiyaga o'tish uchun `./deploy.sh` ni ishga tushiring.

> ⚠️ Rollback ma'lumotlar bazasini qaytarmaydi. Migratsiyalar paydo bo'lgach (Phase 2),
> deploydan oldin bazadan nusxa oling:
> `cp storage/savex.db storage/savex.db.$(date +%F_%H%M).bak`

## 5. Foydali buyruqlar

```bash
sudo systemctl stop savex-bot        # to'xtatish
sudo systemctl start savex-bot       # ishga tushirish
sudo systemctl restart savex-bot     # qayta ishga tushirish
du -sh storage/temp              # vaqtinchalik fayllar hajmi
rm -rf storage/temp/*            # vaqtinchalik fayllarni tozalash (bot to'xtatilganda)
```

## 6. Cookies (Instagram va boshqa platformalar uchun login)

Instagram rasm/karusel postlari va ko'p YouTube videolari akkauntga kirmasdan ochilmaydi.
Serverda logda `There is no video in this post` va keyin gallery-dl'dan
`HTTP redirect to login page` ko'rinsa, sabab shu: cookies yo'q yoki eskirgan.

### Qaysi fayl ishlatiladi

yt-dlp ham, gallery-dl ham bir xil faylni ishlatadi:

| Platforma | Fayl (default) | Env orqali o'zgartirish |
|---|---|---|
| Instagram | `/opt/bots/SaveX/cookies/instagram.txt` | `INSTAGRAM_COOKIES=/boshqa/yo'l.txt` |
| YouTube | `/opt/bots/SaveX/cookies/youtube.txt` | `YOUTUBE_COOKIES` |
| TikTok | `/opt/bots/SaveX/cookies/tiktok.txt` | `TIKTOK_COOKIES` |
| Twitter/X | `/opt/bots/SaveX/cookies/twitter.txt` | `TWITTER_COOKIES` |
| Pinterest | `/opt/bots/SaveX/cookies/pinterest.txt` | `PINTEREST_COOKIES` |

Platforma fayli bo'lmasa, eski umumiy `storage/cookies.txt` ishlatiladi (bor bo'lsa).
Env o'zgaruvchilari `.env` fayliga yoziladi (`.env.example` ga qarang).

### Qanday qo'shish (birinchi marta)

1. **Alohida (qo'shimcha) Instagram akkaunt** oching. O'zingizning asosiy akkauntingizni
   ishlatmang: bot kirishi uchun akkaunt bloklanishi mumkin.
2. Kompyuteringizdagi brauzerda shu akkauntga kiring (login qilib turing).
3. Brauzer kengaytmasi (masalan "Get cookies.txt LOCALLY") bilan `instagram.com` uchun
   cookies ni **Netscape formatida** eksport qiling. Fayl birinchi qatori
   `# Netscape HTTP Cookie File` bo'lishi shart.
4. Faylni serverga yuklang (kompyuteringizdan):
   ```bash
   scp instagram.txt <foydalanuvchi>@<server>:/opt/bots/SaveX/cookies/instagram.txt
   ```
5. Serverda ruxsatlarni cheklang:
   ```bash
   cd /opt/bots/SaveX
   chmod 700 cookies
   chmod 600 cookies/instagram.txt
   head -n 1 cookies/instagram.txt      # "# Netscape HTTP Cookie File" chiqishi kerak
   ```
   (Faqat birinchi qatorni ko'rsating. Faylning ichini hech qayerga — chatga, loglarga,
   GitHub'ga — yubormang: `sessionid` bilan akkauntga kirish mumkin.)
6. Botni qayta ishga tushirish **shart emas**: cookies har bir so'rovda qayta o'qiladi.
   Tekshirish: botga Instagram rasm/karusel havolasini yuboring.

Qo'lda tekshirish (serverda, `venv` bilan):

```bash
cd /opt/bots/SaveX
venv/bin/python -m gallery_dl --cookies cookies/instagram.txt -s "<instagram post havolasi>"
```

### Qanday yangilash (cookies eskirganda)

Cookies eskirsa (Instagram sessiyani tugatsa, parol o'zgarsa, akkaunt chiqib ketsa),
foydalanuvchiga "sessiya (cookies) yo'q yoki eskirgan" xabari ko'rsatiladi va adminlarga
**`⚠️ Instagram cookies expired`** xabari keladi (har bir platforma uchun 10 daqiqada
bir martadan ko'p emas; fayl umuman bo'lmasa `cookies missing`). Yangilash:

1. Brauzerda o'sha akkauntga qayta kiring (kerak bo'lsa, Instagram so'ragan tasdiqlashni bajaring).
2. Cookies ni yuqoridagi 3-qadamdagidek qaytadan eksport qiling.
3. Serverdagi faylni **almashtiring** (4–5-qadamlar). Restart kerak emas.
4. Botga havola yuborib tekshiring. Xabar yana kelsa: akkaunt Instagram tomonidan cheklangan
   bo'lishi mumkin (checkpoint), brauzerda akkauntni tekshiring.

### Xavfsizlik

- `cookies/` papkasi `.gitignore` da; hech qachon commit qilmang.
- `deploy.sh` `cookies/` ga umuman tegmaydi (o'qimaydi, o'zgartirmaydi, o'chirmaydi) va git'da
  `cookies/` ichida fayl bo'lgan versiyani deploy qilishni rad etadi.
- Bot cookies mazmunini hech qachon loglamaydi. yt-dlp har bir yuklash uchun faylning vaqtinchalik
  nusxasini oladi va ish tugagach o'chiradi; asl faylni faqat o'qiydi.
- Docker ishlatilsa, `cookies/` papkasini konteynerga faqat o'qish uchun ulang
  (`./cookies:/app/cookies:ro`).

## 7. Boshqa loyihalar bilan to'qnashmaslik (qoidalar)

- Papka: faqat `/opt/bots/SaveX`. Boshqa loyiha papkalariga tegmang.
- Servis: `savex-bot` (docker bo'lsa compose loyiha nomi `savex`, konteynerlar, tarmoqlar va
  volume'lar `savex-` bilan boshlanadi).
- Keyingi bosqichlarda PostgreSQL va Redis konteynerlari `savex-postgres` va `savex-redis`
  deb nomlanadi, ularning portlari tashqariga ochilmaydi (faqat `savex` ichki tarmog'i).
- Faqat o'z servisingizni qayta ishga tushiring; Docker daemon, nginx va boshqa umumiy
  xizmatlarni qayta ishga tushirmang.
- Mavjud `ig.json` fayli git'da emas: u serverda `storage/ig.json` da saqlanadi
  (`/opt/bots/SaveX/ig.json` — unga symlink). Uni commit qilmang.
