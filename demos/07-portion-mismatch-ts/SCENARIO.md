# Demo 07 - Banner under-marks a TOP SECRET portion

An intelligence-summary excerpt (`intsum_undermarked.txt`) banner-marked SECRET
that contains a `(TS)` TOP SECRET portion. Under DoDM 5200.01 the banner must
reflect the most restrictive portion, so the document is under-marked — a
serious spillage-adjacent defect.

## Where the data came from

A sanitized training stand-in for an INTSUM. All content is illustrative; no
real intelligence.

## Intentional defect

Highest portion `(TS)` exceeds the `SECRET` banner ->
`BANNER-PORTION-MISMATCH` (ERROR).

## What to expect

`FAIL`: banner `S`, derived `TS`, one `BANNER-PORTION-MISMATCH` error at L1.
Exit code 1.

## Run it

```sh
python -m milstdlint lint demos/07-portion-mismatch-ts/intsum_undermarked.txt
```

## How to act

Either raise the top and bottom banner to `TOP SECRET`, or move/declassify the
`(TS)` content. Under-marking is the case to never ship.
