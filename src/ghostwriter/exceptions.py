"""Exceptions for ghostwriter."""


class HookError(Exception):
    """A pre-rewrite hook failed."""


class ResolutionError(Exception):
    """Resolving an input route failed."""


class MatchNotFoundError(Exception):
    """No target matching input route was found."""
