# AUDIO_ID collisions on the real library

Measured 2026-10-04 over three collections, for the one M-001 promotion
threshold that needs only a collection to measure. `spike/dedupe/measure.py`
is the spike that produces the artifact; this is evidence for one of its
three gates, not the artifact.

| Collection | Entries | Carrying AUDIO_ID | Shared AUDIO_IDs | Durations disagree |
|---|---|---|---|---|
| `$COLLECTION2026-08-31-reconnected.nml` | 12,805 | 12,799 | 289 | 0 |
| `traktor\collection.nml` | 4,677 | 4,667 | 288 | 0 (1 unreadable) |
| `$COLLECTION2024_10_23.nml` | 10,460 | 10,455 | 9 | 0 |

**586 AUDIO_ID values are held by more than one entry, and none spans
entries whose PLAYTIME_FLOAT disagrees.** No full-length track in these
collections shares an AUDIO_ID with different audio.

## Why the count is taken on duration

`plan.md`'s promotion rule states false collisions as pairs sharing an
AUDIO_ID whose artist, title or duration disagree. Counted that way the
same three collections give 32, and inspecting those rows shows nearly
all are one file catalogued under two spellings:

```
'Lipps Inc.' / 'Funkytown (instrumental)'   filesize=8964  playtime=282.600006
'Lipps Inc.' / 'Funkytown'                  filesize=8964  playtime=282.600006
```

Equal FILESIZE, PLAYTIME_FLOAT and BITRATE: one file, titled twice. A
tagging difference is not a fingerprint failure, which is why
`false_collisions` treats a pair agreeing on all three measured values as
one file catalogued twice.

## The collision the duration test cannot see

`Kenkeni 016.flac` and `Kenkeni 017.flac` share an AUDIO_ID, a FILESIZE
of 456 and a PLAYTIME_FLOAT of 0.806984, differing only at BITRATE
613000 against 614000. They are two 0.8-second percussion loops: a real
collision, carried by the count because BITRATE differs, and invisible to
a duration test alone. A fingerprint has little to work with under a
second, which argues for excluding very short entries from tier 3's
grouping - not from this count, where the collision belongs.

## What this does not establish

**Two of the three thresholds are unmeasured.** Re-analysis stability and
copy agreement need a collection Traktor re-analysed and a folder of
byte-identical and format-converted copies. Tier 3 is not promotable on
this evidence alone, and `2026-09-26-dedupe-spike.md` stands as a
template until the spike is run.

**These are three collections on one machine.** Nothing here measures
AUDIO_ID across machines or Traktor versions.

## Why it matters that this exists

On the same collections, 982 diverging groups are one recording stored
under two filenames, 98.4% of them agreeing on AUDIO_ID - the case tier 3
names. See `2026-10-04-metadata-tier-reach.md`.
