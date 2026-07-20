"""Unit tests for the proactive notification scheduler."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from solver.infrastructure.scheduler import ProactiveScheduler
from solver.domain.repositories import (
    UserRepository,
    ProblemRepository,
    ConversationContextRepository,
)
from solver.application.ai_service import AIAnalysisService


@pytest.fixture
def mock_user_repo():
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def mock_problem_repo():
    return AsyncMock(spec=ProblemRepository)


@pytest.fixture
def mock_context_repo():
    return AsyncMock(spec=ConversationContextRepository)


@pytest.fixture
def mock_ai_service():
    return AsyncMock(spec=AIAnalysisService)


@pytest.fixture
def mock_notification_sender():
    return AsyncMock()


@pytest.fixture
def scheduler(
    mock_user_repo,
    mock_problem_repo,
    mock_context_repo,
    mock_ai_service,
    mock_notification_sender,
):
    return ProactiveScheduler(
        user_repo=mock_user_repo,
        problem_repo=mock_problem_repo,
        context_repo=mock_context_repo,
        ai_service=mock_ai_service,
        notification_sender=mock_notification_sender,
        check_interval_minutes=60,
    )


class TestProactiveScheduler:
    """Tests for ProactiveScheduler."""

    def test_scheduler_initialization(self, scheduler):
        """Verify scheduler initializes in stopped state."""
        assert scheduler._is_running is False

    @pytest.mark.asyncio
    async def test_start_sets_running_flag(self, scheduler):
        """Verify starting the scheduler sets the running flag."""
        scheduler.start()
        assert scheduler._is_running is True
        scheduler.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running_flag(self, scheduler):
        """Verify stopping the scheduler clears the running flag."""
        scheduler.start()
        scheduler.stop()
        assert scheduler._is_running is False

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self, scheduler):
        """Verify starting twice doesn't cause issues."""
        scheduler.start()
        scheduler.start()  # Should be idempotent
        assert scheduler._is_running is True
        scheduler.stop()

    async def test_schedule_followup(
        self, scheduler, mock_ai_service, mock_notification_sender
    ):
        """Verify a follow-up can be scheduled for a problem."""
        scheduler.start()

        mock_ai_service.check_in.return_value = "How is it going?"

        await scheduler.schedule_problem_followup(
            telegram_id=12345,
            problem_title="Test Problem",
            steps_status=[{"description": "Step 1", "status": "pending"}],
            conversation_history=[],
            delay_hours=24,
        )

        # Verify job was added
        assert scheduler._scheduler.get_jobs()

        scheduler.stop()

    async def test_cancel_followup(self, scheduler):
        """Verify a follow-up can be cancelled."""
        scheduler.start()

        await scheduler.schedule_problem_followup(
            telegram_id=12345,
            problem_title="Cancel Me",
            steps_status=[],
            conversation_history=[],
            delay_hours=24,
        )

        job_count_before = len(scheduler._scheduler.get_jobs())
        scheduler.cancel_problem_followup(telegram_id=12345, problem_title="Cancel Me")
        job_count_after = len(scheduler._scheduler.get_jobs())

        assert job_count_after == job_count_before - 1

        scheduler.stop()
