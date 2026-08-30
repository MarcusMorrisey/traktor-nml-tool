# Resume: build-playlist planner workflow — plan-docs QR pass

## Context
We're using the `planner` skill (`C:\Users\marcu\.claude\skills\scripts\skills\planner\`) to plan a new `build-playlist` feature for the `traktor_nml` tool (a Traktor NML playlist-file manipulation CLI) at **`C:\codex\traktor-nml-tool`** (real git repo). The feature resolves an external plain-text track list against an existing NML collection and synthesizes a new playlist node.

State dir: **`C:\Users\marcu\AppData\Local\Temp\planner-a031gp_v`** — contains `context.json`, `plan.json` (the evolving plan), and `qr-plan-design.json` / `qr-plan-code.json` / `qr-plan-docs.json` (QR checklists per phase).

## Progress so far
- **plan-design phase**: architect produced the design; QR pass found and fixed ~16 real issues (DL/R-number collisions with the real package's own decision log, missing decisions, doc gaps). **56/56 QR items PASS.**
- **plan-code phase**: developer wrote real diffs for 13 code intents (`tracklist.py`, `buildplaylist.py`, `playlists.py`, `commands/build_playlist_cmd.py`, 2 new test files). QR pass found and fixed ~9 real bugs (a decision contradicting its own code, systematically wrong diff hunk-header line counts across ~13 diffs, dead/tautological validation code, unguarded UTF-8 decode, missing output-path refusal on `--unresolved-report`, weak tests). **35/35 QR items PASS.** Also fixed a real bug in the planner skill's own `skills/planner/cli/qr.py` (Windows `os.replace`-on-open-file bug) — durable fix, already applied.
- **plan-docs phase**: technical-writer added inline WHY-comments (doc_diffs) to existing code_changes. QR decompose found issues; **8/12 QR items now PASS** (`qa-201`/`201a`/`201b`/`201c`, `qa-202`/`202a`, `qa-203`, `qa-204`). Just fixed and marked `qa-204` PASS (a `tests/CLAUDE.md` row was missing a file reference — fixed).

## Remaining work (do this first)
**4 QR items still TODO in `qr-plan-docs.json`: `qa-205`, `qa-205a`, `qa-206`, `qa-207`** (groups `parent-qa-205`, `parent-qa-206`, `parent-qa-207`). Dispatch `quality-reviewer` subagents via the `Agent` tool, one group at a time (sequentially — **not in parallel**, see below), each running:
```
python3 -m skills.planner.quality_reviewer.plan_docs_qr_verify --step 1 --state-dir C:\Users\marcu\AppData\Local\Temp\planner-a031gp_v --qr-item qa-205 --qr-item qa-205a
```
(then separately for `qa-206`, then `qa-207`).

For each FAIL, read the finding, fix `plan.json` directly (Read/Edit tools — the orchestrator role normally forbids this, but for QR-driven fixes we do it directly rather than round-tripping through another subagent), then re-dispatch a fresh verify agent for that item. Record PASS/FAIL via:
```
python3 -m skills.planner.cli.qr --state-dir C:\Users\marcu\AppData\Local\Temp\planner-a031gp_v --qr-phase plan-docs update-item <id> --status PASS
```
(only when you've independently confirmed it yourself, or a subagent confirmed it).

## Critical known environment quirks (do not rediscover these the hard way)
1. **`context.json` FileNotFoundError with a mangled path** (e.g. `C:UsersmarcuAppDataLocalTempplanner-a031gp_v\context.json` — backslashes stripped) is a **known intermittent harness flake**, not a real missing file — the file genuinely exists. Tell dispatched agents: retry the exact same command up to twice; if it still fails, fall back to manual review directly against `plan.json` and the real repo, applying the same standard.
2. **NEVER trust the `patch` CLI tool for verification in this environment** — it has a confirmed, reproducible false-failure bug (rejects hunks whose content is verified byte-for-byte identical to the target; root cause not fully identified, possibly a Windows/MSYS Git-Bash `patch` 2.7.6 quirk). Tell every dispatched agent NOT to use it. Verify diffs by direct content/line reading instead.
3. **Diff hunk header arithmetic bugs were rampant** in this plan (the doc-writing subagent habitually declared wrong old/new line counts, and — more subtly — wrong **start lines** because later diffs in the same file's chain don't account for earlier diffs/doc_diffs shifting line numbers). The reliable fix method that worked: **content-anchor-based reconstruction** — for each file's diff chain, build the actual resulting text by literal substring search of each hunk's context text against the correctly-evolving prior content (starting from the real file on disk for existing files, or empty for new files), applying hunks strictly in `code_changes` list order (each intent's code diff, then its own doc_diff, then the next intent's...). This is far more reliable than line-number arithmetic. A working Python snippet for this is in the conversation history — recreate it if needed (it's straightforward: parse `@@ -old,n +new,n @@` headers, split hunk body into context/added/removed lines by leading `-`/`+`/` ` marker, find the context-before text as a literal substring in the running content, insert there).
4. **Bare empty-string context lines** (`""` instead of the required space-prefixed `" "`) inside hunk bodies caused silent miscounting in earlier fix attempts — when writing or checking diffs, make sure every unchanged blank line inside a hunk body is `" "` (single space), not `""`.
5. A one-off file **encoding corruption** (2 raw non-UTF-8 bytes, from a test fixture string `"Björk - Jóga"`) was found and fixed early in the plan-docs phase — if `json.load` on `plan.json` ever raises `UnicodeDecodeError` again, the fix pattern is: read raw bytes, find non-ASCII bytes (`b >= 0x80`), decode the specific offending byte(s) as cp1252/latin-1, re-encode as UTF-8, write back.
6. Always validate `plan.json` with `python3 -c "import json; json.load(open(r'...', encoding='utf-8'))"` after every edit.
7. Windows path gotcha: **always use `C:/...` (forward slashes with drive letter) or `C:\...` (Windows backslashes) in Python scripts — never bash-style `/c/...`** paths, since native Windows Python silently misinterprets `/c/...` as "root of current drive + literal folder named c", not drive C:. This caused a whole detour earlier.

## After plan-docs QR is fully green
Continue the orchestrator: `python3 -m skills.planner.orchestrator.planner --step <next>` (check via `--step 13` or whatever comes after doc QR routing — the pattern each phase follows is: `{phase}-work` → `{phase}-qr-decompose` → `{phase}-qr-verify` (per-group dispatch) → `{phase}-qr-route` (gate) → next phase). This should be the last planning phase before the plan is ready for real implementation (writing actual files to `C:\codex\traktor-nml-tool`) — confirm with the orchestrator's own output what comes next rather than assuming.

## User's working style established this session
- Wants genuine, independent QR verification at every step — not self-reported "PASS" claims taken at face value (this discipline caught dozens of real bugs).
- Fine with directly fixing `plan.json` yourself once a finding is confirmed, rather than always round-tripping through another subagent.
- Appreciates being told directly when you've made a mistake (e.g. an incorrect fix, a wrong reconstruction) rather than it being glossed over.
- Dispatch QR-verify subagents sequentially per group (not all-parallel) — running many QR-verify agents in parallel against the *same* shared `qr-plan-*.json` state file caused a **real data-loss race condition** earlier (state file got clobbered). Sequential is slower but safe.
