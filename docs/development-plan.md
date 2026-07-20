# Solver — Development Plan

## Phase 0: Project Setup (Current)
- [x] Initialize git repository
- [x] Create agent team (architect, developer, tester, reviewer, pm)
- [x] Create development pipeline
- [x] Architecture document
- [ ] Python project setup (pyproject.toml, deps)
- [ ] CI config (GitHub Actions for pytest)

## Phase 1: Domain Core (TDD)
**User Stories**: None yet (foundational)
**Deliverables**:
- [ ] Domain entities: `Problem`, `SolutionStep`, `User`
- [ ] Value objects: `ProblemId`, `StepId`, enums
- [ ] Repository interfaces (ABCs)
- [ ] Domain exceptions
- [ ] Unit tests for all entities and value objects

## Phase 2: Infrastructure — Database (TDD)
**User Stories**: None yet (foundational)
**Deliverables**:
- [ ] SQLAlchemy ORM models
- [ ] Repository implementations
- [ ] Unit of Work pattern
- [ ] Database migrations (Alembic)
- [ ] Integration tests with SQLite

## Phase 3: Application Services (TDD)
**User Stories**:
- US-001: Create a problem
- US-002: AI analyzes a problem
**Deliverables**:
- [ ] `ProblemService` with CRUD
- [ ] `AIAnalysisService` with OpenAI integration
- [ ] DTO classes (Pydantic)
- [ ] Unit tests with mocked repositories and AI client
- [ ] Integration tests for AI client

## Phase 4: Telegram Bot — Presentation Layer (TDD)
**User Stories**:
- US-003: User interacts with bot to create problem
- US-004: User views problem status and steps
- US-005: User marks steps as complete
**Deliverables**:
- [ ] Telegram bot setup (webhook or polling)
- [ ] Command handlers: /start, /new, /list, /view, /done
- [ ] Conversation handlers for problem creation flow
- [ ] Callback handlers for step interactions
- [ ] Integration tests with mocked Telegram API

## Phase 5: Proactive Engine (TDD)
**User Stories**:
- US-006: User receives daily reminders
- US-007: User receives problem-specific follow-ups
**Deliverables**:
- [ ] APScheduler integration
- [ ] Proactive trigger logic
- [ ] Notification message templates
- [ ] Integration tests for scheduler

## Phase 6: Polish & Production Readiness
- [ ] Error handling & retry logic
- [ ] Rate limiting for OpenAI API
- [ ] Logging & monitoring
- [ ] Environment configuration (.env)
- [ ] README with setup instructions
- [ ] Docker setup
