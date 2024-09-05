#######
Routing
#######

Routing is accomplished in a fairly straightforward manner.

The routing configuration is found by default at ``/etc/ghostwriter/routing.yaml`` although this is configurable via the Ghostwriter configuration file, by default located at ``/etc/ghostwriter/config.yaml``.

There is a single key, ``routes``, in the routing document, which contains a lists of routes.

Each route contains three entries.

These are ``source_prefix``, ``target``, and ``hooks``.

source_prefix
=============

``source_prefix`` is the top-level redirection route.
It should begin and end with a slash.

This will be rerouted from the top-level to ``/ghostwriter/rewrite/<source_prefix>`` for processing by ``ghostwriter``.

target
======

``target`` is a string in `Python string template format <https://docs.python.org/3/library/string.html#template-strings>`__ .

There are three template variables, defined in the ``ghostwriter.models.substitution.Parameters`` class, that you can use here: ``${base_url}``, ``${user}``, and ``${path}``.

* ``${base_url}`` is defined by the Phalanx installation and is the root URL of the Phalanx environment. In general, if you want the redirection to point to the same Phalanx environment that you're starting from, which you very likely do (although there are imaginable exceptions--maybe you want to point to Roundtable from an RSP instance, for example), you should start ``${target}`` with this.
* ``${user}`` is the username of the logged-in user according to Gafaelfawr.  You will want this, for instance, to create a path into an individual user's JupyterLab environment.
* ``${path}`` is the path after ``${source_prefix}`` is stripped from the front.

hooks
=====

``hooks`` are described `in another section <../hooks/index.html>`__.

Examples
========

The following routes ``/tutorials/`` to a user's checked-out copy of the
tutorial notebooks, and routes ``/queries/`` to a templated notebook for a particular Portal query ID:

    .. code-block:: yaml

       routes:
       - source_prefix: "/tutorials/"
         target: "${base_url}/nb/user/${user}/lab/tree/notebooks/tutorial-notebooks/${path}.ipynb"
         hooks:
         - "ensure_running_lab"
       - source_prefix: "/queries/"
         target: "${base_url}/nb/user/${user}/lab/tree/notebooks/queries/portal_${path}.ipynb"
         hooks:
         - "ensure_running_lab"
         - "portal_query"

For each of these source prefixes, the ultimate targets are within the user's Lab home space.

The ``/nb`` route will carry the user to the Hub.

From there, the ``/user/${user}/lab/tree`` route will take the user to a particular file within their space.

The rest of the path specifies the directory in which the notebook can be found, and constructs the filename and an ``.ipynb`` suffix.

For each route, the ``ensure_running_lab`` hook is run, which does exactly what you would expect from the name.

In the case of the portal query, the second hook, ``portal_query``, reaches into the user's lab and manipulates the server-side query extension that is part of the `rsp-jupyter-extensions <https://github.com/lsst-sqre/rsp-jupyter-extensions>`__ package, which generates a templated notebook.

After all hooks have run, redirection to the specified target occurs.
