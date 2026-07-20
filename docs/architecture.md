# Solver — Architecture Document

## 1. System Context

```
┌──────────┐     ┌─────────────────┐     ┌──────────┐
│ Telegram │────▶│  Solver Bot     │────▶│ OpenAI   │
│  User    │◀────│  (FastAPI/PTB)  │◀────│  API     │
└──────────┘     └───────┬─────────┘     └──────────┘
                         │
                  ┌──────▼─────────┐
                  │   SQLite/      │
                  │   PostgreSQL   │
                  └────────────────┘
```

## 2. Clean Architecture Layers

### Domain Layer (`src/solver/domain/`)
Pure business logic. No external dependencies.

**Entities**:
- `Problem` (aggregate root): id, user_id, title, description, status, priority, created_at, updated_at
- `SolutionStep`: id, problem_id, order, description, status, ai_generated_at
- `User`: id, telegram_id, username, timezone, proactive_enabled, created_at
- `ConversationContext`: id, problem_id, messages[], summary, tokens_used

**Value Objects**:
- `ProblemId`, `StepId`, `UserId` (UUID-based)
- `ProblemStatus` (enum: DRAFT, ANALYZING, ACTIVE, ON_HOLD, RESOLVED)
- `StepStatus` (enum: PENDING, IN_PROGRESS, COMPLETED, SKIPPED)
- `Priority` (enum: LOW, MEDIUM, HIGH, CRITICAL)
- `ProactiveLevel` (enum: GENTLE, MODERATE, PERSISTENT)

**Repository Interfaces** (abstract):
- `ProblemRepository`
- `UserRepository`
- `ConversationContextRepository`

### Application Layer (`src/solver/application/`)
Orchestrates domain objects. Contains use cases.

**Services**:
- `ProblemService`: CRUD + AI analysis orchestration
- `AIAnalysisService`: Prompt engineering, AI response parsing
- `NotificationService`: Proactive reminders logic
- `UserService`: User preferences, onboarding

**DTOs**:
- `CreateProblemDTO`, `ProblemResponseDTO`
- `AIAnalysisResultDTO`
- `StepUpdateDTO`

### Infrastructure Layer (`src/solver/infrastructure/`)
External adapters implementing domain interfaces.

- `SqlAlchemyProblemRepository`
- `SqlAlchemyUserRepository`
- `TelegramBotAdapter` (python-telegram-bot)
- `OpenAIClientAdapter`
- `APSchedulerAdapter`
- `SQLAlchemyUnitOfWork`

### Presentation Layer (`src/solver/presentation/`)
- `telegram/handlers/`: Command handlers, conversation handlers, callback handlers
- `telegram/middleware/`: User identification, logging, error handling

## 3. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Clean Architecture | Testability, framework independence, domain isolation |
| Repository Pattern | Swap SQLite→PostgreSQL without domain changes |
| Async SQLAlchemy | Non-blocking DB operations in async bot |
| Pydantic v2 DTOs | Type-safe data transfer, automatic validation |
| APScheduler | Lightweight in-process scheduling for proactive reminders |
| python-telegram-bot | Mature async Telegram Bot API wrapper |
| UUID for IDs | Avoid sequential ID enumeration, future sharding |

## 4. Database Schema

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    timezone TEXT DEFAULT 'UTC',
    proactive_level TEXT DEFAULT 'moderate',
    proactive_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Problems
CREATE TABLE problems (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'draft',
    priority TEXT DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Solution Steps
CREATE TABLE solution_steps (
    id UUID PRIMARY KEY,
    problem_id UUID REFERENCES problems(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    ai_suggestion TEXT,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Conversation Context
CREATE TABLE conversation_contexts (
    id UUID PRIMARY KEY,
    problem_id UUID REFERENCES problems(id) ON DELETE CASCADE,
    messages JSONB DEFAULT '[]',
    summary TEXT,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Proactive Triggers
CREATE TABLE proactive_triggers (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    problem_id UUID REFERENCES problems(id),
    trigger_type TEXT NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    fired_at TIMESTAMP,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 5. API Flow: User Creates a Problem

```
User: "У меня конфликт с коллегой на работе"
  │
  ▼
Telegram Handler ──▶ ProblemService.create_problem(dto)
  │                      │
  │                      ├─▶ ProblemRepository.add(problem)
  │                      ├─▶ AIAnalysisService.analyze(problem)
  │                      │      ├─▶ Build prompt with context
  │                      │      ├─▶ OpenAI API call
  │                      │      └─▶ Parse response → SolutionStep[]
  │                      ├─▶ ProblemRepository.add_steps(steps)
  │                      └─▶ Scheduler.schedule_followup(problem)
  │
  ▼
Bot replies: "Я проанализировал ситуацию. Вот план действий:
  1. Запиши конкретные примеры конфликтных ситуаций
  2. Определи свою позицию и потребности
  3. Предложи коллеге встречу 1-на-1 в нейтральной обстановке
  
  Начнём с первого шага? Я напомню о нём завтра утром."
```
