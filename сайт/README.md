# Lumo — демо-сайт каталога

React-витрина карточек из **той же базы**, что и бот: `lumo-bot/lumo.db` → таблица `catalog_opportunities`.

## Быстрый запуск (Windows)

```powershell
cd C:\Users\User\Desktop\lumo-bot\сайт
.\start.ps1
```

Открой **http://localhost:5173** → вкладка **«Каталог»**.

## Ручной запуск

**Терминал 1 — бэкенд:**
```powershell
cd сайт\backend
$env:LUMO_DB = "C:\Users\User\Desktop\lumo-bot\lumo.db"
.\.venv\Scripts\python -m uvicorn main:app --reload --port 8000
```

**Терминал 2 — фронтенд:**
```powershell
cd сайт\frontend
npm install
npm run dev
```

> Запускай uvicorn через `.\.venv\Scripts\python`, не системный `python`.

## Проверка подключения к базе

```text
GET http://127.0.0.1:8000/api/lumo/status
```

Пример ответа:
```json
{
  "connected": true,
  "dbPath": "C:\\Users\\User\\Desktop\\lumo-bot\\lumo.db",
  "total": 404,
  "active": 62,
  "archived": 342
}
```

## API каталога

| Метод | Описание |
|-------|----------|
| `GET /api/lumo/status` | Статус подключения к `lumo.db` |
| `GET /api/lumo/categories` | Категории и счётчики |
| `GET /api/lumo/opportunities?page=1&page_size=20` | Карточки (пагинация) |
| `GET /api/lumo/opportunities/{id}` | Детали карточки |
| `POST /api/lumo/match` | AI-подбор по запросу |

Переменная окружения **`LUMO_DB`** — путь к другому файлу SQLite, если база лежит не в корне проекта.

## Структура

```
сайт/
  backend/   — FastAPI, читает lumo.db
  frontend/  — React + Tailwind (CatalogPreview.jsx)
  start.ps1  — запуск обоих серверов
```
