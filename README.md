# Telegram Ping Bot

Масштабируемый Telegram бот с модульной архитектурой для командной разработки.

## Возможности

- ✅ Команда `/start` - приветствие и список команд
- ✅ Команда `/ping` - случайная фраза из JSON
- ✅ Команда `/help` - помощь
- ✅ Модульная архитектура
- ✅ Логирование
- ✅ Тесты
- ✅ Docker support
- ✅ Pre-commit hooks

## Быстрый старт

### С Docker (рекомендуется)

1. Создайте `.env`:
```bash
echo "BOT_TOKEN=YOUR_TOKEN" > .env
```

2. Запустите:
```bash
make docker-up
```

3. Просмотр логов:
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
echo "BOT_TOKEN=YOUR_TOKEN" > .env
```

3. Запустите:
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
make run          # Запуск бота
make test         # Запуск тестов
make lint         # Проверка кода
make format       # Форматирование кода
```

## Настройка

Переменные окружения в `.env`:

```bash
BOT_TOKEN=your_bot_token          # Обязательно
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR
DEBUG=false                        # true/false
PHRASES_FILE=data/phrases.json    # Путь к файлу с фразами
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
- python-telegram-bot 20.7
- pytest для тестов
- black, isort для форматирования
- flake8, mypy для линтинга
- Docker & Docker Compose

## Лицензия

MIT

## Contributing

См. [CONTRIBUTING.md](CONTRIBUTING.md)
