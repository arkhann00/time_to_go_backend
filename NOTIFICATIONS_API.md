# Push-уведомления: контракт для Flutter

Этот документ описывает все backend-ручки, связанные с push-уведомлениями, и
последовательность их использования во Flutter.

## Базовый адрес и авторизация

Локально: `http://127.0.0.1:8000`.

Для ручек текущего пользователя передавайте JWT после входа:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

`access_token` возвращается `POST /auth/login`.

## Рекомендуемый сценарий Flutter

1. Инициализировать Firebase и запросить разрешение на уведомления.
2. Получить FCM token через `FirebaseMessaging.instance.getToken()`.
3. После успешного входа отправить token в `PUT /auth/me/push-device`.
4. При `FirebaseMessaging.instance.onTokenRefresh` повторить этот `PUT` с новым
   token.
5. При выходе пользователя из аккаунта удалить устройство через
   `DELETE /auth/me/push-device`.
6. Получить и при необходимости изменить настройки напоминания.

Пример получения и регистрации token:

```dart
final messaging = FirebaseMessaging.instance;
await messaging.requestPermission();

final fcmToken = await messaging.getToken();
if (fcmToken != null) {
  await api.put(
    '/auth/me/push-device',
    data: {
      'token': fcmToken,
      'platform': Platform.isIOS ? 'ios' : 'android',
      'timezone': 'Europe/Moscow', // Получать из устройства, а не хардкодить.
    },
  );
}

FirebaseMessaging.instance.onTokenRefresh.listen((newToken) async {
  await api.put(
    '/auth/me/push-device',
    data: {
      'token': newToken,
      'platform': Platform.isIOS ? 'ios' : 'android',
      'timezone': deviceTimezone,
    },
  );
});
```

`timezone` должен быть IANA-идентификатором, например `Europe/Moscow`,
`Asia/Yekaterinburg` или `America/New_York`. Используйте библиотеку Flutter,
которая возвращает IANA timezone устройства.

## Устройства

### Зарегистрировать или обновить устройство

```http
PUT /auth/me/push-device
Authorization: Bearer <access_token>

{
  "token": "<FCM token>",
  "platform": "ios",
  "timezone": "Europe/Moscow"
}
```

`platform` принимает только `ios` или `android`.

Один FCM token хранится один раз. Повторный запрос с тем же token обновляет его
платформу, timezone и включает устройство.

Ответ `200`:

```json
{
  "id": 12,
  "platform": "ios",
  "timezone": "Europe/Moscow",
  "enabled": true,
  "created_at": "2026-08-24T12:00:00",
  "updated_at": "2026-08-24T12:00:00"
}
```

### Удалить устройство при logout

```http
DELETE /auth/me/push-device
Authorization: Bearer <access_token>

{
  "token": "<FCM token>"
}
```

Ответ — `204 No Content`. Если token текущему пользователю не принадлежит или уже
удалён, backend вернёт `404`.

## Настройки субботнего напоминания

Напоминание по умолчанию включено и запланировано на `10:00` в timezone активного
устройства пользователя. Backend проверяет расписание каждые 15 минут. Одному
пользователю оно не отправляется дважды в одну локальную субботу.

Также через 24 часа после добавления каждого новообращённого backend отправляет
владельцу одно напоминание написать этому человеку. В payload такого уведомления
передаются `type: new_believer_follow_up` и `screen: believers`.

### Получить настройки

```http
GET /auth/me/notification-settings
Authorization: Bearer <access_token>
```

Ответ `200`:

```json
{
  "believers_friday_reminder_enabled": true,
  "believers_friday_reminder_time": "10:00"
}
```

### Изменить настройки

Тело частичное — можно передать один или оба поля.

```http
PATCH /auth/me/notification-settings
Authorization: Bearer <access_token>

{
  "believers_friday_reminder_enabled": false,
  "believers_friday_reminder_time": "19:30"
}
```

Время передаётся в формате `HH:MM`.

## Тестовая отправка

### На все устройства текущего пользователя

```http
POST /auth/me/test-push-notification
Authorization: Bearer <access_token>
```

Сразу отправляет уведомление на все активные устройства пользователя, без проверки
даты, времени или наличия новообращённых.

Ответ:

```json
{ "sent_to_devices": 1 }
```

### На один явно переданный token без авторизации

```http
POST /auth/test-push-notification
Content-Type: application/json

{ "token": "<FCM token>" }
```

Ответ:

```json
{ "sent": true }
```

Эта ручка предназначена только для ручной отладки. Она публична и не сохраняет
переданный token.

## Входящий FCM payload

Flutter должен обрабатывать `data` как маршрутизацию внутри приложения:

```json
{
  "notification": {
    "title": "Время идти 🙌",
    "body": "Напиши своим ребятам и пригласи их в церковь."
  },
  "data": {
    "type": "believers_friday_reminder",
    "screen": "believers"
  }
}
```

Для Android используется notification channel `general`; для iOS — звук `default`.
При открытии уведомления Flutter может направить пользователя на экран
`believers`, проверив `message.data['screen']`.

## Временная Admin-ручка

```http
GET /auth/admin/push-device-tokens
```

Ручка отображается во вкладке `Admin` Swagger и отдаёт все сохранённые FCM tokens.
Она временно публична, небезопасна и нужна только для отладки. Не используйте её в
клиентском приложении; перед production она должна быть удалена или защищена ролью
администратора.
