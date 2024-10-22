"""Perform the series of substitutions to redirect the user request."""

from string import Template

from pydantic import HttpUrl
from structlog.stdlib import BoundLogger

from ..exceptions import HookError, MatchNotFoundError, ResolutionError
from ..models.substitution import Parameters
from ..models.v1.mapping import RouteCollection, RouteMapping


async def rewrite_request(
    route_collection: RouteCollection, params: Parameters, logger: BoundLogger
) -> str:
    """Find matching route, if any, and apply its mapping.

    Parameters
    ----------
    route_collection.
        List of path prefixes mapped to their substitution criteria.

    params
        Substitution parameters.

    logger
        Logger.

    Returns
    -------
    str
        A string representing the target template with all fields
    substituted from the supplied parameters.
    """
    for route in route_collection.routes:
        # Because we have sorted the routes, longest first, we will
        # necessarily hit the most-specific route before a less-specific
        # one.
        if params.path.startswith(route.source_prefix[1:]):
            # Source paths start with "/"; targets do not.
            # Restore target.
            return await rewrite_route(route, params, logger)
    raise MatchNotFoundError(
        f"No match for {params.path} found in {route_collection.get_routes()}"
    )


async def rewrite_route(
    route: RouteMapping, params: Parameters, logger: BoundLogger
) -> str:
    """Resolve a route.

    Parameters
    ----------
    route
        A path prefix mapped to its substitution criteria.

    params
        Substitution parameters.

    logger
        Logger.

    Returns
    -------
    str
        A string representing the target template with all fields
    substituted from the supplied parameters.

    Notes
    -----
    Resolution has two phases.

    The first is to run each hook, in order.  Every hook is an async
    function that takes a `~ghostwriter.models.substitution.Parameters`
    object as its only argument.  It returns either ``None`` or a
    `~ghostwriter.models.substitution.Parameters` object.  The hook
    may take any action it desires, and it should raise an exception if
    that action fails.  If it returns a ``Parameters`` object, only the
    ``target`` and ``unique_id`` fields may differ from the input.
    Any other change will raise an exception.  If the hook returns a
    value, that value is used as the ``Parameters`` input for subsequent
    hooks, and the current route target is updated immediately.  Otherwise
    the input remains unchanged.

    The second is to substitute the (possibly updated) route target
    template with any or all of the ``base_url``, ``user``, ``path``,
    and ``unique_id`` fields.  This will return a string with
    those placeholders filled in, and that in turn will be the final
    target (the Location: header) of the HTTP redirect response received
    by the user.

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
    # Sanity check
    if not params.path.startswith(route.source_prefix[1:]):
        # The source prefix starts with a slash; the passed path will not.
        raise MatchNotFoundError(
            f"Source {route.source_prefix} does not match {params.path}"
        )

    params = await run_hooks(route=route, params=params, logger=logger)
    if params.target is None:
        raise RuntimeError(
            f"Parameters {params} cannot have empty target"
            " after hook processing"
        )

    tmpl = Template(params.target)
    mapping = params.rewrite_mapping()
    full_path = mapping["path"]
    # Strip matched path if requested
    if params.strip:
        mapping["path"] = full_path[(len(route.source_prefix) - 1) :]
    logger.debug(f"Rewriting '{params.target}' with '{mapping}'")
    try:
        # Canonicalize the resulting URL (and throw an error if it's
        # wildly not URL-looking).
        results = str(HttpUrl(tmpl.substitute(mapping)))
        logger.debug(f"Rewritten target: '{results}'")
        return results
    except Exception as exc:
        raise ResolutionError(
            f"Resolving {route.target} with parameters {params}"
            f" failed: {exc}"
        ) from exc


async def run_hooks(
    route: RouteMapping, params: Parameters, logger: BoundLogger
) -> Parameters:
    """Run hooks for a route.  Return a set of parameters, which may be
    modified from the ones we received.

    Parameters
    ----------
    route
        A path prefix mapped to its substitution criteria.

    params
        Substitution parameters.

    logger
        Logger.

    Returns
    -------
    `~ghostwriter.models.substitution.Parameters`
        Parameters to pass to the URL rewrite.  These may not be the same
    as the ones that we received as our input parameters (specifically,
    target, unique_id, and/or final may have changed).
    """
    current_target = route.target
    params.target = current_target
    if route.hooks is None:
        # We need the target, but since no hooks ran, it is unchanged from
        # the route target
        return params
    try:
        for hook in route.hooks:
            logger.debug(f"Running hook '{hook}' with '{params}'")
            res = await hook(params)
            if res is None:
                continue
            # If we got back a value, those are our new parameters.
            # The target field and unique_id fields may have
            # changed. If base_url, user, path, token, or client has
            # changed, call shenanigans and raise an error.
            errs = [
                x
                for x in ("base_url", "user", "token", "client", "path")
                if getattr(res, x) != getattr(params, x)
            ]
            if errs:
                errstr = "Attempt to change immutable parameter"
                if len(errs) > 1:
                    errstr += "s"
                errstr += f": {', '.join(errs)}"
                raise RuntimeError(errstr)  # Immediately converted
            if res.target is None:
                res.target = current_target  # No parameters changed
            if res.final:
                return res
            if res.target != current_target:
                # Update current_target with result field if it changed
                current_target = res.target
            # Use result as next round's params
            params = res
    except Exception as exc:
        raise HookError(
            f"Hook {hook} with parameters {params} failed: {exc}"
        ) from exc
    return params
