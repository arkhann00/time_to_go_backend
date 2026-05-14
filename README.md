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

Ручки по новообращённым:
- `GET /believers/my` — только свои
- `GET /believers/all` — все новообращённые
- `GET /believers/testimony-of-day?day=2026-05-14` — свидетельство дня (если `day` не передан, берется сегодня)
- `GET /believers/stats/accepted-jesus-count` — общее количество людей со стадией выше `interested`
- `GET /believers/latest?date_from=2026-05-01&date_to=2026-05-31` — последние 20 по `met_at` с фильтром по дате
