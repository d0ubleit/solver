"""Domain exceptions for the Solver application."""


class DomainError(Exception):
    """Base class for all domain errors."""


class ProblemAlreadyResolvedError(DomainError):
    """Raised when trying to resolve an already resolved problem."""

    def __init__(self, problem_id: str = "") -> None:
        self.problem_id = problem_id
        super().__init__(f"Problem {problem_id} is already resolved")


class StepNotPendingError(DomainError):
    """Raised when trying to complete a step that is not in pending/in_progress state."""

    def __init__(self, step_id: str = "", current_status: str = "") -> None:
        self.step_id = step_id
        self.current_status = current_status
        super().__init__(
            f"Step {step_id} cannot be completed: current status is {current_status}"
        )


class InvalidStepStatusTransitionError(DomainError):
    """Raised when an invalid step status transition is attempted."""

    def __init__(self, step_id: str = "", from_status: str = "", to_status: str = "") -> None:
        self.step_id = step_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid step transition for {step_id}: {from_status} -> {to_status}"
        )


class ProblemNotFoundError(DomainError):
    """Raised when a problem is not found in the repository."""

    def __init__(self, problem_id: str = "") -> None:
        self.problem_id = problem_id
        super().__init__(f"Problem {problem_id} not found")


class UserNotFoundError(DomainError):
    """Raised when a user is not found in the repository."""

    def __init__(self, user_id: str = "") -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")


class AIAnalysisError(DomainError):
    """Raised when AI analysis fails."""

    def __init__(self, problem_id: str = "", reason: str = "") -> None:
        self.problem_id = problem_id
        self.reason = reason
        super().__init__(f"AI analysis failed for problem {problem_id}: {reason}")
