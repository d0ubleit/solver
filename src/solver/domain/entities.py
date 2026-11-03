"""Domain entities: Problem, SolutionStep, User, ConversationContext."""

from datetime import datetime
from datetime import timezone as tz
from uuid import uuid4

from solver.domain.exceptions import (
    ProblemAlreadyResolvedError,
    StepNotPendingError,
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


class User:
    """User entity representing a Telegram bot user."""

    __slots__ = (
        "_id",
        "_telegram_id",
        "_username",
        "_timezone",
        "_proactive_level",
        "_proactive_enabled",
        "_created_at",
        "_updated_at",
    )

    def __init__(
        self,
        telegram_id: int,
        id: UserId | None = None,
        username: str = "",
        timezone: str = "UTC",
        proactive_level: ProactiveLevel = ProactiveLevel.MODERATE,
        proactive_enabled: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._id = id or UserId.generate()
        self._telegram_id = telegram_id
        self._username = username
        self._timezone = timezone
        self._proactive_level = proactive_level
        self._proactive_enabled = proactive_enabled
        self._created_at = created_at or datetime.now(tz.utc)
        self._updated_at = updated_at or datetime.now(tz.utc)

    @property
    def id(self) -> UserId:
        return self._id

    @property
    def telegram_id(self) -> int:
        return self._telegram_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def timezone(self) -> str:
        return self._timezone

    @property
    def proactive_level(self) -> ProactiveLevel:
        return self._proactive_level

    @property
    def proactive_enabled(self) -> bool:
        return self._proactive_enabled

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def enable_proactive(self) -> None:
        """Enable proactive notifications."""
        self._proactive_enabled = True
        self._updated_at = datetime.now(tz.utc)

    def disable_proactive(self) -> None:
        """Disable proactive notifications."""
        self._proactive_enabled = False
        self._updated_at = datetime.now(tz.utc)

    def set_proactive_level(self, level: ProactiveLevel) -> None:
        """Set the proactive engagement level."""
        self._proactive_level = level
        self._updated_at = datetime.now(tz.utc)


class SolutionStep:
    """An individual action step within a problem's solution plan."""

    __slots__ = (
        "_id",
        "_problem_id",
        "_step_order",
        "_description",
        "_status",
        "_ai_suggestion",
        "_completed_at",
        "_created_at",
    )

    def __init__(
        self,
        problem_id: ProblemId,
        step_order: int,
        description: str,
        id: StepId | None = None,
        status: StepStatus = StepStatus.PENDING,
        ai_suggestion: str = "",
        completed_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self._id = id or StepId.generate()
        self._problem_id = problem_id
        self._step_order = step_order
        self._description = description
        self._status = status
        self._ai_suggestion = ai_suggestion
        self._completed_at = completed_at
        self._created_at = created_at or datetime.now(tz.utc)

    @property
    def id(self) -> StepId:
        return self._id

    @property
    def problem_id(self) -> ProblemId:
        return self._problem_id

    @property
    def step_order(self) -> int:
        return self._step_order

    @property
    def description(self) -> str:
        return self._description

    @property
    def status(self) -> StepStatus:
        return self._status

    @property
    def ai_suggestion(self) -> str:
        return self._ai_suggestion

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def complete(self) -> None:
        """Mark this step as completed."""
        if self._status == StepStatus.COMPLETED:
            raise StepNotPendingError(
                step_id=str(self._id), current_status=self._status.value
            )
        self._status = StepStatus.COMPLETED
        self._completed_at = datetime.now(tz.utc)

    def start(self) -> None:
        """Mark this step as in progress."""
        self._status = StepStatus.IN_PROGRESS

    def skip(self) -> None:
        """Mark this step as skipped."""
        self._status = StepStatus.SKIPPED

    def set_ai_suggestion(self, suggestion: str) -> None:
        """Set or update the AI-generated suggestion for this step."""
        self._ai_suggestion = suggestion

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SolutionStep):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)


class Problem:
    """Aggregate root representing a user's problem to solve."""

    __slots__ = (
        "_id",
        "_user_id",
        "_title",
        "_description",
        "_status",
        "_priority",
        "_steps",
        "_created_at",
        "_updated_at",
        "_resolved_at",
    )

    def __init__(
        self,
        user_id: UserId,
        title: str,
        id: ProblemId | None = None,
        description: str = "",
        status: ProblemStatus = ProblemStatus.DRAFT,
        priority: Priority = Priority.MEDIUM,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        resolved_at: datetime | None = None,
    ) -> None:
        self._id = id or ProblemId.generate()
        self._user_id = user_id
        self._title = title
        self._description = description
        self._status = status
        self._priority = priority
        self._steps: list[SolutionStep] = []
        self._created_at = created_at or datetime.now(tz.utc)
        self._updated_at = updated_at or datetime.now(tz.utc)
        self._resolved_at = resolved_at

    @property
    def id(self) -> ProblemId:
        return self._id

    @property
    def user_id(self) -> UserId:
        return self._user_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def status(self) -> ProblemStatus:
        return self._status

    @property
    def priority(self) -> Priority:
        return self._priority

    @property
    def steps(self) -> list[SolutionStep]:
        return self._steps.copy()

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def resolved_at(self) -> datetime | None:
        return self._resolved_at

    @property
    def completed_steps_count(self) -> int:
        """Return the number of completed steps."""
        return sum(1 for step in self._steps if step.status == StepStatus.COMPLETED)

    @property
    def total_steps_count(self) -> int:
        """Return the total number of steps."""
        return len(self._steps)

    @property
    def progress_percentage(self) -> float:
        """Return the progress as a percentage (0-100)."""
        if not self._steps:
            return 0.0
        return (self.completed_steps_count / self.total_steps_count) * 100.0

    def start_analysis(self) -> None:
        """Transition the problem to ANALYZING status."""
        self._status = ProblemStatus.ANALYZING
        self._updated_at = datetime.now(tz.utc)

    def activate(self) -> None:
        """Transition the problem to ACTIVE status."""
        self._status = ProblemStatus.ACTIVE
        self._updated_at = datetime.now(tz.utc)

    def put_on_hold(self) -> None:
        """Transition the problem to ON_HOLD status."""
        self._status = ProblemStatus.ON_HOLD
        self._updated_at = datetime.now(tz.utc)

    def resolve(self) -> None:
        """Mark the problem as RESOLVED."""
        if self._status == ProblemStatus.RESOLVED:
            raise ProblemAlreadyResolvedError(problem_id=str(self._id))
        self._status = ProblemStatus.RESOLVED
        self._resolved_at = datetime.now(tz.utc)
        self._updated_at = datetime.now(tz.utc)

    def add_step(self, description: str, ai_suggestion: str = "") -> SolutionStep:
        """Add a new solution step to this problem."""
        step = SolutionStep(
            problem_id=self._id,
            step_order=len(self._steps),
            description=description,
            ai_suggestion=ai_suggestion,
        )
        self._steps.append(step)
        self._updated_at = datetime.now(tz.utc)
        return step

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Problem):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)


