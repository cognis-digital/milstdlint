# Demo 08 - Clean SECRET technical data package cover sheet

A correctly marked Technical Data Package (TDP) cover sheet (`tdp_cover.txt`)
mixing `(U)`, `(C)`, and `(S)` portions under a `SECRET` banner. Demonstrates
correct banner derivation when portions span multiple levels: the banner equals
the **highest** portion present.

## Where the data came from

A sanitized training stand-in for a TDP cover sheet (MIL-STD-31000 family).

## What to expect

`PASS`, no findings. Banner `S`, derived `S`. Exit 0.

## Run it

```sh
python -m milstdlint lint demos/08-clean-tdp/tdp_cover.txt
```

## How to act

Positive control for multi-level portion aggregation. If it fails, banner
derivation regressed.
