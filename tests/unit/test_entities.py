"""Unit tests for domain entities: Problem, SolutionStep, User, ConversationContext."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from solver.domain.value_objects import (
    ProblemStatus,
    StepStatus,
    Priority,
    ProactiveLevel,
    ProblemId,
    StepId,
    UserId,
)
from solver.domain.entities import (
    Problem,
    SolutionStep,
    User,
    ConversationContext,
)
from solver.domain.exceptions import (
    ProblemAlreadyResolvedError,
    StepNotPendingError,
    InvalidStepStatusTransitionError,
)


class TestUser:
    """Tests for User entity."""

    def test_create_user_with_minimal_data(self) -> None:
        """Verify user can be created with minimal required data."""
        telegram_id = 123456789
        user = User(telegram_id=telegram_id)

        assert user.telegram_id == telegram_id
        assert isinstance(user.id, UserId)
        assert user.proactive_level == ProactiveLevel.MODERATE
        assert user.proactive_enabled is True
        assert user.timezone == "UTC"
        assert isinstance(user.created_at, datetime)

    def test_create_user_with_full_data(self) -> None:
        """Verify user can be created with all fields specified."""
        uid = UserId.generate()
        telegram_id = 987654321
        user = User(
            id=uid,
            telegram_id=telegram_id,
            username="testuser",
            timezone="Europe/Moscow",
            proactive_level=ProactiveLevel.GENTLE,
            proactive_enabled=False,
        )

        assert user.id == uid
        assert user.telegram_id == telegram_id
        assert user.username == "testuser"
        assert user.timezone == "Europe/Moscow"
        assert user.proactive_level == ProactiveLevel.GENTLE
        assert user.proactive_enabled is False

    def test_enable_proactive(self) -> None:
        """Verify proactive mode can be enabled."""
        user = User(telegram_id=123)
        assert user.proactive_enabled is True
        # Disable first
        user.disable_proactive()
        assert user.proactive_enabled is False
        # Enable again
        user.enable_proactive()
        assert user.proactive_enabled is True

    def test_disable_proactive(self) -> None:
        """Verify proactive mode can be disabled."""
        user = User(telegram_id=123)
        user.disable_proactive()
        assert user.proactive_enabled is False

    def test_set_proactive_level(self) -> None:
        """Verify proactive level can be changed."""
        user = User(telegram_id=123)
        user.set_proactive_level(ProactiveLevel.PERSISTENT)
        assert user.proactive_level == ProactiveLevel.PERSISTENT


class TestProblem:
    """Tests for Problem aggregate root."""

    def test_create_problem_with_minimal_data(self) -> None:
        """Verify problem can be created with minimal required data."""
        user_id = UserId.generate()
        problem = Problem(user_id=user_id, title="Конфликт с коллегой")

        assert problem.title == "Конфликт с коллегой"
        assert problem.user_id == user_id
        assert isinstance(problem.id, ProblemId)
        assert problem.status == ProblemStatus.DRAFT
        assert problem.priority == Priority.MEDIUM
        assert problem.description == ""
        assert isinstance(problem.created_at, datetime)
        assert problem.steps == []

    def test_create_problem_with_full_data(self) -> None:
        """Verify problem can be created with all fields."""
        pid = ProblemId.generate()
        uid = UserId.generate()
        problem = Problem(
            id=pid,
            user_id=uid,
            title="Сложная проблема",
            description="Нужно разобраться с ипотекой",
            status=ProblemStatus.ACTIVE,
            priority=Priority.HIGH,
        )

        assert problem.id == pid
        assert problem.title == "Сложная проблема"
        assert problem.description == "Нужно разобраться с ипотекой"
        assert problem.status == ProblemStatus.ACTIVE
        assert problem.priority == Priority.HIGH

    def test_start_analysis_changes_status(self) -> None:
        """Verify starting analysis transitions status to ANALYZING."""
        problem = Problem(user_id=UserId.generate(), title="Test")
        assert problem.status == ProblemStatus.DRAFT

        problem.start_analysis()
        assert problem.status == ProblemStatus.ANALYZING

    def test_activate_changes_status(self) -> None:
        """Verify activating changes status to ACTIVE."""
        problem = Problem(
            user_id=UserId.generate(),
            title="Test",
            status=ProblemStatus.ANALYZING,
        )
        problem.activate()
        assert problem.status == ProblemStatus.ACTIVE

    def test_put_on_hold_changes_status(self) -> None:
        """Verify putting on hold changes status."""
        problem = Problem(
            user_id=UserId.generate(),
            title="Test",
            status=ProblemStatus.ACTIVE,
        )
        problem.put_on_hold()
        assert problem.status == ProblemStatus.ON_HOLD

    def test_resolve_changes_status_and_timestamp(self) -> None:
        """Verify resolving marks problem as resolved and sets timestamp."""
        problem = Problem(
            user_id=UserId.generate(),
            title="Test",
            status=ProblemStatus.ACTIVE,
        )
        assert problem.resolved_at is None

        problem.resolve()
        assert problem.status == ProblemStatus.RESOLVED
        assert isinstance(problem.resolved_at, datetime)

    def test_cannot_resolve_already_resolved_problem(self) -> None:
        """Verify resolving an already resolved problem raises error."""
        problem = Problem(
            user_id=UserId.generate(),
            title="Test",
            status=ProblemStatus.RESOLVED,
        )
        with pytest.raises(ProblemAlreadyResolvedError):
            problem.resolve()

    def test_add_step_appends_to_steps_list(self) -> None:
        """Verify adding a step appends to the problem's steps."""
        problem = Problem(user_id=UserId.generate(), title="Test")
        assert len(problem.steps) == 0

        step = problem.add_step("Первый шаг")
        assert len(problem.steps) == 1
        assert problem.steps[0] == step
        assert step.description == "Первый шаг"
        assert step.step_order == 0

    def test_add_multiple_steps_increases_order(self) -> None:
        """Verify steps get sequential order numbers."""
        problem = Problem(user_id=UserId.generate(), title="Test")
        step1 = problem.add_step("Шаг 1")
        step2 = problem.add_step("Шаг 2")
        step3 = problem.add_step("Шаг 3")

        assert step1.step_order == 0
        assert step2.step_order == 1
        assert step3.step_order == 2

    def test_completed_steps_count(self) -> None:
        """Verify completed steps count is correct."""
        problem = Problem(user_id=UserId.generate(), title="Test")
        s1 = problem.add_step("Шаг 1")
        s2 = problem.add_step("Шаг 2")
        s3 = problem.add_step("Шаг 3")

        assert problem.completed_steps_count == 0

        s1.complete()
        assert problem.completed_steps_count == 1

        s2.complete()
        assert problem.completed_steps_count == 2

    def test_total_steps_count(self) -> None:
        """Verify total steps count is correct."""
        problem = Problem(user_id=UserId.generate(), title="Test")
        assert problem.total_steps_count == 0

        problem.add_step("Шаг 1")
        problem.add_step("Шаг 2")
        assert problem.total_steps_count == 2

    def test_progress_percentage(self) -> None:
        """Verify progress calculation is correct."""
        problem = Problem(user_id=UserId.generate(), title="Test")
        assert problem.progress_percentage == 0.0

        step1 = problem.add_step("Шаг 1")
        step2 = problem.add_step("Шаг 2")

        step1.complete()
        assert problem.progress_percentage == 50.0

        step2.complete()
        assert problem.progress_percentage == 100.0

    def test_progress_percentage_empty_steps(self) -> None:
        """Verify progress is 0 when there are no steps."""
        problem = Problem(user_id=UserId.generate(), title="Test")
        assert problem.progress_percentage == 0.0