class ConversationContext:
    """Stores conversation history and context for a problem's AI interactions."""

    __slots__ = (
        "_id",
        "_problem_id",
        "_messages",
        "_summary",
        "_tokens_used",
        "_created_at",
        "_updated_at",
        "_last_activity_at",
    )

    def __init__(
        self,
        problem_id: ProblemId,
        id: UserId | None = None,
        messages: list[dict[str, str]] | None = None,
        summary: str = "",
        tokens_used: int = 0,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        last_activity_at: datetime | None = None,
    ) -> None:
        self._id = id or UserId(uuid4())
        self._problem_id = problem_id
        self._messages = messages or []
        self._summary = summary
        self._tokens_used = tokens_used
        self._created_at = created_at or datetime.now(tz.utc)
        self._updated_at = updated_at or datetime.now(tz.utc)
        self._last_activity_at = last_activity_at or datetime.now(tz.utc)

    @property
    def problem_id(self) -> ProblemId:
        return self._problem_id

    @property
    def messages(self) -> list[dict[str, str]]:
        return self._messages.copy()

    @property
    def summary(self) -> str:
        return self._summary

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def last_activity_at(self) -> datetime:
        return self._last_activity_at

    def add_message(self, role: str, content: str, tokens: int = 0) -> None:
        """Add a message to the conversation history."""
        self._messages.append({"role": role, "content": content})
        self._tokens_used += tokens
        now = datetime.now(tz.utc)
        self._updated_at = now
        self._last_activity_at = now

    def summarize(self, summary: str) -> None:
        """Store a summary of the conversation."""
        self._summary = summary
        now = datetime.now(tz.utc)
        self._updated_at = now
        self._last_activity_at = now

    def touch_activity(self) -> None:
        """Update the last activity timestamp (e.g. when user views the problem)."""
        self._last_activity_at = datetime.now(tz.utc)
