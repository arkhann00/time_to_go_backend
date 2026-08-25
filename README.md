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

## Запуск в Docker (production, HTTPS)

Перед запуском убедитесь, что:
- DNS-запись `api.time.to.go.xn--80a6ad.space` указывает на IP сервера
- Порты `80` и `443` открыты на сервере

```bash
docker compose up --build -d
```

Caddy автоматически получит TLS-сертификат от Let's Encrypt.

```text
API:     https://api.time.to.go.xn--80a6ad.space
Swagger: https://api.time.to.go.xn--80a6ad.space/docs
```

## После локального запуска

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

## Push-напоминание по пятницам

Сервер раз в 15 минут проверяет активные устройства. Если в часовом поясе хотя бы
одного устройства пользователя пятница и попадает заданное время напоминания (по
умолчанию `18:00`), пользователь имеет хотя бы одного новообращённого и уведомление
ещё не отправлялось в эту локальную пятницу, оно уйдёт на все его активные устройства.

Для Firebase задайте **один** из вариантов только через окружение или secret storage:

```bash
# Полный JSON сервисного аккаунта Firebase в одной environment variable.
FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

# Или путь к JSON-файлу, смонтированному как secret вне репозитория.
FIREBASE_SERVICE_ACCOUNT_PATH=/run/secrets/firebase-service-account.json
```

Не добавляйте ключ сервисного аккаунта, FCM token или `.env` с секретами в Git.

При запуске через Docker Compose JSON должен быть записан в `.env` **одной
строкой**, после `FIREBASE_SERVICE_ACCOUNT_JSON=`. Многострочный JSON Compose
прочитать не сможет. Переменная передаётся в контейнер через `docker-compose.yml`.

Планировщик запускается вместе с FastAPI. Для отдельного production-процесса (это
предпочтительно при нескольких API-инстансах) запускайте:

```bash
uv run python -m src.notifications.scheduler
```

Журнал отправок в БД с уникальным ключом `(user_id, notification_type, local_date)`
не допускает дубль даже при одновременной работе нескольких планировщиков. При запуске
отдельного процесса API-планировщик следует отключить через `ENABLE_PUSH_SCHEDULER=false`.

### Контракт для Flutter

Все вызовы ниже требуют `Authorization: Bearer <access_token>`.

```http
PUT /auth/me/push-device
Content-Type: application/json

{"token":"<FCM token>","platform":"ios","timezone":"Europe/Moscow"}
```

`platform`: `ios` или `android`; `timezone` — валидный IANA timezone. Повторная
регистрация того же token обновляет устройство и включает его.

```http
DELETE /auth/me/push-device
Content-Type: application/json

{"token":"<FCM token>"}

POST /auth/me/test-push-notification

POST /auth/test-push-notification
Content-Type: application/json

{"token":"<FCM token>"}

GET /auth/me/notification-settings

PATCH /auth/me/notification-settings
Content-Type: application/json

{"believers_friday_reminder_enabled":true,"believers_friday_reminder_time":"18:00"}
```

Настройки возвращают поля `believers_friday_reminder_enabled` и
`believers_friday_reminder_time`. Тело `PATCH` частичное. Уведомление содержит
`notification.title = "Время идти 🙌"`, `notification.body = "Напиши своим ребятам и пригласи их в церковь."`,
а также `data.type = believers_friday_reminder` и `data.screen = believers`.

`POST /auth/me/test-push-notification` немедленно отправляет этот же payload на все
активные устройства текущего пользователя — без проверки дня недели, локального
времени или наличия новообращённых. Ответ: `{ "sent_to_devices": 1 }`.

`POST /auth/test-push-notification` не требует авторизации и отправляет payload
только на FCM token из тела запроса. Он не сохраняет token и не зависит от данных
пользователя. Ответ: `{ "sent": true }`.

### Временная Admin-ручка

`GET /auth/admin/push-device-tokens` находится во вкладке `Admin` Swagger и без
авторизации возвращает все сохранённые FCM tokens. Она добавлена только для ручного
тестирования и **небезопасна**: перед production её необходимо удалить или защитить
ролью администратора.
