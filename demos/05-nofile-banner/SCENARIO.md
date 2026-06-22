# Demo 05 - Missing overall classification banner

A draft SOP (`draft_no_banner.txt`) where every paragraph is portion-marked but
the author forgot the overall banner lines at top and bottom. This is the most
common release-blocking defect.

## Where the data came from

A sanitized training stand-in for a draft pasted out of a word processor.

## Intentional defect

No banner lines at all -> `BANNER-MISSING` (ERROR, document-level).

## What to expect

`FAIL`: banner `-`, derived `U` (from the portion marks). One `BANNER-MISSING`
error. Exit code 1.

## Run it

```sh
python -m milstdlint lint demos/05-nofile-banner/draft_no_banner.txt
```

## How to act

Add an `UNCLASSIFIED` banner line as the first and last content line of the
document, then re-run.
