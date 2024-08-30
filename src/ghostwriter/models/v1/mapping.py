"""Definition of the mapping from a top-level route to its substituted form,
as well as any hooks that should be called before passing the input route
to be rewritten.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Awaitable, Callable
from string import Template
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from ...exceptions import HookError, MatchNotFoundError, ResolutionError
from ..substitution import Parameters


def canonicalize_source_route(v: str) -> str:
    """Force source route to have one leading and one trailing slash."""
    return f"/{v.strip('/')}/"


class MapRule(BaseModel):
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
        None | list[Callable[[Parameters], Awaitable[None]]],
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
    ] = None

    skip_hooks: Annotated[
        bool,
        Field(
            title=(
                "Do not run hooks before substituting routes. You should"
                " only use this for testing."
            ),
        ),
    ] = False

    async def run_hooks(self, params: Parameters) -> None:
        """Run hooks for a route."""
        if self.skip_hooks:
            return
        if self.hooks is None:
            return
        try:
            for hook in self.hooks:
                await hook(params)
        except Exception as exc:
            raise HookError(
                f"Hook {hook} with parameters {params} failed: {exc}"
            ) from exc

    async def resolve(self, params: Parameters) -> str:
        """Resolve a route."""
        if not params.path.startswith(self.source_prefix[1:]):
            # The source prefix starts with a slash; the passed path will not.
            raise MatchNotFoundError(
                f"Source {self.source_prefix} does not match {params.path}"
            )
        await self.run_hooks(params=params)
        tmpl = Template(self.target)
        mapping = dataclasses.asdict(params)
        full_path = mapping["path"]
        # Strip matched path
        mapping["path"] = full_path[(len(self.source_prefix) - 1) :]
        try:
            return tmpl.substitute(mapping)
        except Exception as exc:
            raise ResolutionError(
                f"Resolving {self.target} with parameters {params}"
                f" failed: {exc}"
            ) from exc


def sort_routes(v: list[MapRule]) -> list[MapRule]:
    """Sort routes by length, longest first."""
    return sorted(v, key=lambda x: len(str(x)), reverse=True)


class RouteMap(BaseModel):
    """Collection of MapRules."""

    routes: Annotated[
        list[MapRule],
        Field(title="List of route transformation rules"),
        AfterValidator(sort_routes),
    ]

    def get_routes(self) -> list[str]:
        """Return all matchable source routes."""
        return [x.source_prefix for x in self.routes]

    async def resolve(self, params: Parameters) -> str:
        """Resolve a route substitution."""
        for route in self.routes:
            if params.path.startswith(route.source_prefix[1:]):
                # Source paths start with "/"; targets do not.
                return await route.resolve(params)
        raise MatchNotFoundError(
            f"No match for {params.path} found in {self.get_routes()}"
        )
