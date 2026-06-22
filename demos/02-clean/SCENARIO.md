# Demo 02 - Clean UNCLASSIFIED document (baseline)

A correctly marked UNCLASSIFIED public-affairs talking-points sheet
(`clean_unclassified.txt`). Use it as a known-good baseline: the linter must
report **zero** findings and exit 0.

## Where the data came from

A sanitized stand-in for a routine public-affairs product. Every line is
illustrative training content only; no real program data.

## What to expect

`PASS`, no findings, banner `U`, derived `U`.

## Run it

```sh
python -m milstdlint lint demos/02-clean/clean_unclassified.txt
```

## How to act

If this file ever starts producing findings, your build environment or a rule
change broke a known-good baseline — investigate before trusting other results.
