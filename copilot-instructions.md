# Solver Project — Copilot Instructions

## Always-On Rules

### Development Process
1. **TDD Mandatory**: Write tests BEFORE implementation. Run `python -m pytest` after each change.
2. **Pipeline**: Every feature goes through PLAN → RED → GREEN → REFACTOR → COMMIT.
3. **Review Required**: All code must pass the reviewer agent check before commit.

### Code Quality
1. Type hints on ALL functions and methods
2. Google-style docstrings on all public API
3. Custom domain exceptions (no bare `except`)
4. Constants in enums or config files (no magic strings)
5. Async/await for all I/O operations

### Architecture
1. Dependency inversion: depend on abstractions (interfaces/ABCs), not concretions
2. Repository pattern for data access
3. Pydantic models for DTOs between layers
4. Clean Architecture: Domain → Application → Infrastructure → Presentation

### Testing
1. pytest + pytest-asyncio
2. AAA pattern (Arrange-Act-Assert)
3. Mock external dependencies
4. >90% coverage on domain & application layers

### Git
1. Conventional commits: `feat|fix|refactor|test(<scope>): <message>`
2. Atomic commits (one logical change per commit)
