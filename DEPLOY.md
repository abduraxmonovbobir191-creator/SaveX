# SaveX — Serverga joylash (Deploy)

Barcha buyruqlar serverda, loyiha papkasida bajariladi (masalan `/opt/SaveX`).

## 1. Birinchi marta o'rnatish

```bash
# Tizim paketlari
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg aria2

# Kodni yuklab olish
cd /opt
sudo git clone https://github.com/abduraxmonovbobir191-creator/SaveX.git
sudo chown -R $USER:$USER /opt/SaveX
cd /opt/SaveX

# Virtual muhit va kutubxonalar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gallery-dl          # hozircha requirements.txt da yo'q (PROGRESS.md #3)

# Sozlamalar
cp .env.example .env
nano .env                       # BOT_TOKEN, ADMIN_IDS, DATABASE_URL ni kiriting
mkdir -p storage/temp
# Instagram/YouTube cookies kerak bo'lsa: storage/cookies.txt (Netscape formatida)

chmod +x deploy.sh
```

### Lokal Telegram Bot API server

Bot `http://127.0.0.1:8081` dagi lokal Bot API serverga ulanadi (2 GB gacha fayl
yuborish uchun). U alohida ishga tushirilgan bo'lishi kerak:

```bash
telegram-bot-api --local --api-id=<API_ID> --api-hash=<API_HASH> --http-port=8081
```

(`API_ID` va `API_HASH` ni https://my.telegram.org dan olasiz. Ularni hech qayerga
commit qilmang.)

### systemd servisi `savex`

`/etc/systemd/system/savex.service` faylini yarating:

```ini
[Unit]
Description=SaveX Telegram bot
After=network-online.target

[Service]
Type=simple
User=<server_foydalanuvchisi>
WorkingDirectory=/opt/SaveX
ExecStart=/opt/SaveX/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now savex
```

## 2. Yangilash (har safar)

```bash
cd /opt/SaveX
./deploy.sh
```

`deploy.sh` quyidagilarni bajaradi:
1. Hozirgi commitni `.deploy_prev_commit` ga saqlaydi (orqaga qaytish uchun).
2. `git pull --ff-only`.
3. Kutubxonalarni o'rnatadi (`venv` bo'lsa, o'shani ishlatadi).
4. `alembic.ini` bo'lsa, `alembic upgrade head` bilan migratsiyalarni bajaradi.
5. `docker-compose.yml` bo'lsa, `docker compose up -d` qiladi; aks holda
   `sudo systemctl restart savex`.

## 3. Loglarni ko'rish

```bash
# Jonli loglar
sudo journalctl -u savex -f

# Oxirgi 200 qator
sudo journalctl -u savex -n 200 --no-pager

# Bugungi xatolar
sudo journalctl -u savex --since today -p err --no-pager

# Servis holati
sudo systemctl status savex
```

Docker ishlatilsa:

```bash
docker compose logs -f --tail=200
```

## 4. Orqaga qaytish (Rollback)

Oxirgi deploydan oldingi versiyaga qaytish:

```bash
cd /opt/SaveX
./deploy.sh rollback
```

Ma'lum bir commitga qaytish:

```bash
cd /opt/SaveX
git log --oneline -n 20          # kerakli commitni toping
git reset --hard <commit_hash>
sudo systemctl restart savex
```

Keyin yana eng so'nggi versiyaga o'tish uchun `./deploy.sh` ni ishga tushiring.

> ⚠️ Rollback ma'lumotlar bazasini qaytarmaydi. Migratsiyalar paydo bo'lgach (Phase 2),
> deploydan oldin bazadan nusxa oling:
> `cp storage/savex.db storage/savex.db.$(date +%F_%H%M).bak`

## 5. Foydali buyruqlar

```bash
sudo systemctl stop savex        # to'xtatish
sudo systemctl start savex       # ishga tushirish
sudo systemctl restart savex     # qayta ishga tushirish
du -sh storage/temp              # vaqtinchalik fayllar hajmi
rm -rf storage/temp/*            # vaqtinchalik fayllarni tozalash (bot to'xtatilganda)
```
