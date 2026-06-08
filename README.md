# Time To Go Backend

## Локальный запуск

```bash
# 1) установить зависимости
uv sync

# 2) применить миграции
uv run alembic upgrade head

# 3) запустить сервер
uv run uvicorn src.main:app --reload
```

## Запуск в Docker

```bash
# 1) собрать образ
docker build -t time_to_go_backend .

# 2) запустить контейнер
docker run --rm -p 8000:8000 time_to_go_backend
```

или через docker compose:

```bash
docker compose up --build
```

## После запуска

```text
API: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs
```

## Профиль пользователя

Защищенные ручки (нужен `Authorization: Bearer <token>`):

- `GET /auth/me` — получить текущий профиль
- `PATCH /auth/me` — обновить свой профиль (поля `name`, `about`)
- `POST /auth/me/avatar` — загрузить свою аватарку (`multipart/form-data`, поле `avatar`)

Ограничения для аватарки:

- поддерживаются: `JPEG`, `PNG`, `WEBP`, `GIF`, `HEIC`, `HEIF`
- максимальный размер: `5MB`
- после загрузки backend сохраняет файл в `uploads/avatars` и возвращает путь в `avatar_url`

Получение фото:

- `GET /uploads/{path}` — публичный эндпоинт, авторизация не нужна
- полный URL аватарки: `http://127.0.0.1:8000` + `avatar_url` (например: `http://127.0.0.1:8000/uploads/avatars/user_1_abc123.jpg`)

Ручки по новообращённым:
- `GET /believers/my` — только свои
- `GET /believers/all` — все новообращённые
- `GET /believers/testimony-of-day?day=2026-05-14` — свидетельство дня (если `day` не передан, берется сегодня)
- `GET /believers/stats/accepted-jesus-count` — общее количество людей со стадией выше `interested`
- `GET /believers/latest?date_from=2026-05-01&date_to=2026-05-31` — последние 20 по `met_at` с фильтром по дате
