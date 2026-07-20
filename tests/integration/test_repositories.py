"""Integration tests for SQLAlchemy repository implementations."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from solver.infrastructure.database import Base, reset_engine
from solver.infrastructure.models import (
    UserModel,
    ProblemModel,
    StepModel,
    ConversationContextModel,
)
from solver.infrastructure.repositories import (
    SqlAlchemyUserRepository,
    SqlAlchemyProblemRepository,
    SqlAlchemyConversationContextRepository,
)
from solver.domain.entities import User, Problem, SolutionStep, ConversationContext
from solver.domain.value_objects import (
    UserId,
    ProblemId,
    ProblemStatus,
    StepStatus,
    Priority,
    ProactiveLevel,
)
from solver.domain.exceptions import ProblemNotFoundError, UserNotFoundError


@pytest_asyncio.fixture(scope="function")
async def async_session():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def user_repo(async_session: AsyncSession):
    """Create a UserRepository backed by the test database."""
    return SqlAlchemyUserRepository(async_session)


@pytest_asyncio.fixture
async def problem_repo(async_session: AsyncSession):
    """Create a ProblemRepository backed by the test database."""
    return SqlAlchemyProblemRepository(async_session)


@pytest_asyncio.fixture
async def context_repo(async_session: AsyncSession):
    """Create a ConversationContextRepository backed by the test database."""
    return SqlAlchemyConversationContextRepository(async_session)


class TestUserRepository:
    """Integration tests for SqlAlchemyUserRepository."""

    async def test_add_and_retrieve_user(self, user_repo: SqlAlchemyUserRepository) -> None:
        """Verify a user can be added and retrieved by ID."""
        user = User(telegram_id=123456789, username="testuser")
        await user_repo.add(user)

        retrieved = await user_repo.get_by_id(user.id)
        assert retrieved is not None
        assert retrieved.telegram_id == 123456789
        assert retrieved.username == "testuser"

    async def test_get_by_telegram_id(self, user_repo: SqlAlchemyUserRepository) -> None:
        """Verify a user can be retrieved by Telegram ID."""
        user = User(telegram_id=987654321)
        await user_repo.add(user)

        retrieved = await user_repo.get_by_telegram_id(987654321)
        assert retrieved is not None
        assert retrieved.id == user.id

    async def test_get_nonexistent_user(self, user_repo: SqlAlchemyUserRepository) -> None:
        """Verify None is returned for a nonexistent user."""
        result = await user_repo.get_by_id(UserId.generate())
        assert result is None

    async def test_update_user(self, user_repo: SqlAlchemyUserRepository) -> None:
        """Verify a user's fields can be updated."""
        user = User(telegram_id=111111, proactive_level=ProactiveLevel.GENTLE)
        await user_repo.add(user)

        user.set_proactive_level(ProactiveLevel.PERSISTENT)
        user.disable_proactive()
        await user_repo.update(user)

        retrieved = await user_repo.get_by_id(user.id)
        assert retrieved is not None
        assert retrieved.proactive_level == ProactiveLevel.PERSISTENT
        assert retrieved.proactive_enabled is False

    async def test_update_nonexistent_user_raises_error(
        self, user_repo: SqlAlchemyUserRepository
    ) -> None:
        """Verify updating a nonexistent user raises UserNotFoundError."""
        user = User(telegram_id=999999)
        with pytest.raises(UserNotFoundError):
            await user_repo.update(user)


