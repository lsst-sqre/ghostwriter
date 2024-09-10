"""Definition of the mapping from a top-level route to its substituted form,
as well as any hooks that should be called before passing the input route
to be rewritten.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from string import Template
from typing import Annotated, TypeAlias

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field

from ... import hooks
from ...exceptions import (
    HookError,
    HookNotFoundError,
    MatchNotFoundError,
    ResolutionError,
)
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

    async def run_hooks(self, params: Parameters) -> None:
        """Run hooks for a route."""
        if self.hooks is None:
            return
        try:
            for hook in self.hooks:
                res = await hook(params)
                if res is None:
                    continue
                # If we got back a value, those are our new parameters.
                # The path may be mutated, and unique_id may have changed.
                # If base_url, user, token, or client has changed, call
                # shenanigans and raise an error.
                errs = [
                    x
                    for x in ("base_url", "user", "token", "client")
                    if getattr(res, x) != getattr(params, x)
                ]
                if errs:
                    errstr = "Attempt to change immutable parameter"
                    if len(errs) > 1:
                        errstr += "s"
                    errstr += f": {', '.join(errs)}"
                    raise RuntimeError(errstr)  # Immediately converted
                params = res
        except Exception as exc:
            raise HookError(
                f"Hook {hook} with parameters {params} failed: {exc}"
            ) from exc

    async def resolve_route(self, params: Parameters) -> str:
        """Resolve a route.

        Resolution has two phases.

        The first is to run each hook, in order.  Every hook is an async
        function that takes a `~ghostwriter.models.substitution.Parameters`
        object as its only argument, and returns either ``None`` or a
        `~ghostwriter.models.substitution.Parameters` object.  The hook may
        take any action it desires, and it should raise an exception if that
        action fails.  If it returns a ``Parameters`` object, only the
        ``path`` and ``unique_id`` fields may differ.  Any other change will
        raise an exception.  If the hook returns a value, that value is used
        as the ``Parameters`` input for subsequent hooks.  Otherwise the input
        remains unchanged.

        The second phase is to substitute the target string with any or all
        of the ``base_url``, ``user``, ``path``, and ``unique_id`` fields
        found in the final ``Parameters`` object, and to return a string
        with those templates filled in.

        Parameters
        ----------
        params
            Substitution parameters.

        Returns
        -------
        str
            A string representing the target template with all fields
        substituted from the supplied parameters.
        """
        if not params.path.startswith(self.source_prefix[1:]):
            # The source prefix starts with a slash; the passed path will not.
            raise MatchNotFoundError(
                f"Source {self.source_prefix} does not match {params.path}"
            )
        await self.run_hooks(params=params)
        tmpl = Template(self.target)
        mapping = params.rewrite_mapping()
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

    async def resolve_route(self, params: Parameters) -> str:
        """Resolve the first matching route substitution."""
        for route in self.routes:
            # Because we have sorted the routes, longest first, we will
            # necessarily hit the most-specific route before a less-specific
            # one.
            if params.path.startswith(route.source_prefix[1:]):
                # Source paths start with "/"; targets do not.
                return await route.resolve_route(params)
        raise MatchNotFoundError(
            f"No match for {params.path} found in {self.get_routes()}"
        )
