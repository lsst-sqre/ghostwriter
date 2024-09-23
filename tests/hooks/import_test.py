"""Test that all hooks import.  Without insanely detailed mocks we can't
really test their functions.
"""

import ghostwriter.hooks


def test_import_hooks() -> None:
    hooks = ghostwriter.hooks.__all__
    for hook in hooks:
        _ = getattr(ghostwriter.hooks, hook)
