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

from tests.baselines.run_root import normalise_run_root, normalise_run_root_bytes
from tests.fixtures.build_fixtures import build_fixtures, build_reconnect_fixtures

MANIFEST_PATH = Path(__file__).parent / "manifest.json"

_RECON_ARGS = [
    "--scan-root", "recon/audio",
    "--volume-map", "recon/audio", "D:", "D:",
    "--match-confidence", "filename",
    "--cache", "out/recon.tagcache.json",
]

_RECON_SCAN = ["scan-reconnect-candidates", "recon/stale.nml", *_RECON_ARGS]
_RECON_DRY_RUN = ["rewrite-from-reconnect", "recon/stale.nml", "out/recon_dry.nml", *_RECON_ARGS, "--dry-run"]
_RECON_MATCHED_WRITE = ["rewrite-from-reconnect", "recon/stale.nml", "out/recon_out.nml", *_RECON_ARGS]
_RECON_AMBIGUITY_CSV = [
    "rewrite-from-reconnect", "recon/stale.nml", "out/recon_csv.nml",
    *_RECON_ARGS, "--csv", "out/recon_ambiguity.csv",
]

# Only the two cases whose OUTPUT NML contains a rewritten LOCATION need
# the run directory substituted; a rewritten DIR is rebuilt from the
# candidate's resolved absolute path. Every other case - including the
# dangling-only surfaces and the ambiguity CSV, whose old_path column is
# fixture-literal - is compared with no substitution at all.
_NORMALISE_RUN_ROOT = {"rewrite-from-reconnect"}


def normalises_run_root(argv: list[str]) -> bool:
    """Single source of truth for which cases are relaxed, keyed on argv
    exactly as _output_paths is, so writer and reader cannot drift."""
    return argv[0] in _NORMALISE_RUN_ROOT and "--dry-run" not in argv


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
    # Reconnect cases. The stale collection carries one clean match, one
    # ambiguity and one dangling entry, so a single scan exercises all
    # three outcomes. --match-confidence filename is required: the audio
    # stubs have no readable tags, so a disk candidate offers only the
    # filename key. --volume-map is required because the prefix scan
    # cannot resolve a single VOLUME/VOLUMEID pair from a relative scan
    # root, and leaving it implicit would pin the case to that failure.
    _RECON_SCAN,
    _RECON_DRY_RUN,
    _RECON_MATCHED_WRITE,
    _RECON_AMBIGUITY_CSV,
]

_OUTPUT_ARG_INDEX = {
    "rewrite": 2,
    "rewrite-from-reconnect": 2,
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
    build_reconnect_fixtures(target_dir / "recon")
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
            relax = normalises_run_root(argv)
            entry = {
                "argv": argv,
                "exit_code": exit_code,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "normalise_run_root": relax,
                "output_files": {},
            }
            if relax:
                entry["stdout"] = normalise_run_root(entry["stdout"], target_dir)
                entry["stderr"] = normalise_run_root(entry["stderr"], target_dir)
            for rel_path in _output_paths(argv):
                path = target_dir / rel_path
                if path.exists():
                    raw = path.read_bytes()
                    if relax:
                        raw = normalise_run_root_bytes(raw, target_dir)
                    entry["output_files"][rel_path] = base64.b64encode(raw).decode("ascii")
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