class TestProblemRepository:
    """Integration tests for SqlAlchemyProblemRepository."""

    async def test_add_and_retrieve_problem(
        self,
        user_repo: SqlAlchemyUserRepository,
        problem_repo: SqlAlchemyProblemRepository,
    ) -> None:
        """Verify a problem can be added and retrieved with steps."""
        user = User(telegram_id=555555)
        await user_repo.add(user)

        problem = Problem(user_id=user.id, title="Test Problem")
        problem.add_step("Step 1")
        problem.add_step("Step 2")
        await problem_repo.add(problem)

        retrieved = await problem_repo.get_by_id(problem.id)
        assert retrieved is not None
        assert retrieved.title == "Test Problem"
        assert retrieved.total_steps_count == 2

    async def test_get_problems_by_user(
        self,
        user_repo: SqlAlchemyUserRepository,
        problem_repo: SqlAlchemyProblemRepository,
    ) -> None:
        """Verify all problems for a user can be retrieved."""
        user = User(telegram_id=222222)
        await user_repo.add(user)

        p1 = Problem(user_id=user.id, title="Problem 1")
        p2 = Problem(user_id=user.id, title="Problem 2")
        await problem_repo.add(p1)
        await problem_repo.add(p2)

        problems = await problem_repo.get_by_user_id(user.id)
        assert len(problems) == 2

    async def test_get_active_problems_only(
        self,
        user_repo: SqlAlchemyUserRepository,
        problem_repo: SqlAlchemyProblemRepository,
    ) -> None:
        """Verify only active (non-resolved) problems are returned."""
        user = User(telegram_id=333333)
        await user_repo.add(user)

        p1 = Problem(user_id=user.id, title="Active", status=ProblemStatus.ACTIVE)
        p2 = Problem(user_id=user.id, title="Resolved", status=ProblemStatus.RESOLVED)
        await problem_repo.add(p1)
        await problem_repo.add(p2)

        active = await problem_repo.get_active_by_user_id(user.id)
        assert len(active) == 1
        assert active[0].title == "Active"

    async def test_update_problem(
        self,
        user_repo: SqlAlchemyUserRepository,
        problem_repo: SqlAlchemyProblemRepository,
    ) -> None:
        """Verify a problem can be updated."""
        user = User(telegram_id=444444)
        await user_repo.add(user)

        problem = Problem(user_id=user.id, title="Original Title")
        await problem_repo.add(problem)

        problem._title = "Updated Title"
        problem.add_step("New Step")
        await problem_repo.update(problem)

        retrieved = await problem_repo.get_by_id(problem.id)
        assert retrieved is not None
        assert retrieved.title == "Updated Title"
        assert retrieved.total_steps_count == 1

    async def test_delete_problem(
        self,
        user_repo: SqlAlchemyUserRepository,
        problem_repo: SqlAlchemyProblemRepository,
    ) -> None:
        """Verify a problem can be deleted."""
        user = User(telegram_id=666666)
        await user_repo.add(user)

        problem = Problem(user_id=user.id, title="To Delete")
        await problem_repo.add(problem)

        await problem_repo.delete(problem.id)
        result = await problem_repo.get_by_id(problem.id)
        assert result is None


class TestConversationContextRepository:
    """Integration tests for SqlAlchemyConversationContextRepository."""

    async def test_add_and_retrieve_context(
        self,
        user_repo: SqlAlchemyUserRepository,
        problem_repo: SqlAlchemyProblemRepository,
        context_repo: SqlAlchemyConversationContextRepository,
    ) -> None:
        """Verify conversation context can be stored and retrieved."""
        user = User(telegram_id=777777)
        await user_repo.add(user)

        problem = Problem(user_id=user.id, title="Context Test")
        await problem_repo.add(problem)

        ctx = ConversationContext(problem_id=problem.id)
        ctx.add_message(role="user", content="Hello")
        ctx.add_message(role="assistant", content="Hi!")
        await context_repo.add(ctx)

        retrieved = await context_repo.get_by_problem_id(problem.id)
        assert retrieved is not None
        assert len(retrieved.messages) == 2
        assert retrieved.messages[0]["content"] == "Hello"

    async def test_update_context(
        self,
        user_repo: SqlAlchemyUserRepository,
        problem_repo: SqlAlchemyProblemRepository,
        context_repo: SqlAlchemyConversationContextRepository,
    ) -> None:
        """Verify conversation context can be updated."""
        user = User(telegram_id=888888)
        await user_repo.add(user)

        problem = Problem(user_id=user.id, title="Update Context")
        await problem_repo.add(problem)

        ctx = ConversationContext(problem_id=problem.id)
        await context_repo.add(ctx)

        ctx.add_message(role="user", content="New message")
        ctx.summarize("Summary text")
        await context_repo.update(ctx)

        retrieved = await context_repo.get_by_problem_id(problem.id)
        assert retrieved is not None
        assert len(retrieved.messages) == 1
        assert retrieved.summary == "Summary text"
