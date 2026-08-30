--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -40,6 +40,10 @@
   source byte span. `playlists.py`'s UUID-marker locator is gone, so a
   playlist whose `PLAYLIST` child carries no UUID is still located and no
   locator rescans the document per element (DL-014, DL-021).
+- `splice_cmd` and `split_cmd` read, parse and write through helpers
+  exported from `rewrite.py` rather than carrying their own input handling
+  and a plain `write_bytes`, so both inherit the diagnostics and the atomic
+  write `write_nml_safely` already implements (DL-019).
 
 ## Invariants
 
@@ -47,6 +51,15 @@
 - Every write command builds its complete output in memory and validates
   it before any file handle opens; a failure partway through conflict
   resolution or reference redirection leaves every output path untouched
   (DL-012).
+- Every output file is additionally committed through a temp file plus
+  `os.replace` so a destination holds either its previous bytes or the
+  complete new bytes (DL-019). Split's multi-output write loop is not
+  transactional across files - a failure partway through leaves earlier
+  groups written - accepted because cross-file staging and commit is new
+  machinery (DL-022).
+- A malformed input yields `xml_parse_error` naming the file and exit code
+  2 from every write command, splice and split included, never an escaping
+  parser exception (DL-019).
 - `reconnect.py`'s one-to-one assignment guarantee (DL-004) and
   `volumes.py`'s explicit-VOLUME/VOLUMEID requirement (DL-005) are both
