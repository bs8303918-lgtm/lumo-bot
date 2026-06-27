# Хостинг Lumo (aiogram + Telethon)

Бот должен работать **24/7** в одном процессе: polling, мониторинг каналов и LLM.

## Рекомендация: VPS

Подойдёт любой Linux VPS с 1 GB RAM:

- [Hetzner](https://www.hetzner.com/) — от ~€4/мес
- [Timeweb Cloud](https://timeweb.cloud/) — удобно из Казахстана
- [DigitalOcean](https://www.digitalocean.com/) — от $6/мес
- Oracle Cloud Free Tier — бесплатный VPS (сложнее настроить)

**Не подходят** serverless (Vercel, Cloudflare Workers) — нужен постоянный процесс и файл сессии Telethon.

---

## Быстрый деплой на Ubuntu

### 1. Сервер

```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv git
```

### 2. Код

```bash
cd /opt
sudo git clone <твой-репозиторий> lumo-bot
sudo chown -R $USER:$USER lumo-bot
cd lumo-bot
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. `.env`

Скопируй с локальной машины и отредактируй:

```bash
cp .env.example .env
nano .env
```

Обязательно: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_ADMIN_CHAT_ID`, LLM-ключ.

### 4. Telethon — один раз

**Вариант A (проще):** залогинься локально, скопируй сессию на сервер:

```powershell
# с Windows — после успешного telethon_login_qr.py
scp lumo_session.session user@SERVER:/opt/lumo-bot/
```

**Вариант B:** на сервере по SSH:

```bash
source .venv/bin/activate
python scripts/telethon_login_qr.py
# отсканируй QR в Telegram → Настройки → Устройства
```

### 5. База

```bash
python scripts/init_db.py
```

Для продакшена можно PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/lumo
```

### 6. systemd — автозапуск

```bash
sudo cp deploy/lumo.service /etc/systemd/system/
sudo nano /etc/systemd/system/lumo.service   # поправь User= и путь
sudo systemctl daemon-reload
sudo systemctl enable lumo
sudo systemctl start lumo
sudo systemctl status lumo
```

Логи:

```bash
journalctl -u lumo -f
tail -f logs/app.log
```

---

## Что хранить на сервере (бэкап)

| Файл | Зачем |
|------|--------|
| `lumo_session.session` | Telethon — без него мониторинг каналов умрёт |
| `lumo.db` | пользователи и посты (если SQLite) |
| `.env` | секреты |

---

## Обновление

```bash
cd /opt/lumo-bot
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart lumo
```

---

## Чеклист после деплоя

1. `systemctl status lumo` — active (running)
2. В боте `/health` — Telethon ✅, LLM ✅
3. В логах: `Monitor cycle: N channels to check`
4. Тест: `/set_interest` → карточка приходит

---

## Баги

Пользователи пишут `/bug` или напрямую @taton4i.