class TestSolutionStep:
    """Tests for SolutionStep entity."""

    def test_create_step(self) -> None:
        """Verify step can be created."""
        problem_id = ProblemId.generate()
        step = SolutionStep(
            problem_id=problem_id,
            step_order=0,
            description="Поговорить с коллегой",
        )

        assert step.problem_id == problem_id
        assert step.step_order == 0
        assert step.description == "Поговорить с коллегой"
        assert step.status == StepStatus.PENDING
        assert step.ai_suggestion == ""
        assert step.completed_at is None
        assert isinstance(step.id, StepId)

    def test_complete_step(self) -> None:
        """Verify completing a step updates status and timestamp."""
        step = SolutionStep(
            problem_id=ProblemId.generate(),
            step_order=0,
            description="Test",
        )
        assert step.status == StepStatus.PENDING
        assert step.completed_at is None

        step.complete()
        assert step.status == StepStatus.COMPLETED
        assert isinstance(step.completed_at, datetime)

    def test_cannot_complete_already_completed_step(self) -> None:
        """Verify completing an already completed step raises error."""
        step = SolutionStep(
            problem_id=ProblemId.generate(),
            step_order=0,
            description="Test",
        )
        step.complete()
        with pytest.raises(StepNotPendingError):
            step.complete()

    def test_start_step(self) -> None:
        """Verify starting a step updates status."""
        step = SolutionStep(
            problem_id=ProblemId.generate(),
            step_order=0,
            description="Test",
        )
        step.start()
        assert step.status == StepStatus.IN_PROGRESS

    def test_skip_step(self) -> None:
        """Verify skipping a step updates status."""
        step = SolutionStep(
            problem_id=ProblemId.generate(),
            step_order=0,
            description="Test",
        )
        step.skip()
        assert step.status == StepStatus.SKIPPED

    def test_set_ai_suggestion(self) -> None:
        """Verify setting AI suggestion."""
        step = SolutionStep(
            problem_id=ProblemId.generate(),
            step_order=0,
            description="Test",
        )
        suggestion = "Попробуй использовать технику 'Я-высказываний'"
        step.set_ai_suggestion(suggestion)
        assert step.ai_suggestion == suggestion


