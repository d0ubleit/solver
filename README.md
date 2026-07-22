# Solver — Проактивный AI-трекер проблем (Telegram Bot)

[![Tests](https://img.shields.io/badge/tests-76%20passed-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

**Solver** — это Telegram бот с искусственным интеллектом, который помогает решать жизненные и рабочие проблемы. В отличие от обычных трекеров задач, Solver проактивно анализирует проблему, предлагает конкретные шаги и мягко сопровождает пользователя до результата.

## Как это работает

1. Вы описываете проблему боту (например: «У меня конфликт с коллегой»)
2. AI анализирует ситуацию и предлагает 3-5 конкретных шагов для решения
3. Бот периодически напоминает о прогрессе и помогает не забросить проблему
4. Вы отмечаете выполненные шаги и видите прогресс

## Установка и запуск

### Предварительные требования

- Python 3.11 или выше
- Токен Telegram бота (получить у [@BotFather](https://t.me/BotFather))
- API ключ OpenAI (получить на [platform.openai.com](https://platform.openai.com))

### Быстрый старт

```bash
# Клонировать репозиторий
git clone <repo-url> && cd solver

# Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Установить зависимости
pip install -e ".[dev]"

# Настроить переменные окружения
cp .env.example .env
# Отредактировать .env: указать TELEGRAM_BOT_TOKEN и OPENAI_API_KEY

# Запустить бота
python -m solver.main
```

### Запуск через Docker (рекомендуется)

```bash
# Первый запуск или после изменений в коде:
docker compose down && docker compose build --no-cache && docker compose up -d

# Быстрый перезапуск (без изменений в коде):
docker compose restart

# Остановка:
docker compose down

# Просмотр логов:
docker compose logs --tail=50

# Очистить БД (при изменении схемы):
docker compose down && docker volume rm solver_solver-data && docker compose up -d
```

### Запуск локально (для разработки)

```bash
python -m solver.main
```

### Запуск тестов

```bash
# Все тесты
python -m pytest tests/ -v

# Только unit-тесты
python -m pytest tests/unit/ -v

# Только интеграционные
python -m pytest tests/integration/ -v

# С покрытием
python -m pytest tests/ --cov=solver --cov-report=term-missing
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начало работы, приветствие |
| `/new` | Создать новую проблему (интерактивный режим) |
| `/list` | Показать активные проблемы |
| `/view N` | Посмотреть проблему №N |
| `/done N M` | Отметить шаг M проблемы N как выполненный |
| `/help` | Показать справку |

## Архитектура

Проект построен по принципам **Clean Architecture** и **SOLID**:

```
src/solver/
├── domain/           # Бизнес-логика: сущности, value objects, интерфейсы репозиториев
├── application/      # Сценарии использования: сервисы, DTO, AI-интеграция
├── infrastructure/   # Адаптеры: БД (SQLAlchemy), Telegram, OpenAI, планировщик
└── presentation/     # Обработчики команд Telegram бота
```

- **Domain Layer** — чистая бизнес-логика, независимая от фреймворков
- **Application Layer** — оркестрация use cases, зависит только от доменных интерфейсов
- **Infrastructure Layer** — реализации интерфейсов (БД, внешние API)
- **Presentation Layer** — Telegram-обработчики, форматирование ответов

## Технологический стек

- **Язык**: Python 3.11+
- **Telegram API**: python-telegram-bot (async)
- **AI**: OpenAI API (GPT-4o-mini / GPT-4o)
- **База данных**: SQLAlchemy 2.0+ (async) + SQLite/PostgreSQL
- **Планировщик**: APScheduler
- **Тестирование**: pytest + pytest-asyncio + pytest-mock
- **Валидация**: Pydantic v2
- **Логирование**: Loguru

## Разработка

Проект использует TDD (Test-Driven Development) и агентный пайплайн разработки:

1. **PLAN** — архитектор и PM проектируют решение
2. **RED** — тестировщик пишет падающие тесты
3. **GREEN** — разработчик реализует код
4. **REFACTOR** — ревьюер проверяет качество и SOLID
5. **COMMIT** — атомарный коммит с осмысленным сообщением

### Агенты команды

В `.github/agents/` находятся конфигурации AI-агентов:
- `architect` — системный архитектор
- `developer` — senior разработчик
- `tester` — QA/TDD инженер
- `reviewer` — код ревьюер
- `pm` — продакт менеджер

## Лицензия

MIT
