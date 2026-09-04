# hooks/

The tracked git hooks, which `git config core.hooksPath hooks` is what makes live.

## Files

| File       | What                                                                                                                                                                                                                                                     | When to read                                                                                        |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `pre-push` | POSIX-sh hook refusing to delete or move a `parity-baseline-*` tag, the local stand-in for GitHub tag protection; a baseline change needs a new `parity-baseline-vN+1` tag. Deliberate re-baselining bypasses it with `git push --no-verify`. Inert until `core.hooksPath` is set, which `tools/preflight.py` checks | Re-baselining the parity oracle, adding a protected tag pattern, or diagnosing a refused tag push |
