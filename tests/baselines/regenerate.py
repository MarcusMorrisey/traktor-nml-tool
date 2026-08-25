"""Regenerate tests/baselines/manifest.json from the current tool.

Documented regeneration command:

    python -m tests.baselines.regenerate

Run only against the unmodified tool when first capturing the parity
oracle, or deliberately after a change whose new output is intentional.
Regeneration over an unmodified tool reproduces the stored manifest exactly
(the fixture corpus and argv list are both deterministic), so running it is
a no-op unless behavior actually changed. Not imported or exercised by the
test suite itself.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
from pathlib import Path

from tests.fixtures.build_fixtures import build_fixtures

MANIFEST_PATH = Path(__file__).parent / "manifest.json"

CASES: list[list[str]] = [
    ["inspect", "corpus/moved_paths.nml", "--limit", "5"],
    ["inspect", "corpus/playlist_tree.nml", "--limit", "5", "--csv", "out/inspect.csv"],
    ["encode-dir", r"C:\Music\Foo"],
    [
        "preview-diff", "corpus/moved_paths.nml",
        "--old-volume", "C:", "--old-dir-prefix", "/:Users/:dj/:Music/:",
        "--new-volume", "D:", "--new-dir-prefix", "/:Music/:",
    ],
    ["preview-compare", "corpus/duplicate_rips.nml", "corpus/duplicate_rips.nml", "--limit", "5"],
    ["scan-compare-candidates", "corpus/moved_paths.nml", "corpus", "--limit", "5"],
    [
        "rewrite", "corpus/moved_paths.nml", "out/rewrite_out.nml",
        "--old-volume", "C:", "--old-dir-prefix", "/:Users/:dj/:Music/:",
        "--new-volume", "D:", "--new-dir-prefix", "/:Music/:",
    ],
    [
        "rewrite-from-collection-compare",
        "corpus/renamed_file.nml", "corpus/renamed_file.nml", "out/compare_out.nml",
        "--allow-artist-title-only",
    ],
]

_OUTPUT_ARG_INDEX = {
    "rewrite": 2,
    "rewrite-from-collection-compare": 3,
}


def _output_paths(argv: list[str]) -> list[str]:
    """Return the output file path(s) argv writes, using
    _OUTPUT_ARG_INDEX to find the destination argument for commands that
    write files; a command absent from that mapping is read-only and
    produces no output file to capture."""
    paths = []
    if "--csv" in argv:
        paths.append(argv[argv.index("--csv") + 1])
    index = _OUTPUT_ARG_INDEX.get(argv[0])
    if index is not None:
        paths.append(argv[index])
    return paths


def regenerate(target_dir: Path) -> list[dict]:
    from traktor_nml.cli import main

    build_fixtures(target_dir / "corpus")
    (target_dir / "out").mkdir(exist_ok=True)

    manifest = []
    old_cwd = Path.cwd()
    os.chdir(target_dir)
    try:
        for argv in CASES:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                try:
                    exit_code = main(argv)
                except SystemExit as exc:
                    exit_code = 0 if exc.code is None else int(exc.code)
            entry = {
                "argv": argv,
                "exit_code": exit_code,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "output_files": {},
            }
            for rel_path in _output_paths(argv):
                path = target_dir / rel_path
                if path.exists():
                    entry["output_files"][rel_path] = base64.b64encode(path.read_bytes()).decode("ascii")
            manifest.append(entry)
    finally:
        os.chdir(old_cwd)
    return manifest


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        manifest = regenerate(Path(tmp))
    # Written as explicit UTF-8 bytes with LF endings, not write_text: the
    # manifest is pinned by SHA-256, and text mode would emit CRLF on
    # Windows and LF elsewhere, so the same reviewed regeneration would
    # produce a different digest per host. Paired with the .gitattributes
    # -text rule that stops git rewriting the blob on checkout.
    MANIFEST_PATH.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    print(f"wrote {MANIFEST_PATH}")
