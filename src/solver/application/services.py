"""Application services for problem management and AI orchestration."""

from typing import TYPE_CHECKING
from uuid import UUID

from solver.application.ai_service import AIAnalysisService
from solver.application.dtos import (
    AIAnalysisRequestDTO,
    CreateProblemDTO,
    ProblemResponseDTO,
    StepResponseDTO,
    UserResponseDTO,
    UpdateStepDTO,
)
from solver.domain.entities import Problem, User
from solver.domain.exceptions import (
    ProblemNotFoundError,
    UserNotFoundError,
    AIAnalysisError,
)
from solver.domain.repositories import (
    ProblemRepository,
    UserRepository,
    ConversationContextRepository,
)
from solver.domain.value_objects import (
    ProblemId,
    StepStatus,
)

if TYPE_CHECKING:
    from solver.application.prompt_service import PromptService


def _problem_to_response(problem: Problem) -> ProblemResponseDTO:
    """Map a Problem entity to a response DTO."""
    return ProblemResponseDTO(
        id=problem.id.value,
        user_id=problem.user_id.value,
        title=problem.title,
        description=problem.description,
        status=problem.status.value,
        priority=problem.priority.value,
        total_steps=problem.total_steps_count,
        completed_steps=problem.completed_steps_count,
        progress_percentage=round(problem.progress_percentage, 1),
        created_at=problem.created_at,
        updated_at=problem.updated_at,
        resolved_at=problem.resolved_at,
        steps=[
            StepResponseDTO(
                id=step.id.value,
                step_order=step.step_order,
                description=step.description,
                status=step.status.value,
                ai_suggestion=step.ai_suggestion,
                completed_at=step.completed_at,
                created_at=step.created_at,
            )
            for step in problem.steps
        ],
    )


def _user_to_response(user: User) -> UserResponseDTO:
    """Map a User entity to a response DTO."""
    return UserResponseDTO(
        id=user.id.value,
        telegram_id=user.telegram_id,
        username=user.username,
        timezone=user.timezone,
        proactive_level=user.proactive_level.value,
        proactive_enabled=user.proactive_enabled,
        created_at=user.created_at,
    )


