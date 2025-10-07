# Telegram Ping Bot

Масштабируемый Telegram бот с модульной архитектурой для командной разработки.

## Возможности

- ✅ Команда `/start` - приветствие и список команд
- ✅ Команда `/ping` - случайная фраза из JSON
- ✅ Команда `/kill_random` - кикает случайного участника из группового чата (требует прав администратора)
- ✅ Команда `/help` - помощь
- ✅ Dead chat детектор - автоматически отправляет "💀 dead chat" если в чате не было сообщений 15 минут (работает с 9:00 до 21:00 МСК)
- ✅ Модульная архитектура
- ✅ Логирование
- ✅ Тесты
- ✅ Docker support
- ✅ Pre-commit hooks

## Быстрый старт

### С Docker (рекомендуется)

1. Получите Telegram API credentials на https://my.telegram.org
   - API_ID (число)
   - API_HASH (строка)

2. Создайте `.env`:
```bash
echo "BOT_TOKEN=YOUR_BOT_TOKEN" > .env
echo "API_ID=YOUR_API_ID" >> .env
echo "API_HASH=YOUR_API_HASH" >> .env
```

3. Установите зависимости и авторизуйте сессию:
```bash
make install
make authorize
```
   Введите номер телефона и код подтверждения из Telegram.

4. Запустите:
```bash
make docker-up
```

5. Просмотр логов:
```bash
make docker-logs
```

### Локально

1. Установите зависимости:
```bash
make install
```

2. Создайте `.env`:
```bash
echo "BOT_TOKEN=YOUR_BOT_TOKEN" > .env
echo "API_ID=YOUR_API_ID" >> .env
echo "API_HASH=YOUR_API_HASH" >> .env
```

3. Авторизуйте Telegram сессию:
```bash
make authorize
```

4. Запустите:
```bash
make run
```

## Структура проекта

```
213bot/
├── bot/                    # Основной пакет бота
│   ├── handlers/          # Обработчики команд
│   ├── services/          # Бизнес-логика
│   ├── config/            # Конфигурация
│   ├── utils/             # Утилиты
│   └── middlewares/       # Middleware
├── data/                  # Данные (phrases.json)
├── tests/                 # Тесты
├── main.py               # Точка входа
└── Dockerfile            # Docker образ
```

## Разработка

Смотрите [CONTRIBUTING.md](CONTRIBUTING.md) для деталей.

### Полезные команды

```bash
make help          # Список всех команд
make install-dev   # Установка dev зависимостей
make authorize     # Авторизация Telegram сессии
make run          # Запуск бота
make test         # Запуск тестов
make lint         # Проверка кода
make format       # Форматирование кода
```

## Настройка

Переменные окружения в `.env`:

```bash
BOT_TOKEN=your_bot_token          # Обязательно: токен бота от @BotFather
API_ID=12345678                    # Обязательно: получить на https://my.telegram.org
API_HASH=your_api_hash_here       # Обязательно: получить на https://my.telegram.org
SESSION_NAME=bot_session          # Опционально: имя сессии Pyrogram
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR
DEBUG=false                        # true/false
PHRASES_FILE=data/phrases.json    # Путь к файлу с фразами
DEAD_CHAT_MINUTES=15              # Минут неактивности для dead chat
```

## Добавление фраз

Редактируйте `data/phrases.json`:

```json
{
  "phrases": [
    "Ваша фраза 1",
    "Ваша фраза 2",
    "Ваша фраза 3"
  ]
}
```

## Команда /kill_random

Команда `/kill_random` мутит случайного участника группового чата на 3 часа.

**Требования:**
- Работает только в групповых чатах (не в личных сообщениях)
- Бот должен быть администратором чата
- У бота должно быть право "Ограничивать участников"
- Аккаунт (API_ID/API_HASH) должен быть участником чата

**Как работает:**
1. Бот получает список всех участников чата через Telegram Client API
2. Исключает ботов, удаленные аккаунты и администраторов
3. Выбирает случайного участника из оставшихся
4. Мутит выбранного участника на 3 часа

**Кулдаун:** 1 час между использованиями команды в любом чате.

**Примечание:** Для работы команды требуется авторизованный Telegram аккаунт (не бот). Используйте `make authorize` для авторизации перед запуском бота.

## Тестирование

```bash
make test
```

## Линтинг и форматирование

```bash
make lint     # Проверка кода
make format   # Автоформатирование
```

## Получение токена бота

1. Напишите [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

## Технологии

- Python 3.11+
- python-telegram-bot 20.7 (Bot API)
- pyrogram 2.0 (Client API для расширенных возможностей)
- pytest для тестов
- black, isort для форматирования
- flake8, mypy для линтинга
- Docker & Docker Compose

## Лицензия

MIT

## Contributing

См. [CONTRIBUTING.md](CONTRIBUTING.md)
