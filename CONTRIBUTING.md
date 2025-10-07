# Contributing Guide

Спасибо за интерес к проекту! Эта инструкция поможет начать разработку.

## Требования

- Python 3.11+
- Docker и Docker Compose (опционально)
- Git

## Настройка окружения

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd 213bot
```

2. **Создайте виртуальное окружение:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. **Установите зависимости для разработки:**
```bash
make install-dev
# или
pip install -r requirements-dev.txt
```

4. **Настройте pre-commit hooks:**
```bash
pre-commit install
```

5. **Создайте .env файл:**
```bash
cp .env.example .env
# Отредактируйте .env и добавьте ваш BOT_TOKEN
```

## Структура проекта

```
213bot/
├── bot/                    # Основной пакет бота
│   ├── handlers/          # Обработчики команд
│   │   ├── basic.py      # Базовые команды (/start, /help)
│   │   ├── ping.py       # Команда /ping
│   │   └── __init__.py
│   ├── services/         # Бизнес-логика
│   │   ├── phrase_service.py
│   │   └── __init__.py
│   ├── config/           # Конфигурация
│   │   ├── settings.py
│   │   └── __init__.py
│   ├── utils/            # Утилиты
│   │   ├── logger.py
│   │   └── __init__.py
│   └── middlewares/      # Middleware (будущее)
├── data/                  # Данные
│   └── phrases.json      # Фразы для /ping
├── tests/                # Тесты
├── main.py               # Точка входа
├── requirements.txt      # Зависимости
├── Dockerfile           # Docker образ
├── docker-compose.yml   # Docker Compose конфигурация
└── Makefile            # Команды для разработки
```

## Разработка

### Запуск бота локально

```bash
make run
```

### Запуск с Docker

```bash
make docker-up
make docker-logs  # Просмотр логов
```

### Форматирование кода

```bash
make format
```

Используем:
- **black** для форматирования
- **isort** для сортировки импортов

### Линтинг

```bash
make lint
```

Проверяем:
- **flake8** - стиль кода
- **mypy** - типы
- **black** - форматирование
- **isort** - импорты

### Тесты

```bash
make test
```

Все тесты должны проходить перед коммитом.

## Добавление новых функций

### 1. Новый handler

Создайте файл в `bot/handlers/`:

```python
# bot/handlers/my_feature.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mycommand"""
    await update.message.reply_text("Response")

def register_my_handlers(app: Application) -> None:
    """Register handlers"""
    app.add_handler(CommandHandler("mycommand", my_command))
    logger.info("My handlers registered")
```

Зарегистрируйте в `bot/handlers/__init__.py`:

```python
from .my_feature import register_my_handlers

def register_all_handlers(app: Application) -> None:
    register_basic_handlers(app)
    register_ping_handlers(app)
    register_my_handlers(app)  # Добавьте сюда
```

### 2. Новый service

Создайте файл в `bot/services/`:

```python
# bot/services/my_service.py
import logging

logger = logging.getLogger(__name__)

class MyService:
    """Description of service"""

    def __init__(self):
        pass

    def do_something(self) -> str:
        """Do something useful"""
        return "result"
```

### 3. Тесты

Создайте тест в `tests/`:

```python
# tests/test_my_feature.py
import pytest
from bot.services.my_service import MyService

def test_my_service():
    service = MyService()
    result = service.do_something()
    assert result == "result"
```

## Git workflow

1. **Создайте ветку для фичи:**
```bash
git checkout -b feature/my-feature
```

2. **Делайте коммиты с понятными сообщениями:**
```bash
git add .
git commit -m "Add new feature: description"
```

3. **Запустите тесты и линтеры:**
```bash
make test
make lint
```

4. **Отправьте изменения:**
```bash
git push origin feature/my-feature
```

5. **Создайте Pull Request**

## Стандарты кода

- Используйте **английский** для комментариев и docstrings
- Используйте **русский** для пользовательских сообщений
- Следуйте **PEP 8**
- Добавляйте **type hints**
- Пишите **docstrings** для функций и классов
- Покрывайте код **тестами**
- Максимальная длина строки: **100 символов**

## Коммит сообщения

Используйте conventional commits:

- `feat:` - новая функция
- `fix:` - исправление бага
- `docs:` - документация
- `style:` - форматирование
- `refactor:` - рефакторинг
- `test:` - тесты
- `chore:` - рутинные задачи

Примеры:
```
feat: add user statistics command
fix: handle empty phrases list
docs: update README with new commands
```

## Получение помощи

- Создайте Issue в GitHub
- Опишите проблему подробно
- Приложите логи если есть

## Code Review

При ревью кода проверяем:
- Работоспособность кода
- Наличие тестов
- Качество кода
- Документацию
- Соответствие стандартам

Спасибо за вклад! 🚀
