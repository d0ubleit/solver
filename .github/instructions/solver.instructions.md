# Solver Project Instructions

## Project: Solver — Proactive AI Problem-Solver Telegram Bot

## Always-On Rules
1. **TDD REQUIRED**: No implementation code without tests first. Write test → see it fail → implement → see it pass.
2. **SOLID Compliance**: Every class must follow SOLID principles. Reviewer agent checks this.
3. **Pipeline**: Every feature goes through PLAN → RED → GREEN → REFACTOR → COMMIT stages.
4. **Clean Code**: Type hints, docstrings, no magic values, consistent naming.
5. **Async by Default**: All I/O operations use async/await.
6. **Pydantic DTOs**: All data transfer between layers uses Pydantic models.
7. **Git Atomicity**: Commit each logical change separately with conventional commit messages.
8. **Memory**: Store important decisions, architecture notes, and patterns in `/memories/repo/`.

## Technology Stack
- Python 3.11+
- python-telegram-bot (async)
- OpenAI API (GPT-4o-mini / GPT-4o)
- SQLAlchemy 2.0+ (async)
- SQLite (dev) / PostgreSQL (prod)
- APScheduler
- Pytest + pytest-asyncio
- Pydantic v2

## Project Structure
```
src/solver/
├── domain/          # Entities, Value Objects, Repository interfaces
├── application/     # Use cases, services, DTOs
├── infrastructure/  # DB, Telegram, AI, Scheduler adapters
└── presentation/    # Telegram handlers
tests/
├── unit/
├── integration/
└── conftest.py
```

## Naming Conventions
- Modules: `snake_case`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`
- Test files: `test_<module>.py`
- Test functions: `test_<behavior>_<expected_result>()`
