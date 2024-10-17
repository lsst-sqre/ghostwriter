#####
Hooks
#####

Hooks are units of work carried out before the redirect for the user's browser is issued.

There is a list of hooks (possibly empty) for each route specified in the configuration.

Each hook is run in sequence. If any hook raises an exception, the user will receive an error rather than a redirect.

Because (at least at present) hooks are, by definition, located inside the ``ghostwriter.hooks`` Python module namespace, any additions or modifications to hooks are code and repository changes.
Therefore, any proposed hooks or modififactions to existing ones will need to go through the SQuaRE PR process.

Anatomy of a Hook
=================

A hook is an ``async`` Python function that takes one argument, a ``ghostwriter.models.substitution.Parameters`` instance, and returns either ``None`` or ``ghostwriter.models.substitution.Parameters``.

To signal failure, a hook should raise an ``Exception``.

If a hook does not wish to modify the parameters used by future hooks or
route substitution, it should return ``None``.

If it does return an object, that object will first be checked to ensure only the ``target`` and ``unique_id`` fields changed.
If any other field changed, an exception will be raised.
The returned ``Parameters`` object will be used as the input to
subsequent hooks and to update the target path that will be substituted.

That's the whole thing.

Within those constraints, a hook can do whatever it likes.

Parameters
==========

Obviously that begs the question of "what's in a ``Parameters`` object?"

Three of the fields are obvious: they are ``base_url``, ``path``, and ``user``, all used in path construction for the redirect.

Two fields are only for use by the hook itself: those are ``target`` and ``unique_id``.
The ``target`` field will be injected when the hook is run, and the ``unique_id`` field may be populated.
These two are the only fields a hook is permitted to change if it returns a ``Parameters`` object.
The ``target`` may need to be rewritten to accomodate a ``unique_id``.

The motivation here is simply to avoid rewriting existing files: the correct response is context-dependent, and might be to redirect to the existing file, but it equally well might be to create a new file under a different name.
In this case, the file name stem (that is, the part before the suffix) might need to be appended with a ``unique_id``, which could be (again, the best choice depends on context) a serial number, as in ``Untitled2.ipynb``, or a string representation of the date and time, or simply a UUID.
The ``unique_id`` can be any string legal in a filename, as long as the filename containing it will be distinct from any other filename in the directory.
Guaranteeing that it is unique is the job of the hook writer.

Given the context, the existing hooks do not worry much about race conditions.
If you are using the date or an incrementing integer...you are still in an RSP context, so it's very unlikely a user will go to the same redirected URL twice in the same microsecond, or even twice within the time it takes to write out a notebook.  If you do have some high-frequency use case, a UUID would be a better choice.

The final pair of fields are slightly more obscure: ``token`` and ``client`` (strictly speaking, ``token`` is superfluous since it is very likely only be useful in the context of ``client``, which already knows it, and from which it could be extracted).

The ``client`` field contains a Nublado client loaded with the given token, which can be used directly (as ``mobu`` and ``noteburst`` do) to execute Python code (or whole notebooks) within the context of a kernel within a Nublado JupyterLab.
It can also be used as a generic (yet authenticated) HTTP client for the rest of a Phalanx environment, and thus can be used to talk to any other service, or to the API endpoints within a Lab environment.

The token, from a `Gafaelfawr <https://gafaelfawr.lsst.io>`__ standpoint, is delegated with the ``notebook: {}`` parameter, meaning that it has identical powers to the token the user got from their initial login via Gafaelfawr.

In effect, that means that the RSP client can perform complete impersonation of the user: anything that user could do inside a given Phalanx instance, a hook could do via its client.

With great power comes great responsibility.

Example
=======

The `portal_query <https://github.com/lsst-sqre/ghostwriter/blob/main/src/ghostwriter/hooks/portal_query.py>`__ hook provides a moderately complex workflow.

Note that it assumes a running Lab for the user.

While this could easily be added to the hook, that workflow already exists as the ``ensure_running_lab`` hook, so it's more economical to simply list ``portal_query`` after ``ensure_running_lab`` in the list of hooks to run for the ``/queries/`` route.

#. The query ID is extracted from the path.
#. This is used to construct the portal query URL.
#. The ``client`` authenticates to the Hub and Lab (since we've just run ``ensure_running_lab`` this step is likely superfluous, because it's quite unlikely we would have gotten deauthenticated in the meantime).
#. The ``client`` uses the ``/api/contents`` endpoint to determine if the requested query notebook already exists, and returns immediately if it does.
#. Otherwise, the ``client`` constructs the ``POST`` to request a templated notebook from the query ID.

After all hooks have finished, the ``ghostwriter`` service will return an HTTP redirect pointing to the templated notebook constructed (or left unaltered, if it already existed) by the hook.
