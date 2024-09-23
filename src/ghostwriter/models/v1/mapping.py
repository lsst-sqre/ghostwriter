"""Definition of the mapping from a top-level route to its substituted form,
as well as any hooks that should be called before passing the input route
to be rewritten.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, TypeAlias

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field

from ... import hooks
from ...exceptions import HookNotFoundError
from ..substitution import Parameters

Hook: TypeAlias = Callable[[Parameters], Awaitable[None | Parameters]]


def load_hooks(v: list[str | Hook]) -> list[Hook]:
    """Hooks will be listed as strings in the config file.  This is a model
    validator, which transforms those strings into the Python objects they
    represent, which has the effect of loading each corresponding hook
    function into the namespace.
    """
    retval: list[Hook] = []
    for hook in v:
        if callable(hook):
            # We can't check if it's just a Hook, because:
            # "Parameterized generics cannot be used with class or instance
            # checks"
            retval.append(hook)
            continue
        if not isinstance(hook, str):
            raise HookNotFoundError(f"Hook {hook} could not be loaded")
        if hook.startswith("ghostwriter.hooks."):
            hookname = hook[len("ghostwriter.hooks.") :]
        else:
            hookname = hook
        try:
            obj = getattr(hooks, hookname)
        except AttributeError as exc:
            raise HookNotFoundError(
                f"Hookname {hook} could not be loaded: {exc}"
            ) from exc
        retval.append(obj)
    return retval


def canonicalize_source_route(v: str) -> str:
    """Force source route to have one leading and one trailing slash."""
    return f"/{v.strip('/')}/"


class RouteMapping(BaseModel):
    """Instructions for rewriting a map."""

    source_prefix: Annotated[
        str,
        Field(
            title="Source route",
            description=(
                "Generic route prefix to be substituted."
                " Everything after this prefix will be collected in"
                " `path` for purposes of substitution in the target"
                " route."
            ),
            examples=["/tutorials/"],
        ),
        AfterValidator(canonicalize_source_route),
    ]

    target: Annotated[
        str,
        Field(
            title="Target route",
            description=(
                "Route prefix (with placeholder[|s]) for the resolved"
                " route. The placeholders are Python string.Template"
                " names.  ${base_url} and ${user} are determined from"
                " the request context, and ${path} is everything following"
                " the source route string in the input route."
            ),
            examples=["${base_url}/nb/user/${user}/lab/tree/${path}.ipynb"],
        ),
    ]

    hooks: Annotated[
        None | list[Hook],
        Field(
            title="Pre-substitution hooks",
            description=(
                "List of hooks to be called in order before substituting"
                " and returning the route. Each hook takes as input a"
                " ~ghostwriter.models.substitution.Parameters object"
                " and returns `None`. In the event of hook failure, it"
                " should raise an exception. These hooks should be"
                " idempotent, which in the usual case, means not"
                " overwriting an extant file, since the common case is to"
                " build or download a file in a user context before"
                " returning the URL pointing to it."
            ),
        ),
        BeforeValidator(load_hooks),
    ] = None


def sort_routes(v: list[RouteMapping]) -> list[RouteMapping]:
    """Sort routes by length, longest first."""
    return sorted(v, key=lambda x: len(str(x)), reverse=True)


class RouteCollection(BaseModel):
    """Collection of MapRules."""

    routes: Annotated[
        list[RouteMapping],
        Field(title="List of route transformation rules"),
        AfterValidator(sort_routes),
    ]

    def get_routes(self) -> list[str]:
        """Return all matchable source routes."""
        return [x.source_prefix for x in self.routes]
