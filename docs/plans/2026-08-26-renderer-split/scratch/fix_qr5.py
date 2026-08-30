# -*- coding: utf-8 -*-
import json

PATH = r"C:\Users\marcu\AppData\Local\Temp\planner-e70yv3f4\plan.json"
p = json.load(open(PATH, encoding="utf-8"))

ccs = {}
cis = {}
for m in p["milestones"]:
    for cc in m.get("code_changes", []):
        ccs[cc["id"]] = cc
    for ci in m.get("code_intents", []):
        cis[ci["id"]] = ci


def bump(obj):
    obj["version"] = obj.get("version", 1) + 1


# =====================================================================
# qa-011 + qa-023 + qa-021: run_reconnection absorbed the whole pipeline
# into one ~106-line body (a god function) and never terminated the
# FpcalcSession it opens. Split into three helpers - volume-identity
# resolution, fingerprint-tier construction, and LOCATION re-encoding -
# and wrap the matching call in try/finally so the session is always
# terminated before the function returns, regardless of which path
# resolve_reconnection takes. Also drops the plan-local "(DL-009)" tag.
# =====================================================================
cc = ccs["CC-M-002-004"]
new_body = '''--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -105,3 +105,150 @@ class RewriteReconnectResult:
     reconnect: Optional[ReconnectResult]
     csv_path: Optional[Path]
     error: Optional[str]
+
+
+def _resolve_volume_identities_and_mounts(
+    args: argparse.Namespace, old_records: list[EntryRecord]
+) -> tuple[dict[Path, tuple[str, str]], dict[tuple[str, str], list[Path]]]:
+    """Resolve each scan root's volume identity once, up front: both the
+    fingerprint tier's old-side resolver and the candidate-side LOCATION
+    re-encoding reuse the same resolved identities rather than resolving
+    twice.
+    """
+    volume_map = parse_volume_map(args.volume_map)
+    volume_identities: dict[Path, tuple[str, str]] = {}
+    for scan_root in args.scan_roots:
+        volume_identities[Path(scan_root)] = resolve_volume_identity(scan_root, old_records, volume_map)
+
+    # known_mounts anchors each scan root at its own filesystem anchor (the
+    # drive letter or POSIX root, e.g. "C:\\\\" or "/"), never at scan_root
+    # itself - decoded_path is volume-relative (relative to the volume
+    # root), not relative to an arbitrary scan-root subdirectory, so
+    # anchoring at scan_root would reconstruct the wrong absolute path for
+    # every record whose file sits outside that particular subdirectory.
+    known_mounts: dict[tuple[str, str], list[Path]] = {}
+    for scan_root, identity in volume_identities.items():
+        anchor = Path(scan_root).anchor
+        if anchor:
+            known_mounts.setdefault(identity, []).append(Path(anchor))
+    return volume_identities, known_mounts
+
+
+def _build_fingerprint_tier(
+    args: argparse.Namespace,
+    cache: TagCache,
+    candidates: list[EntryRecord],
+    known_mounts: dict[tuple[str, str], list[Path]],
+):
+    """Build the fingerprint key provider when --fingerprint is set, or
+    return an empty tier when it is not. The returned session (or None)
+    is the caller's to terminate once resolve_reconnection has finished
+    with it - this function only opens it, because the fingerprint
+    provider's provide() closure fingerprints old-side records lazily
+    during matching, after this function has already returned.
+    """
+    key_providers = []
+    fingerprint_stats: dict[str, int] = {}
+    warnings: list[str] = []
+    if not getattr(args, "fingerprint", False):
+        return key_providers, fingerprint_stats, warnings, None
+
+    if fingerprint_key_provider is None:
+        raise _FingerprintUnavailable(
+            "fingerprint_key_provider unavailable (traktor_nml.fingerprint not installed)"
+        )
+    unavailable = fingerprint_unavailable_reason()
+    if unavailable is not None:
+        # Every way this tier can be unusable degrades to matching
+        # nothing, so an undiagnosed run looks exactly like one that
+        # searched and found no candidates. The reason is named rather
+        # than the dependency set listed, because the three pieces fail
+        # independently and "pyacoustid/fpcalc not available" is wrong
+        # advice when the missing piece is the chromaprint library and
+        # both of those are installed.
+        warnings.append(
+            f"fingerprint_dependency_missing={unavailable}; "
+            "--fingerprint tier will find no matches"
+        )
+    # The session owns the fpcalc child, so a per-file timeout is
+    # enforceable and a caller can terminate one mid-fingerprint.
+    fpcalc_session = FpcalcSession(timeout=getattr(args, "fpcalc_timeout", FPCALC_TIMEOUT_SECONDS))
+    key_providers.append(
+        fingerprint_key_provider(cache, candidates, fingerprint_stats, known_mounts, fpcalc_session)
+    )
+    return key_providers, fingerprint_stats, warnings, fpcalc_session
+
+
+def _reencode_winning_locations(
+    mapping: dict[str, EntryRecord], volume_identities: dict[Path, tuple[str, str]]
+) -> None:
+    """Re-encode each winning candidate's real absolute path into a
+    proper LOCATION using its scan root's resolved volume identity - the
+    placeholder LocationParts a disk-scan candidate carries has no real
+    VOLUME/VOLUMEID and is never written as-is.
+    """
+    for candidate in mapping.values():
+        if candidate.source_path is None:
+            continue
+        for scan_root, identity in volume_identities.items():
+            try:
+                candidate.source_path.relative_to(scan_root.resolve())
+            except ValueError:
+                continue
+            candidate.location = location_from_disk_path(candidate.source_path, *identity)
+            break
+
+
+def run_reconnection(
+    args: argparse.Namespace,
+    old_root,
+    *,
+    on_progress: Optional[Callable[[int, int, Path], None]] = None,
+    cancel=None,
+) -> ReconnectResult:
+    """Run the whole reconnection pipeline and return a ReconnectResult.
+
+    on_progress and cancel are forwarded verbatim to index_scan_roots,
+    which already accepts both; both default to None so the CLI path
+    indexes exactly as it does without them, and a GUI gets live indexing
+    progress and a cancel token without bypassing this core.
+    ScanCancelled propagates rather than becoming a field on the result:
+    a short candidate list is indistinguishable from a complete one, so a
+    partial result would report most of the collection as missing - a
+    wrong answer delivered confidently.
+    """
+    old_records = collection_records(old_root)
+    cache = TagCache(args.cache)
+    candidates = index_scan_roots(
+        args.scan_roots, cache, refresh_cache=args.refresh_cache,
+        on_progress=on_progress, cancel=cancel,
+    )
+    confidence = resolve_confidence(args)
+
+    volume_identities, known_mounts = _resolve_volume_identities_and_mounts(args, old_records)
+    key_providers, fingerprint_stats, warnings, fpcalc_session = _build_fingerprint_tier(
+        args, cache, candidates, known_mounts
+    )
+    try:
+        # fpcalc_session, when the fingerprint tier is active, is opened
+        # by _build_fingerprint_tier above and its child process must not
+        # outlive this function: resolve_reconnection is the last
+        # consumer (its provide() closure fingerprints old-side records
+        # lazily during matching), so the session is terminated here
+        # regardless of how matching finishes.
+        mapping, stats, ambiguity_rows = resolve_reconnection(
+            old_records, candidates, confidence, key_providers,
+            refute=should_refute(args),
+        )
+    finally:
+        if fpcalc_session is not None:
+            fpcalc_session.terminate()
+    stats = {**fingerprint_stats, **stats}
+
+    _reencode_winning_locations(mapping, volume_identities)
+
+    cache.flush()
+    return ReconnectResult(mapping, stats, ambiguity_rows, old_records, warnings)
'''
cc["diff"] = new_body
bump(cc)
print("CC-M-002-004 rewritten (fpcalc close + decomposition)")

