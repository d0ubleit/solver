"""Repository interfaces (ports) for the domain layer."""

from abc import ABC, abstractmethod
from typing import Sequence

from solver.domain.entities import Problem, User, ConversationContext
from solver.domain.value_objects import ProblemId, UserId


class UserRepository(ABC):
    """Repository interface for User aggregate."""

    @abstractmethod
    async def add(self, user: User) -> User:
        """Add a new user to the repository."""
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None:
        """Retrieve a user by their ID."""
        ...

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Retrieve a user by their Telegram ID."""
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update an existing user."""
        ...


class ProblemRepository(ABC):
    """Repository interface for Problem aggregate."""

    @abstractmethod
    async def add(self, problem: Problem) -> Problem:
        """Add a new problem to the repository."""
        ...

    @abstractmethod
    async def get_by_id(self, problem_id: ProblemId) -> Problem | None:
        """Retrieve a problem by its ID."""
        ...

    @abstractmethod
    async def get_by_user_id(self, user_id: UserId) -> Sequence[Problem]:
        """Retrieve all problems for a given user."""
        ...

    @abstractmethod
    async def get_active_by_user_id(self, user_id: UserId) -> Sequence[Problem]:
        """Retrieve all active (non-resolved) problems for a user."""
        ...

    @abstractmethod
    async def update(self, problem: Problem) -> Problem:
        """Update an existing problem."""
        ...

    @abstractmethod
    async def delete(self, problem_id: ProblemId) -> None:
        """Delete a problem by its ID."""
        ...


class ConversationContextRepository(ABC):
    """Repository interface for ConversationContext."""

    @abstractmethod
    async def add(self, context: ConversationContext) -> ConversationContext:
        """Add a new conversation context."""
        ...

    @abstractmethod
    async def get_by_problem_id(self, problem_id: ProblemId) -> ConversationContext | None:
        """Retrieve the conversation context for a problem."""
        ...

    @abstractmethod
    async def update(self, context: ConversationContext) -> ConversationContext:
        """Update an existing conversation context."""
        ...
