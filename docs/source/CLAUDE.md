# docs/source/

Sphinx sources for the code-reference site; the API reference under `generated/` is produced by `conf.py` on each run and the HTML lands in `docs/build/`, neither of which is edited by hand.

## Files

| File           | What                                                                                                                                                                       | When to read                                                              |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `conf.py`      | Sphinx configuration: autodoc/autosummary/napoleon/viewcode extensions, the alabaster theme, `acoustid`/`mutagen`/`nicegui` mocked for import, and a `builder-inited` hook running `sphinx.ext.apidoc` over `traktor_nml/` into `generated/` | Changing extensions or theme, mocking another optional import, or changing how the API reference is generated |
| `index.rst`    | Root document and toctree over `overview`, `cli` and `generated/traktor_nml`                                                                                                | Adding a page to the site                                                  |
| `overview.rst` | What the tool is, which document is authoritative for what (repository `README.md`, `traktor_nml/README.md`, this site), and the `pip install .[docs]` / `sphinx-build` commands | Orienting in the docs, or looking up the build command                     |
| `cli.rst`      | `automodule` entries for `traktor_nml.cli` and the `traktor_nml_tool` wrapper script                                                                                         | Changing which CLI modules the site documents                              |

## Build

```bash
pip install .[docs]
sphinx-build -b html docs/source docs/build/html
```
