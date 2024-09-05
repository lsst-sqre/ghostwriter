.. toctree::
   :maxdepth: 1
   :hidden:

   routing/index
   hooks/index
   api

###########
Ghostwriter
###########

Ghostwriter is a service to provide link shortening and personalization for a Phalanx installation.

There are two initial use cases: the first is to allow specification of a generic URL for tutorial notebooks that will open them in a user's Lab environment.

The second is to allow appending a Portal UWS query ID to a generic route, and have that open a templated notebook in a user's Lab containing retrieval of that query and conversion to a table.

This is accomplished through a configuration file specifying the routes that get redirected and personalized, and for each route a list of hooks applied to do work before the redirection is implemented.

.. grid:: 1

   .. grid-item-card:: Routing
      :link: routing/index
      :link-type: doc

      Learn how to set up routing for ghostwriter redirection.

   .. grid-item-card:: Hooks
      :link: hooks/index
      :link-type: doc

      Learn how to use hooks to provide pre-redirection functionality.

