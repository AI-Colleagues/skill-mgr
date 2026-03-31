"""Project error types."""

from __future__ import annotations


class SkillMgrError(RuntimeError):
    """Raised when a skill-manager operation fails."""

    def __init__(self, message: str, *, code: str = "skill_mgr_error") -> None:
        """Initialize the error with a stable error code."""
        super().__init__(message)
        self.code = code
