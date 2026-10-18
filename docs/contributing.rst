Building the Documentation
==========================

The documentation uses Sphinx and the Read the Docs theme, like the
``alternative`` package. The examples are included directly from
``README.rst`` so they have one source.

Use uv 0.13.1 or newer and Python 3.12 or newer for documentation work.
The package itself continues to support Python 3.9 and newer.

.. code-block:: console

   $ uv sync --locked --group docs --python 3.12
   $ uv run --locked --group docs sphinx-build --fail-on-warning --keep-going --builder=html docs docs/_build/html

Open ``docs/_build/html/index.html`` to preview the result. CI runs the same
warning-free HTML build, and ``.readthedocs.yaml`` configures Read the Docs
to build ``docs/conf.py`` on Python 3.12.

The committed ``uv.lock`` records documentation dependencies. After changing
them, run ``uv lock --upgrade`` and commit the updated lockfile. Dependabot
also proposes weekly dependency updates.

Read the Docs builds the ``latest`` documentation from ``master``. New
version tags can be enabled after they include the documentation configuration.
