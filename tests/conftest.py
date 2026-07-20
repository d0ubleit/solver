"""Test fixtures and configuration for the entire test suite."""

import pytest
from uuid import UUID, uuid4


@pytest.fixture
def sample_user_id() -> UUID:
    """Return a sample user ID for testing."""
    return uuid4()


@pytest.fixture
def sample_problem_id() -> UUID:
    """Return a sample problem ID for testing."""
    return uuid4()


@pytest.fixture
def sample_step_id() -> UUID:
    """Return a sample step ID for testing."""
    return uuid4()
