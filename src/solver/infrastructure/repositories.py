"""SQLAlchemy repository implementations for domain repository interfaces."""

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone as tz
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solver.domain.entities import (
    ConversationContext,
    Problem,
    SolutionStep,
    User,
)
from solver.domain.exceptions import ProblemNotFoundError, UserNotFoundError
from solver.domain.repositories import (
    ConversationContextRepository,
    ProblemRepository,
    UserRepository,
)
from solver.domain.value_objects import (
    Priority,
    ProactiveLevel,
    ProblemId,
    ProblemStatus,
    StepId,
    StepStatus,
    UserId,
)
from solver.infrastructure.models import (
    ConversationContextModel,
    ProblemModel,
    StepModel,
    UserModel,
)


def _user_to_entity(model: UserModel) -> User:
    """Map a UserModel to a User domain entity."""
    return User(
        id=UserId(UUID(model.id)),
        telegram_id=model.telegram_id,
        username=model.username or "",
        timezone=model.timezone or "UTC",
        proactive_level=ProactiveLevel(model.proactive_level),
        proactive_enabled=model.proactive_enabled,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _step_to_entity(model: StepModel) -> SolutionStep:
    """Map a StepModel to a SolutionStep domain entity."""
    return SolutionStep(
        id=StepId(UUID(model.id)),
        problem_id=ProblemId(UUID(model.problem_id)),
        step_order=model.step_order,
        description=model.description,
        status=StepStatus(model.status),
        ai_suggestion=model.ai_suggestion or "",
        completed_at=model.completed_at,
        created_at=model.created_at,
    )


def _problem_to_entity(model: ProblemModel) -> Problem:
    """Map a ProblemModel to a Problem domain entity, including its steps."""
    problem = Problem(
        id=ProblemId(UUID(model.id)),
        user_id=UserId(UUID(model.user_id)),
        title=model.title,
        description=model.description or "",
        status=ProblemStatus(model.status),
        priority=Priority(model.priority),
        created_at=model.created_at,
        updated_at=model.updated_at,
        resolved_at=model.resolved_at,
    )
    # Reconstruct steps in correct order
    for step_model in sorted(model.steps, key=lambda s: s.step_order):
        step = _step_to_entity(step_model)
        problem._steps.append(step)
    return problem


def _context_to_entity(model: ConversationContextModel) -> ConversationContext:
    """Map a ConversationContextModel to a ConversationContext domain entity."""
    return ConversationContext(
        id=UserId(UUID(model.id)),
        problem_id=ProblemId(UUID(model.problem_id)),
        messages=list(model.messages) if model.messages else [],
        summary=model.summary or "",
        tokens_used=model.tokens_used or 0,
        created_at=model.created_at,
        updated_at=model.updated_at,
        last_activity_at=model.last_activity_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        model = UserModel(
            id=str(user.id),
            telegram_id=user.telegram_id,
            username=user.username,
            timezone=user.timezone,
            proactive_level=user.proactive_level.value,
            proactive_enabled=user.proactive_enabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        await self._session.commit()
        return user

    async def get_by_id(self, user_id: UserId) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == str(user_id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _user_to_entity(model)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.telegram_id == telegram_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _user_to_entity(model)

    async def update(self, user: User) -> User:
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == str(user.id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise UserNotFoundError(user_id=str(user.id))

        model.username = user.username
        model.timezone = user.timezone
        model.proactive_level = user.proactive_level.value
        model.proactive_enabled = user.proactive_enabled
        model.updated_at = datetime.now(tz.utc)
        await self._session.commit()
        return user


class SqlAlchemyProblemRepository(ProblemRepository):
    """SQLAlchemy implementation of ProblemRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, problem: Problem) -> Problem:
        model = ProblemModel(
            id=str(problem.id),
            user_id=str(problem.user_id),
            title=problem.title,
            description=problem.description,
            status=problem.status.value,
            priority=problem.priority.value,
            created_at=problem.created_at,
            updated_at=problem.updated_at,
            resolved_at=problem.resolved_at,
        )
        # Add steps
        for step in problem.steps:
            step_model = StepModel(
                id=str(step.id),
                problem_id=str(step.problem_id),
                step_order=step.step_order,
                description=step.description,
                status=step.status.value,
                ai_suggestion=step.ai_suggestion,
                completed_at=step.completed_at,
                created_at=step.created_at,
            )
            model.steps.append(step_model)

        self._session.add(model)
        await self._session.commit()
        return problem

    async def get_by_id(self, problem_id: ProblemId) -> Problem | None:
        result = await self._session.execute(
            select(ProblemModel).where(ProblemModel.id == str(problem_id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _problem_to_entity(model)

    async def get_by_user_id(self, user_id: UserId) -> Sequence[Problem]:
        result = await self._session.execute(
            select(ProblemModel)
            .where(ProblemModel.user_id == str(user_id))
            .order_by(ProblemModel.created_at.desc())
        )
        models = result.scalars().all()
        return [_problem_to_entity(m) for m in models]

    async def get_active_by_user_id(self, user_id: UserId) -> Sequence[Problem]:
        result = await self._session.execute(
            select(ProblemModel)
            .where(
                ProblemModel.user_id == str(user_id),
                ProblemModel.status != ProblemStatus.RESOLVED.value,
            )
            .order_by(ProblemModel.created_at.desc())
        )
        models = result.scalars().all()
        return [_problem_to_entity(m) for m in models]

    async def update(self, problem: Problem) -> Problem:
        result = await self._session.execute(
            select(ProblemModel).where(ProblemModel.id == str(problem.id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ProblemNotFoundError(problem_id=str(problem.id))

        model.title = problem.title
        model.description = problem.description
        model.status = problem.status.value
        model.priority = problem.priority.value
        model.resolved_at = problem.resolved_at
        model.updated_at = datetime.now(tz.utc)

        # Update steps: remove deleted, update existing, add new
        existing_step_ids = {StepId(UUID(s.id)) for s in model.steps}
        new_step_ids = {s.id for s in problem.steps}

        # Remove steps no longer in domain
        for step_model in model.steps[:]:
            if StepId(UUID(step_model.id)) not in new_step_ids:
                model.steps.remove(step_model)

        # Update or add steps
        for step in problem.steps:
            if step.id in existing_step_ids:
                # Update existing
                for step_model in model.steps:
                    if UUID(step_model.id) == step.id.value:
                        step_model.description = step.description
                        step_model.status = step.status.value
                        step_model.ai_suggestion = step.ai_suggestion
                        step_model.completed_at = step.completed_at
                        step_model.step_order = step.step_order
            else:
                # Add new
                step_model = StepModel(
                    id=str(step.id),
                    problem_id=str(step.problem_id),
                    step_order=step.step_order,
                    description=step.description,
                    status=step.status.value,
                    ai_suggestion=step.ai_suggestion,
                    completed_at=step.completed_at,
                    created_at=step.created_at,
                )
                model.steps.append(step_model)

        await self._session.commit()
        return problem

    async def delete(self, problem_id: ProblemId) -> None:
        result = await self._session.execute(
            select(ProblemModel).where(ProblemModel.id == str(problem_id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ProblemNotFoundError(problem_id=str(problem_id))
        await self._session.delete(model)
        await self._session.commit()


class SqlAlchemyConversationContextRepository(ConversationContextRepository):
    """SQLAlchemy implementation of ConversationContextRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, context: ConversationContext) -> ConversationContext:
        model = ConversationContextModel(
            id=str(context._id),
            problem_id=str(context.problem_id),
            messages=context.messages,
            summary=context.summary,
            tokens_used=context.tokens_used,
            last_activity_at=context.last_activity_at,
            created_at=context.created_at,
            updated_at=context._updated_at,
        )
        self._session.add(model)
        await self._session.commit()
        return context

    async def get_by_problem_id(
        self, problem_id: ProblemId
    ) -> ConversationContext | None:
        result = await self._session.execute(
            select(ConversationContextModel).where(
                ConversationContextModel.problem_id == str(problem_id)
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _context_to_entity(model)

    async def update(self, context: ConversationContext) -> ConversationContext:
        result = await self._session.execute(
            select(ConversationContextModel).where(
                ConversationContextModel.id == str(context._id)
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            # If not found, try to add
            return await self.add(context)

        model.messages = context.messages
        model.summary = context.summary
        model.tokens_used = context.tokens_used
        model.last_activity_at = context.last_activity_at
        model.updated_at = datetime.now(tz.utc)
        await self._session.commit()
        return context


class SqlAlchemyPromptTemplateRepository:
    """SQLAlchemy implementation of PromptTemplateRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, template):
        from solver.infrastructure.models import PromptTemplateModel

        model = PromptTemplateModel(
            id=str(template.id),
            category=template.category,
            title=template.title,
            system_prompt=template.system_prompt,
            usage_count=template.usage_count,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template._updated_at,
        )
        self._session.add(model)
        await self._session.commit()
        return template

    async def get_by_category(self, category: str):
        from uuid import UUID

        from solver.domain.prompts import PromptTemplate, PromptTemplateId
        from solver.infrastructure.models import PromptTemplateModel

        result = await self._session.execute(
            select(PromptTemplateModel).where(
                PromptTemplateModel.category == category,
                PromptTemplateModel.is_active.is_(True),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return PromptTemplate(
            id=PromptTemplateId(UUID(model.id)),
            category=model.category,
            title=model.title,
            system_prompt=model.system_prompt,
            usage_count=model.usage_count or 0,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_active(self) -> list:
        from uuid import UUID

        from solver.domain.prompts import PromptTemplate, PromptTemplateId
        from solver.infrastructure.models import PromptTemplateModel

        result = await self._session.execute(
            select(PromptTemplateModel).where(PromptTemplateModel.is_active.is_(True))
        )
        models = result.scalars().all()
        return [
            PromptTemplate(
                id=PromptTemplateId(UUID(m.id)),
                category=m.category,
                title=m.title,
                system_prompt=m.system_prompt,
                usage_count=m.usage_count or 0,
                is_active=m.is_active,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in models
        ]

    async def update(self, template):
        from solver.infrastructure.models import PromptTemplateModel

        result = await self._session.execute(
            select(PromptTemplateModel).where(PromptTemplateModel.id == str(template.id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            return await self.add(template)

        model.usage_count = template.usage_count
        model.is_active = template.is_active
        model.system_prompt = template.system_prompt
        model.updated_at = datetime.now(tz.utc)
        await self._session.commit()
        return template