class ProblemService:
    """Application service for managing problems and orchestrating AI analysis."""

    def __init__(
        self,
        problem_repo: ProblemRepository,
        user_repo: UserRepository,
        context_repo: ConversationContextRepository,
        ai_service: AIAnalysisService,
        prompt_service: "PromptService | None" = None,
    ) -> None:
        self._problem_repo = problem_repo
        self._user_repo = user_repo
        self._context_repo = context_repo
        self._ai_service = ai_service
        self._prompt_service = prompt_service

    async def create_problem(
        self, telegram_id: int, dto: CreateProblemDTO
    ) -> ProblemResponseDTO:
        """Create a new problem and trigger AI analysis."""
        # Get or create user
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id)
            await self._user_repo.add(user)

        # Create problem
        problem = Problem(
            user_id=user.id,
            title=dto.title,
            description=dto.description,
        )
        await self._problem_repo.add(problem)

        return _problem_to_response(problem)

    async def analyze_problem(
        self, telegram_id: int, problem_id: UUID
    ) -> ProblemResponseDTO:
        """Run AI analysis on a problem and generate solution steps."""
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(user_id=str(telegram_id))

        problem = await self._problem_repo.get_by_id(ProblemId(problem_id))
        if problem is None:
            raise ProblemNotFoundError(problem_id=str(problem_id))

        if problem.user_id != user.id:
            raise ProblemNotFoundError(problem_id=str(problem_id))

        # Mark as analyzing
        problem.start_analysis()
        await self._problem_repo.update(problem)

        # Get conversation context
        ctx = await self._context_repo.get_by_problem_id(problem.id)

        # Call AI with adapted prompt
        try:
            # Get best prompt for this problem
            adapted_prompt = ""
            if self._prompt_service:
                adapted_prompt = await self._prompt_service.get_prompt_for_problem(
                    problem_title=problem.title,
                    problem_description=problem.description,
                    base_prompt="",  # Will use AI service's default
                )

            result = await self._ai_service.analyze(
                AIAnalysisRequestDTO(
                    problem_title=problem.title,
                    problem_description=problem.description,
                    conversation_history=ctx.messages if ctx else [],
                ),
                system_prompt=adapted_prompt,
            )
        except Exception as e:
            raise AIAnalysisError(problem_id=str(problem.id), reason=str(e))

        # Add generated steps
        for step_desc in result.steps:
            problem.add_step(description=step_desc)

        problem.activate()
        await self._problem_repo.update(problem)

        return _problem_to_response(problem)

    async def get_problem(
        self, telegram_id: int, problem_id: UUID
    ) -> ProblemResponseDTO:
        """Retrieve a problem by ID."""
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(user_id=str(telegram_id))

        problem = await self._problem_repo.get_by_id(ProblemId(problem_id))
        if problem is None or problem.user_id != user.id:
            raise ProblemNotFoundError(problem_id=str(problem_id))

        return _problem_to_response(problem)

    async def list_problems(self, telegram_id: int) -> list[ProblemResponseDTO]:
        """List all problems for a user."""
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            return []

        problems = await self._problem_repo.get_by_user_id(user.id)
        return [_problem_to_response(p) for p in problems]

    async def list_active_problems(self, telegram_id: int) -> list[ProblemResponseDTO]:
        """List active (non-resolved) problems for a user."""
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            return []

        problems = await self._problem_repo.get_active_by_user_id(user.id)
        return [_problem_to_response(p) for p in problems]

    async def update_step_status(
        self, telegram_id: int, problem_id: UUID, step_id: UUID, dto: UpdateStepDTO
    ) -> ProblemResponseDTO:
        """Update the status of a step."""
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(user_id=str(telegram_id))

        problem = await self._problem_repo.get_by_id(ProblemId(problem_id))
        if problem is None or problem.user_id != user.id:
            raise ProblemNotFoundError(problem_id=str(problem_id))

        # Find and update the step
        target_step = None
        for step in problem.steps:
            if step.id.value == step_id:
                target_step = step
                break

        if target_step is None:
            raise ProblemNotFoundError(problem_id=str(step_id))

        new_status = StepStatus(dto.status)
        if new_status == StepStatus.COMPLETED:
            target_step.complete()
        elif new_status == StepStatus.IN_PROGRESS:
            target_step.start()
        elif new_status == StepStatus.SKIPPED:
            target_step.skip()

        # Check if all steps are completed
        if problem.progress_percentage >= 100.0:
            problem.resolve()

        await self._problem_repo.update(problem)
        return _problem_to_response(problem)

    async def resolve_problem(
        self, telegram_id: int, problem_id: UUID
    ) -> ProblemResponseDTO:
        """Resolve a problem."""
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(user_id=str(telegram_id))

        problem = await self._problem_repo.get_by_id(ProblemId(problem_id))
        if problem is None or problem.user_id != user.id:
            raise ProblemNotFoundError(problem_id=str(problem_id))

        problem.resolve()
        await self._problem_repo.update(problem)
        return _problem_to_response(problem)

    async def continue_session(
        self, telegram_id: int, problem_id: UUID, user_message: str
    ) -> dict:
        """Continue a conversation session for an existing problem.

        Returns:
            {"reply": str, "updated_steps": list[str] | None}
        """
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(user_id=str(telegram_id))

        problem = await self._problem_repo.get_by_id(ProblemId(problem_id))
        if problem is None or problem.user_id != user.id:
            raise ProblemNotFoundError(problem_id=str(problem_id))

        # Get or create conversation context
        ctx = await self._context_repo.get_by_problem_id(problem.id)
        if ctx is None:
            from solver.domain.entities import ConversationContext
            ctx = ConversationContext(problem_id=problem.id)
            await self._context_repo.add(ctx)

        # Build steps summary for AI context
        steps_summary = "\n".join(
            f"{s.step_order + 1}. [{s.status.value}] {s.description}"
            for s in problem.steps
        ) if problem.steps else "Шаги ещё не определены"

        # Add user message to context
        ctx.add_message(role="user", content=user_message)

        # Call AI
        try:
            result = await self._ai_service.continue_dialog(
                problem_title=problem.title,
                problem_description=problem.description,
                steps_summary=steps_summary,
                conversation_history=ctx.messages[:-1],  # exclude the one we just added
                user_message=user_message,
            )
        except Exception as e:
            from solver.domain.exceptions import AIAnalysisError
            raise AIAnalysisError(problem_id=str(problem.id), reason=str(e))

        # Add AI reply to context
        ctx.add_message(role="assistant", content=result.get("reply", ""))
        await self._context_repo.update(ctx)

        # Update steps if AI suggested changes
        updated_steps = result.get("updated_steps")
        if updated_steps and isinstance(updated_steps, list):
            # Replace all steps with AI-suggested ones
            problem._steps.clear()
            for desc in updated_steps:
                problem.add_step(description=str(desc))
            await self._problem_repo.update(problem)

        return {
            "reply": result.get("reply", "Понял. Продолжаем работу."),
            "updated_steps": updated_steps,
        }
