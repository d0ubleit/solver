"""PromptTemplate entity — a reusable AI prompt for a problem category."""

from datetime import datetime, timezone as tz
from uuid import UUID, uuid4


class PromptTemplateId:
    """Strongly-typed identifier for a PromptTemplate."""

    __slots__ = ("_value",)

    def __init__(self, value: UUID) -> None:
        self._value = value

    @classmethod
    def generate(cls) -> "PromptTemplateId":
        return cls(uuid4())

    @property
    def value(self) -> UUID:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PromptTemplateId):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return str(self._value)


class PromptTemplate:
    """A reusable AI system prompt template for a specific problem category."""

    __slots__ = (
        "_id",
        "_category",
        "_title",
        "_system_prompt",
        "_usage_count",
        "_is_active",
        "_created_at",
        "_updated_at",
    )

    def __init__(
        self,
        category: str,
        title: str,
        system_prompt: str,
        id: PromptTemplateId | None = None,
        usage_count: int = 0,
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._id = id or PromptTemplateId.generate()
        self._category = category
        self._title = title
        self._system_prompt = system_prompt
        self._usage_count = usage_count
        self._is_active = is_active
        self._created_at = created_at or datetime.now(tz.utc)
        self._updated_at = updated_at or datetime.now(tz.utc)

    @property
    def id(self) -> PromptTemplateId:
        return self._id

    @property
    def category(self) -> str:
        return self._category

    @property
    def title(self) -> str:
        return self._title

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def usage_count(self) -> int:
        return self._usage_count

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def increment_usage(self) -> None:
        """Record that this template was used."""
        self._usage_count += 1
        self._updated_at = datetime.now(tz.utc)

    def deactivate(self) -> None:
        """Deactivate this template (e.g. poor feedback)."""
        self._is_active = False
        self._updated_at = datetime.now(tz.utc)