# Update the intent to describe the decomposition and drop plan-local tags.
ci = cis["CI-M-002-002"]
ci["behavior"] = (
    "Signature run_reconnection(args, old_root, *, on_progress=None, cancel=None) -> ReconnectResult. "
    "on_progress and cancel are forwarded verbatim to index_scan_roots (traktor_nml/diskscan.py:155), "
    "which already accepts both; both default to None so the CLI path indexes exactly as it does today, "
    "and a GUI gets live indexing progress and a cancel token without bypassing the core. The pipeline is "
    "split across three helpers rather than inlined in one body: "
    "_resolve_volume_identities_and_mounts (one up-front resolution reused by both the fingerprint key "
    "provider and the LOCATION re-encoding), _build_fingerprint_tier (the optional FpcalcSession-owned key "
    "provider), and _reencode_winning_locations, so run_reconnection itself stays a short orchestration of "
    "collection_records, TagCache, index_scan_roots, the three helpers, resolve_reconnection and "
    "cache.flush. The FpcalcSession _build_fingerprint_tier opens is terminated in a try/finally around the "
    "resolve_reconnection call, because resolve_reconnection's fingerprint provide() closure is the last "
    "consumer of the session's fpcalc child; no session escapes run_reconnection. The two fingerprint "
    "failure modes stay distinct: fingerprint_key_provider being None still raises _FingerprintUnavailable, "
    "while a non-None fingerprint_unavailable_reason() is appended to warnings instead of being printed to "
    "stderr. warn_refutation_disabled is not called here. ScanCancelled propagates."
)
bump(ci)
print("CI-M-002-002 behavior updated")

json.dump(p, open(PATH, "w", encoding="utf-8"), indent=2)
print("ok - stage 4")
