# Demo 09 - Unrecognized portion-marking token

A memo (`memo_bad_token.txt`) where one paragraph uses a portion token that is
not a valid classification level (`(XYZ)`). Catches typos and copy-paste errors
in portion marks before release.

## Where the data came from

A sanitized training stand-in for an internal memo.

## Intentional defect

`(XYZ)` is not a known level (`U`/`CUI`/`C`/`S`/`TS`) -> `PORTION-UNKNOWN`
(WARNING). The paragraph is treated as marked (so it does not also raise
`PORTION-MISSING`), but the token is flagged for review.

## What to expect

`PASS` by default (it is a warning), with one `PORTION-UNKNOWN` at L9. Exit 0.
Run with `--strict` to make it fail the gate.

## Run it

```sh
python -m milstdlint lint demos/09-unknown-token/memo_bad_token.txt

# Treat the bad token as a blocking error
python -m milstdlint lint --strict demos/09-unknown-token/memo_bad_token.txt
```

## How to act

Replace `(XYZ)` with the correct portion marking for that paragraph.
