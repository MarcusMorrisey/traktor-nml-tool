    old_records = collection_records(old_root)
    cache = TagCache(args.cache)
    candidates = index_scan_roots(args.scan_roots, cache, refresh_cache=args.refresh_cache)
    confidence = resolve_confidence(args)

    key_providers = []
    fingerprint_stats: dict[str, int] = {}
    if getattr(args, "fingerprint", False):
        if fingerprint_key_provider is None:
            raise _FingerprintUnavailable(
                "fingerprint_key_provider unavailable (traktor_nml.fingerprint not installed)"
            )
        if not HAS_ACOUSTID:
            # The module imported fine but its own dependency probe failed
            # (pyacoustid and/or the fpcalc binary are absent) - the fingerprint
            # tier is then a silent no-op (see fingerprint.py's own gate), so
            # that must be surfaced here rather than left undiagnosed, matching
            # the xmlio.HAS_LXML fallback's own diagnostic style.
            print(
                "fingerprint_dependency_missing=pyacoustid/fpcalc not available; "
                "--fingerprint tier will find no matches",
                file=sys.stderr,
            )
        key_providers.append(fingerprint_key_provider(cache, candidates, fingerprint_stats))

    mapping, stats, ambiguity_rows = resolve_reconnection(
        old_records, candidates, confidence, key_providers
    )
    stats = {**fingerprint_stats, **stats}

    # Re-encode each winning candidate's real absolute path into a proper
    # LOCATION using its scan root's resolved volume identity - the
    # placeholder LocationParts a disk-scan candidate carries has no real
    # VOLUME/VOLUMEID and is never written as-is.
    volume_map = parse_volume_map(args.volume_map)
    volume_identities: dict[Path, tuple[str, str]] = {}
    for scan_root in args.scan_roots:
        volume_identities[Path(scan_root)] = resolve_volume_identity(scan_root, old_records, volume_map)

    for candidate in mapping.values():
        if candidate.source_path is None:
            continue
        for scan_root, identity in volume_identities.items():
            try:
                candidate.source_path.relative_to(scan_root.resolve())
            except ValueError:
                continue
            candidate.location = location_from_disk_path(candidate.source_path, *identity)
            break

    cache.flush()
    return mapping, stats, ambiguity_rows, old_records
