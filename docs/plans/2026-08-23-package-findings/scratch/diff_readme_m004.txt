--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -36,7 +36,15 @@
 - `--match-confidence` is one ordered enum (strict/loose/filename) rather
   than a second boolean flag, because disk-scan matching's filename-only
   tier and tag-based matching's artist-title-only tier are really one
   cascade, not two independent knobs (DL-010).
+- `spans.py` builds one `SpanIndex` per source document in a single pass -
+  one pre-order walk for per-tag ordinals, one token scan for opening-tag
+  offsets - and it is the only mechanism that maps a parsed element to its
+  source byte span. `playlists.py`'s UUID-marker locator is gone, so a
+  playlist whose `PLAYLIST` child carries no UUID is still located and no
+  locator rescans the document per element (DL-014, DL-021).
 
 ## Invariants
 
@@ -60,5 +68,8 @@
   location - an extension of the DL-005 explicit-identity invariant
   above, not an exception to it (DL-017, DL-018).
+- An element is located in source by tree identity through one `SpanIndex`
+  per document, never by searching for an attribute value and never by a
+  second locator (DL-014, DL-021).
 - The NML schema (COLLECTION/PLAYLISTS/SUBNODES/PRIMARYKEY shapes and
   their count attributes) is confirmed only against NML VERSION=20 /
   Traktor Pro 4; `spans.py`'s count-attribute recalculation is generic
