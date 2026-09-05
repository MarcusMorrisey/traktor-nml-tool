# The vendored typeface

`theme.py`'s `FONT_SANS` and `FONT_MONO` name IBM Plex, and `fonts/`
holds the faces that make those names paint. Naming a family the page
cannot load is silent: the browser walks the stack to the next entry it
has, so the page renders in Segoe UI and Consolas while the stylesheet
says IBM Plex, and nothing reports it. The measurement that found it
compared the two stacks against known families in the served page's own
canvas: the sans stack drew a test string at 485.5078125px, identical to
`system-ui` and to `"Segoe UI"`, and the mono stack at 615.78125px,
identical to `Consolas`.

## What is vendored, and from where

The seven faces `design/reconnect-wizard/Main.dc.html` line 11 imports:
IBM Plex Sans 400/500/600/700 and IBM Plex Mono 400/500/600. No italic,
because no artboard sets one.

Upstream is IBM's own npm publication of the families, `@ibm/plex-sans`
and `@ibm/plex-mono`, both at version **1.1.0**, taken from the
`fonts/complete/woff2/` directory of each package. The files are
committed unmodified and unsubsetted (DL-167).

| File | Family, weight | Bytes | SHA-256 |
|---|---|---|---|
| `IBMPlexSans-Regular.woff2` | Sans 400 | 63020 | `ba711a3085ff9f27440b6b9c4550cfc47c97bf36591d5da958b975bb3add8c1a` |
| `IBMPlexSans-Medium.woff2` | Sans 500 | 66740 | `5660f8a658f8bb50dbc005232f885eadffd2bc1c235c4f6fbb63469d1f9cde6d` |
| `IBMPlexSans-SemiBold.woff2` | Sans 600 | 67060 | `f78048030eab62e860efa39a0df79e2e5581bf122eb95b9bc42c0b8a4988d205` |
| `IBMPlexSans-Bold.woff2` | Sans 700 | 63012 | `fa7130d854a660b39a7fc9e6e0f2dc23dba5f1346e2adea3e1fe37b6d884133d` |
| `IBMPlexMono-Regular.woff2` | Mono 400 | 45640 | `49ce58b41a0e1cb921c0f58d9a5b8b96a2cc21437c7066f3ba4f24873076d131` |
| `IBMPlexMono-Medium.woff2` | Mono 500 | 46724 | `8c2c290cbd998fa1f647e4572aca6ebbd72589551b0f3f9f8bb8628fbb8219d5` |
| `IBMPlexMono-SemiBold.woff2` | Mono 600 | 47016 | `ed5eaca7522336959d6c3810bd9bb78424f0d964082d581bfbea169ee08d14e3` |

The measured total is **399212 bytes** across the seven faces, and
`tests/test_gui_font_assets.py` asserts each file against its size and
hash above and the directory against that total. A ceiling picked for
looking generous admits any drift beneath it; the measured total names
what is there, so a face swapped for another is a guard failure and a
decision rather than a quiet gain (DL-176).

`OFL.txt` beside the faces is the licence they ship under, SIL Open Font
License 1.1 (DL-166).

## How they reach the page

`theme.py` holds `FONT_URL_BASE` and `FONT_FACES` and emits one
`@font-face` block per entry; `app.py` mounts the directory at that same
constant. The src and the route that answers it are one fact, and
`theme.py` may not import nicegui (DL-069), so the constant lives on the
nicegui-free side and the mount reads it (DL-164).

The mount is `nicegui.app.app.add_static_files`, whose signature in the
installed **nicegui 3.16.0** is
`(url_path: str, local_directory: str | Path, *, follow_symlink: bool = False, max_cache_age: int = 3600) -> None`.
That reading is recorded here because no guard can execute the mount:
the suite runs under the system interpreter, which has no nicegui
(DL-174, DL-178).

`_mount_fonts()` is called from `_page_chrome`, which both pages call,
and it is idempotent because nicegui raises on a route mounted twice.

## What the guards can and cannot see

No guard asserts a font-family name on its own. `theme.FONT_SANS`
already named IBM Plex throughout the period the page painted Segoe UI,
and `document.fonts.check('14px "IBM Plex Sans"')` returns `True` for an
absent face, so a name assertion is true in exactly the broken state
(DL-165). The guards read the files, their sizes and hashes, the count
and content of the emitted `@font-face` blocks, and the argument the
mount is given. What none of them can read is whether the face actually
painted; that is a served-page reading, and it belongs to the record
DL-180 requires.
