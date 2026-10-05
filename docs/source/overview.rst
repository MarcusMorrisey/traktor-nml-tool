Overview
========

``traktor-nml-tool`` is a Python CLI for inspecting, repairing, merging, and
splitting Traktor ``.nml`` collection files, with a desktop app
(``python -m traktor_nml.gui``) for reconstructing playlists, reviewing
reconnect matches, and building playlists from a track list.

Documentation layout
--------------------

- The repository ``README.md`` is the operator-facing overview and install guide.
- ``traktor_nml/README.md`` is the architectural reference and decision log.
- This Sphinx site is the code reference for the importable package, the
  ``traktor_nml.gui`` app and the CLI shim. The app's third-party imports
  (``nicegui``, ``webview``) are mocked, so the site builds without the ``gui``
  extra.

Build the docs
--------------

Install the docs extra and build HTML output:

.. code-block:: bash

   pip install .[docs]
   sphinx-build -b html docs/source docs/build/html

The generated site entrypoint is ``docs/build/html/index.html``.
