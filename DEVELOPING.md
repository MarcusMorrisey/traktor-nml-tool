# Developing this project

Setting up, and the invariants that are silent when they break. The README's
[Install](README.md#install) section covers the package and its extras; this covers
working *on* it.

## The layout

Three repositories, siblings, plus the handoff beside them:

```
C:\codex\
  traktor-nml-tool\             this repository - the tool and the wizard
  traktor-nml-tool-gate\        the serving gate and its fixtures
  traktor-nml-tool-plan\        the W-001..W-004 plan, archival
  CONTINUE-traktor-wizard.md    the handoff a new session reads first
```

Nothing hardcodes those paths. `tools/preflight.py`, `tools/refresh_handoff.py` and the
gate's `gate_paths.py` all resolve siblings from their own location, with an environment
variable overriding each for a tree that sits elsewhere:

| Variable | Overrides | Read by |
|---|---|---|
| `TRAKTOR_NML_TOOL` | this repository | the gate's `gate_paths.py` |
| `TRAKTOR_NML_TOOL_PLAN` | the plan repository | `tools/refresh_handoff.py` |
| `TRAKTOR_NML_TOOL_GATE` | the gate repository | `tools/refresh_handoff.py` |
| `TRAKTOR_WIZARD_HANDOFF` | the handoff file | `tools/refresh_handoff.py` |

The one that is *not* overridable is this repository as `refresh_handoff.py` sees it: that
file lives here, so `tools/../` is the only tree it can be describing, and an override would
let it rewrite one repository's facts from another's.

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
| Suite | **416 passed, 3 skipped** | **417 passed, 2 skipped** |

The whole of that difference is `pyacoustid` and the chromaprint library it needs. The
handoff records the system pair, so `tools/refresh_handoff.py` refuses to run under an
interpreter carrying `nicegui` rather than writing the other pair in — not because that pair
is wrong, but because the two mean different things and only one is what the document says.

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

- `traktor_nml/gui/app.py` is wholly CRLF, 1388 of them and no bare LF.
  `tests/test_gui_line_endings.py` asserts it and `tools/preflight.py` reports it.
- The patch sets under `docs/plans/*/scratch/` are CRLF because that is what they were
  captured from. A rewritten one produces phantom rejects when reapplied.
- `tests/baselines/manifest.json` is pinned by SHA-256 over its exact bytes.

`.gitattributes` sets `* -text`, so git stores and checks out bytes unchanged. Without it a
clone on a stock Windows git — `core.autocrlf=true` is the installer's default — normalises
the CRLF files to LF in the index on the next commit and checks the LF files out as CRLF,
across the whole tree at once. Both sibling repositories carry the same line.

When editing, read and write with `newline=''` so the file keeps its own endings. An
exact-match edit that "cannot find" its anchor is usually this.

## A session

At the start:

```bash
python tools/preflight.py
```

Checks what is cheap and silent when it fails — hooks wired, the sibling repositories
resolving, `app.py` still wholly CRLF. Runs no tests. Exit 1 if anything is wrong.

At the end, before writing the handoff:

```bash
python tools/refresh_handoff.py --check
```

Runs the full suite to derive the handoff's counts and reports which of its facts have
drifted; exit 1 when any has. Drop `--check` to rewrite them. It then names the facts it
cannot derive — the repositories' file counts, the browser-record count, the backlog and the
deferrals — because those need a person.

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
