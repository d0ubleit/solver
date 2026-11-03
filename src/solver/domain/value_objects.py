"""Domain value objects: enums and typed identifiers."""

from enum import StrEnum
from uuid import UUID, uuid4


class ProblemStatus(StrEnum):
    """Status of a problem in its lifecycle."""

    DRAFT = "draft"
    ANALYZING = "analyzing"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    RESOLVED = "resolved"


class StepStatus(StrEnum):
    """Status of a solution step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class Priority(StrEnum):
    """Priority level of a problem."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProactiveLevel(StrEnum):
    """Level of proactive engagement for a user."""

    GENTLE = "gentle"
    MODERATE = "moderate"
    PERSISTENT = "persistent"


class ProblemId:
    """Strongly-typed identifier for a Problem."""

    __slots__ = ("_value",)

    def __init__(self, value: UUID) -> None:
        self._value = value

    @classmethod
    def generate(cls) -> "ProblemId":
        """Generate a new unique ProblemId."""
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> "ProblemId":
        """Create a ProblemId from a string representation."""
        try:
            return cls(UUID(value))
        except ValueError:
            raise ValueError(f"Invalid UUID string for ProblemId: {value}")

    @property
    def value(self) -> UUID:
        """Return the underlying UUID value."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProblemId):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"ProblemId({self._value})"


class StepId:
    """Strongly-typed identifier for a SolutionStep."""

    __slots__ = ("_value",)

    def __init__(self, value: UUID) -> None:
        self._value = value

    @classmethod
    def generate(cls) -> "StepId":
        """Generate a new unique StepId."""
        return cls(uuid4())

    @property
    def value(self) -> UUID:
        """Return the underlying UUID value."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StepId):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"StepId({self._value})"


class UserId:
    """Strongly-typed identifier for a User."""

    __slots__ = ("_value",)

    def __init__(self, value: UUID) -> None:
        self._value = value

    @classmethod
    def generate(cls) -> "UserId":
        """Generate a new unique UserId."""
        return cls(uuid4())

    @property
    def value(self) -> UUID:
        """Return the underlying UUID value."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UserId):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"UserId({self._value})"
