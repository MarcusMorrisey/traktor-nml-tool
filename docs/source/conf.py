from __future__ import annotations

from pathlib import Path

project = "traktor-nml-tool"
author = "traktor-nml-tool contributors"
copyright = "2026, traktor-nml-tool contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns: list[str] = []
html_theme = "alabaster"

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True
autodoc_mock_imports = ["acoustid", "mutagen", "nicegui"]

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "traktor_nml"
GENERATED_DIR = Path(__file__).resolve().parent / "generated"


def _generate_apidoc(_app) -> None:
    from sphinx.ext.apidoc import main as apidoc_main

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    apidoc_main(
        [
            "--force",
            "--module-first",
            "--separate",
            "--no-toc",
            "--output-dir",
            str(GENERATED_DIR),
            str(PACKAGE_DIR),
        ]
    )


def setup(app) -> dict[str, bool]:
    import sys

    sys.path.insert(0, str(ROOT))
    app.connect("builder-inited", _generate_apidoc)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
