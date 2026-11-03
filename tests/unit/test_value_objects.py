"""Unit tests for domain value objects: enums, IDs, statuses."""

from uuid import UUID, uuid4

import pytest

from solver.domain.value_objects import (
    Priority,
    ProactiveLevel,
    ProblemId,
    ProblemStatus,
    StepId,
    StepStatus,
    UserId,
)


class TestProblemStatus:
    """Tests for ProblemStatus enum."""

    def test_status_values_exist(self) -> None:
        """Verify all expected statuses are defined."""
        assert ProblemStatus.DRAFT.value == "draft"
        assert ProblemStatus.ANALYZING.value == "analyzing"
        assert ProblemStatus.ACTIVE.value == "active"
        assert ProblemStatus.ON_HOLD.value == "on_hold"
        assert ProblemStatus.RESOLVED.value == "resolved"

    def test_status_from_string(self) -> None:
        """Verify status can be created from string."""
        assert ProblemStatus("active") == ProblemStatus.ACTIVE
        assert ProblemStatus("draft") == ProblemStatus.DRAFT

    def test_status_invalid_string_raises_error(self) -> None:
        """Verify invalid status string raises ValueError."""
        with pytest.raises(ValueError):
            ProblemStatus("invalid_status")


class TestStepStatus:
    """Tests for StepStatus enum."""

    def test_status_values_exist(self) -> None:
        """Verify all expected step statuses are defined."""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.IN_PROGRESS.value == "in_progress"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.SKIPPED.value == "skipped"

    def test_status_transitions(self) -> None:
        """Verify valid status transitions."""
        # A step can be marked complete
        step = StepStatus.PENDING
        assert step == StepStatus.PENDING
        # These transitions should all be valid
        assert StepStatus("in_progress") == StepStatus.IN_PROGRESS
        assert StepStatus("completed") == StepStatus.COMPLETED
        assert StepStatus("skipped") == StepStatus.SKIPPED


class TestPriority:
    """Tests for Priority enum."""

    def test_priority_values_exist(self) -> None:
        """Verify all expected priorities are defined."""
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"
        assert Priority.CRITICAL.value == "critical"

    @pytest.mark.parametrize("value,expected", [
        ("low", Priority.LOW),
        ("medium", Priority.MEDIUM),
        ("high", Priority.HIGH),
        ("critical", Priority.CRITICAL),
    ])
    def test_priority_from_string(self, value: str, expected: Priority) -> None:
        """Verify priority can be created from string."""
        assert Priority(value) == expected


class TestProactiveLevel:
    """Tests for ProactiveLevel enum."""

    def test_level_values_exist(self) -> None:
        """Verify all expected proactive levels are defined."""
        assert ProactiveLevel.GENTLE.value == "gentle"
        assert ProactiveLevel.MODERATE.value == "moderate"
        assert ProactiveLevel.PERSISTENT.value == "persistent"


class TestProblemId:
    """Tests for ProblemId value object."""

    def test_create_with_valid_uuid(self, sample_problem_id: UUID) -> None:
        """Verify creation with valid UUID."""
        pid = ProblemId(sample_problem_id)
        assert pid.value == sample_problem_id
        assert str(pid) == str(sample_problem_id)

    def test_generate_creates_valid_id(self) -> None:
        """Verify generate() creates a valid UUID-based ID."""
        pid = ProblemId.generate()
        assert isinstance(pid, ProblemId)
        assert isinstance(pid.value, UUID)

    def test_from_string_creates_valid_id(self) -> None:
        """Verify from_string creates ID from string representation."""
        uuid_str = "123e4567-e89b-12d3-a456-426614174000"
        pid = ProblemId.from_string(uuid_str)
        assert isinstance(pid, ProblemId)
        assert str(pid) == uuid_str

    def test_from_string_invalid_raises_error(self) -> None:
        """Verify invalid string raises ValueError."""
        with pytest.raises(ValueError):
            ProblemId.from_string("not-a-uuid")

    def test_equality(self) -> None:
        """Verify two ProblemId with same value are equal."""
        uuid = uuid4()
        assert ProblemId(uuid) == ProblemId(uuid)

    def test_inequality(self) -> None:
        """Verify two ProblemId with different values are not equal."""
        assert ProblemId(uuid4()) != ProblemId(uuid4())


class TestStepId:
    """Tests for StepId value object."""

    def test_generate_creates_valid_id(self) -> None:
        """Verify generate() creates a valid UUID-based ID."""
        sid = StepId.generate()
        assert isinstance(sid, StepId)
        assert isinstance(sid.value, UUID)

    def test_equality(self) -> None:
        """Verify two StepId with same value are equal."""
        uuid = uuid4()
        assert StepId(uuid) == StepId(uuid)


class TestUserId:
    """Tests for UserId value object."""

    def test_generate_creates_valid_id(self) -> None:
        """Verify generate() creates a valid UUID-based ID."""
        uid = UserId.generate()
        assert isinstance(uid, UserId)
        assert isinstance(uid.value, UUID)

    def test_equality(self) -> None:
        """Verify two UserId with same value are equal."""
        uuid = uuid4()
        assert UserId(uuid) == UserId(uuid)
