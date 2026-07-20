"""Unit tests for application services with mocked dependencies."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from solver.application.services import ProblemService
from solver.application.dtos import (
    CreateProblemDTO,
    AIAnalysisRequestDTO,
    AIAnalysisResponseDTO,
    UpdateStepDTO,
)
from solver.domain.entities import User, Problem
from solver.domain.value_objects import (
    UserId,
    ProblemId,
    StepId,
    StepStatus,
    ProblemStatus,
)
from solver.domain.exceptions import ProblemNotFoundError, UserNotFoundError
from solver.domain.repositories import (
    UserRepository,
    ProblemRepository,
    ConversationContextRepository,
)
from solver.application.ai_service import AIAnalysisService


@pytest.fixture
def mock_user_repo():
    """Create a mock UserRepository."""
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def mock_problem_repo():
    """Create a mock ProblemRepository."""
    return AsyncMock(spec=ProblemRepository)


@pytest.fixture
def mock_context_repo():
    """Create a mock ConversationContextRepository."""
    return AsyncMock(spec=ConversationContextRepository)


@pytest.fixture
def mock_ai_service():
    """Create a mock AIAnalysisService."""
    return AsyncMock(spec=AIAnalysisService)


@pytest.fixture
def problem_service(mock_problem_repo, mock_user_repo, mock_context_repo, mock_ai_service):
    """Create a ProblemService with mocked dependencies."""
    return ProblemService(
        problem_repo=mock_problem_repo,
        user_repo=mock_user_repo,
        context_repo=mock_context_repo,
        ai_service=mock_ai_service,
    )


class TestCreateProblem:
    """Tests for problem creation."""

    async def test_create_problem_new_user(
        self, problem_service, mock_user_repo, mock_problem_repo
    ):
        """Verify problem creation also creates user if not exists."""
        mock_user_repo.get_by_telegram_id.return_value = None
        mock_user_repo.add.return_value = None

        dto = CreateProblemDTO(title="Test Problem", description="Description")
        result = await problem_service.create_problem(telegram_id=12345, dto=dto)

        assert result.title == "Test Problem"
        assert result.description == "Description"
        assert result.status == "draft"
        mock_user_repo.add.assert_called_once()
        mock_problem_repo.add.assert_called_once()

    async def test_create_problem_existing_user(
        self, problem_service, mock_user_repo, mock_problem_repo
    ):
        """Verify problem creation for existing user."""
        existing_user = User(telegram_id=12345)
        mock_user_repo.get_by_telegram_id.return_value = existing_user

        dto = CreateProblemDTO(title="Existing User Problem")
        result = await problem_service.create_problem(telegram_id=12345, dto=dto)

        assert result.title == "Existing User Problem"
        # User should NOT be created again
        mock_user_repo.add.assert_not_called()
        mock_problem_repo.add.assert_called_once()


class TestAnalyzeProblem:
    """Tests for AI analysis."""

    async def test_analyze_problem_success(
        self, problem_service, mock_user_repo, mock_problem_repo, mock_ai_service
    ):
        """Verify successful AI analysis flow."""
        user = User(telegram_id=12345)
        problem = Problem(user_id=user.id, title="Test")
        mock_user_repo.get_by_telegram_id.return_value = user
        mock_problem_repo.get_by_id.return_value = problem
        mock_ai_service.analyze.return_value = AIAnalysisResponseDTO(
            analysis="Analysis text",
            steps=["Step 1", "Step 2", "Step 3"],
            tokens_used=100,
        )

        result = await problem_service.analyze_problem(
            telegram_id=12345, problem_id=problem.id.value
        )

        assert result.total_steps == 3
        assert result.status == "active"
        mock_ai_service.analyze.assert_called_once()
        mock_problem_repo.update.assert_called()  # Called for start_analysis + after steps

    async def test_analyze_problem_not_found(
        self, problem_service, mock_user_repo, mock_problem_repo
    ):
        """Verify error when problem not found."""
        mock_user_repo.get_by_telegram_id.return_value = User(telegram_id=12345)
        mock_problem_repo.get_by_id.return_value = None

        with pytest.raises(ProblemNotFoundError):
            await problem_service.analyze_problem(
                telegram_id=12345, problem_id=uuid4()
            )

    async def test_analyze_problem_wrong_user(
        self, problem_service, mock_user_repo, mock_problem_repo
    ):
        """Verify error when problem belongs to different user."""
        user1 = User(telegram_id=11111)
        user2 = User(telegram_id=22222)
        problem = Problem(user_id=user2.id, title="Other's problem")

        mock_user_repo.get_by_telegram_id.return_value = user1
        mock_problem_repo.get_by_id.return_value = problem

        with pytest.raises(ProblemNotFoundError):
            await problem_service.analyze_problem(
                telegram_id=11111, problem_id=problem.id.value
            )


class TestListProblems:
    """Tests for problem listing."""

    async def test_list_problems_empty_for_new_user(
        self, problem_service, mock_user_repo
    ):
        """Verify empty list for new user."""
        mock_user_repo.get_by_telegram_id.return_value = None

        result = await problem_service.list_problems(telegram_id=99999)

        assert result == []

    async def test_list_active_problems(
        self, problem_service, mock_user_repo, mock_problem_repo
    ):
        """Verify active problems listing."""
        user = User(telegram_id=12345)
        mock_user_repo.get_by_telegram_id.return_value = user
        mock_problem_repo.get_active_by_user_id.return_value = [
            Problem(user_id=user.id, title="Active 1", status=ProblemStatus.ACTIVE),
            Problem(user_id=user.id, title="Active 2", status=ProblemStatus.ACTIVE),
        ]

        result = await problem_service.list_active_problems(telegram_id=12345)

        assert len(result) == 2


class TestUpdateStepStatus:
    """Tests for step status updates."""

    async def test_complete_step(
        self, problem_service, mock_user_repo, mock_problem_repo
    ):
        """Verify completing a step updates status."""
        user = User(telegram_id=12345)
        problem = Problem(user_id=user.id, title="Test", status=ProblemStatus.ACTIVE)
        step = problem.add_step("Complete me")

        mock_user_repo.get_by_telegram_id.return_value = user
        mock_problem_repo.get_by_id.return_value = problem

        result = await problem_service.update_step_status(
            telegram_id=12345,
            problem_id=problem.id.value,
            step_id=step.id.value,
            dto=UpdateStepDTO(status="completed"),
        )

        completed_step = result.steps[0]
        assert completed_step.status == "completed"

    async def test_complete_all_steps_resolves_problem(
        self, problem_service, mock_user_repo, mock_problem_repo
    ):
        """Verify completing all steps auto-resolves the problem."""
        user = User(telegram_id=12345)
        problem = Problem(user_id=user.id, title="Test", status=ProblemStatus.ACTIVE)
        step = problem.add_step("Only step")

        mock_user_repo.get_by_telegram_id.return_value = user
        mock_problem_repo.get_by_id.return_value = problem

        result = await problem_service.update_step_status(
            telegram_id=12345,
            problem_id=problem.id.value,
            step_id=step.id.value,
            dto=UpdateStepDTO(status="completed"),
        )

        assert result.status == "resolved"
        assert result.progress_percentage == 100.0
