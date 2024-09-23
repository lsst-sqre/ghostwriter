"""Exceptions for ghostwriter."""


class HookError(Exception):
    """A pre-rewrite hook failed."""


class HookNotFoundError(Exception):
    """A hook could not be loaded."""


class MatchNotFoundError(Exception):
    """No target matching input route was found."""


class ResolutionError(Exception):
    """Resolving an input route failed."""