class TestConversationContext:
    """Tests for ConversationContext entity."""

    def test_create_context(self) -> None:
        """Verify conversation context can be created."""
        problem_id = ProblemId.generate()
        ctx = ConversationContext(problem_id=problem_id)

        assert ctx.problem_id == problem_id
        assert ctx.messages == []
        assert ctx.summary == ""
        assert ctx.tokens_used == 0
        assert isinstance(ctx.created_at, datetime)

    def test_add_message(self) -> None:
        """Verify adding a message to conversation context."""
        ctx = ConversationContext(problem_id=ProblemId.generate())
        ctx.add_message(role="user", content="Привет")
        ctx.add_message(role="assistant", content="Здравствуйте!")

        assert len(ctx.messages) == 2
        assert ctx.messages[0] == {"role": "user", "content": "Привет"}
        assert ctx.messages[1] == {"role": "assistant", "content": "Здравствуйте!"}

    def test_add_message_updates_tokens(self) -> None:
        """Verify adding messages with token count updates total."""
        ctx = ConversationContext(problem_id=ProblemId.generate())
        ctx.add_message(role="user", content="Hello", tokens=10)
        ctx.add_message(role="assistant", content="Hi there!", tokens=15)

        assert ctx.tokens_used == 25

    def test_summarize_updates_summary(self) -> None:
        """Verify summarize stores summary text."""
        ctx = ConversationContext(problem_id=ProblemId.generate())
        ctx.add_message(role="user", content="У меня проблема с коллегой")
        ctx.add_message(role="assistant", content="Расскажите подробнее")

        ctx.summarize("Пользователь описал рабочий конфликт, требуется анализ.")
        assert ctx.summary == "Пользователь описал рабочий конфликт, требуется анализ."
