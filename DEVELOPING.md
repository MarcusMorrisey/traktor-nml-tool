# Developing this project

Setting up, and the invariants that are silent when they break. The README's
[Install](README.md#install) section covers the package and its extras; this covers
working *on* it.

## The layout

Three repositories, siblings:

```
C:\codex\
  traktor-nml-tool\             this repository - the tool and the wizard
  traktor-nml-tool-gate\        the serving gate and its fixtures
  traktor-nml-tool-plan\        the W-001..W-004 plan, archival
```

The durable record of why the tree is shaped as it is lives in the repositories
themselves: `traktor_nml/README.md` is the decision log and the authority,
`docs/plans/` holds one directory per piece of work, and `docs/` holds the dated
records of what each served-page gate run measured.

Nothing hardcodes any of these paths. `tools/preflight.py` and the gate's
`gate_paths.py` resolve siblings from their own location, with an environment
variable overriding each for a tree that sits elsewhere:

| Variable | Overrides | Read by |
|---|---|---|
| `TRAKTOR_NML_TOOL` | this repository | the gate's `gate_paths.py` |
| `TRAKTOR_NML_TOOL_PLAN` | the plan repository | `tools/preflight.py` |
| `TRAKTOR_NML_TOOL_GATE` | the gate repository | `tools/preflight.py` |

The one that is *not* overridable is this repository as `preflight.py` sees it: that
file lives here, so `tools/../` is the only tree it can be describing.

## From a clean clone

```bash
git clone https://github.com/MarcusMorrisey/traktor-nml-tool.git
git clone https://github.com/MarcusMorrisey/traktor-nml-tool-gate.git
git clone https://github.com/MarcusMorrisey/traktor-nml-tool-plan.git
```

Then, in `traktor-nml-tool`:

```bash
git config core.hooksPath hooks
```

`hooks/pre-push` refuses to move or delete a `parity-baseline-*` tag, which pins the parity
oracle. Git reads hooks from `.git/hooks` unless told otherwise, and `core.hooksPath` is
config rather than content, so it does not clone. Until that line is run the hook sits on
disk inert, which reads exactly like one that is working. `tools/preflight.py` checks it.

## Two interpreters, and why

Both are legitimate. Both are green. They are not interchangeable.

| | System interpreter | `.venv` |
|---|---|---|
| Runs | the suite | the app and the gate |
| Carries | `mutagen`, `lxml` | those plus `nicegui`, `webview`, `tinycss2` |
| Suite | **531 passed, 3 skipped** | **532 passed, 2 skipped** |

The whole of that difference is `pyacoustid` and the chromaprint library it needs. Both
runs are green; the two counts mean different things, so a count quoted without the
interpreter it was taken under says nothing. The suite prints both beside its totals.

**The isolation tests do not depend on `nicegui` being absent.**
`tests/test_cli_without_nicegui.py` blocks the import through `sys.meta_path` precisely so it
holds on a machine carrying the real package, and `tests/test_gui_import_isolation.py` walks
ASTs and imports nothing. Both pass under either interpreter — 7 passed each way, measured
with `nicegui` 3.16.0 installed. Do not add a guard that refuses `.venv` on their account.

No pre-flight incantation is needed to tell the two apart: the suite prints its interpreter
and its optional packages beside its own totals, under `-q` as well, so a count copied out of
a run carries the conditions it was taken under.

Create `.venv` with the `gui` extra:

```bash
python -m venv .venv && .venv/Scripts/python.exe -m pip install -e .[gui]
```

Never install into the system interpreter.

## Line endings

This tree is deliberately not uniform: 320 files are LF, 100 are CRLF, three are mixed, and
each is load-bearing somewhere.

- `traktor_nml/gui/app.py` is wholly CRLF, 1686 of them and no bare LF.
  `tests/test_gui_line_endings.py` asserts it and `tools/preflight.py` reports it.
- The patch sets under `docs/plans/*/scratch/` are CRLF because that is what they were
  captured from. A rewritten one produces phantom rejects when reapplied.
- `tests/baselines/manifest.json` is pinned by SHA-256 over its exact bytes.

`.gitattributes` sets `* -text`, so git stores and checks out bytes unchanged. Without it a
clone on a stock Windows git — `core.autocrlf=true` is the installer's default — checks the
LF files out as CRLF. Measured by cloning this repository at each commit with that setting:

| | worktree `README.md` | index | `git status` |
|---|---|---|---|
| without `* -text` | 132 CRLF | 152 LF | clean |
| with `* -text` | 152 LF | 152 LF | clean |

The conversion happens and `git status` reports nothing, which is the point — it is invisible
to the one command anyone would run, and every tool reading bytes rather than lines then sees
a file that is not what the repository holds. Both sibling repositories carry the same line.

The index-normalisation half of the usual autocrlf description is not repeated here because
it did not reproduce on this tree: staging a CRLF file under `core.autocrlf=true` left it
`i/crlf` either way.

When editing, read and write with `newline=''` so the file keeps its own endings. An
exact-match edit that "cannot find" its anchor is usually this.

## A session

At the start:

```bash
python tools/preflight.py
```

Checks what is cheap and silent when it fails — hooks wired, the sibling repositories
resolving, `app.py` still wholly CRLF. Runs no tests. Exit 1 if anything is wrong.

The slow check is the suite itself, run on its own:

```bash
python -m pytest tests/ -q
```

It prints the interpreter it ran under and the optional packages present beside its
own totals, under `-q` as well, so a count copied out of a run carries the conditions
it was taken under.

## The gate

Serving the real page in a real browser is the control that has caught the defects source
reading could not: a focus ring that painted nothing under a real Tab, a primary ink losing
at cascade, six controls at the wrong height, and a pointer decision that announced nothing.
Run it whenever `traktor_nml/gui/` changes. `../traktor-nml-tool-gate/README.md` has the
driving order; use `.venv`, since it is the only interpreter that can serve the page.

## Things that stay as they are

- **The parity manifest is never regenerated.** Non-regeneration is the check.
- **The gate fixture is never rebuilt** unless the measurements are being retaken.
  `gate_fixture.py` overwrites the exact fixture every recorded measurement was taken against.
- **Documentation describes the code as it stands** — no "previously", "used to", "now does",
  "no longer".
- **Never cite a source that does not say what you cite it for.** Re-measure inherited
  numbers rather than repeating them.
- **Every guard constructs its broken scenario in executable code**, and its docstring records
  the specific mutation and the specific observed output. Run it, read the value, then write it.
