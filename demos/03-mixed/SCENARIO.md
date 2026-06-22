# Demo 03 - Mixed document (good content with two defects)

A SECRET operations-order excerpt (`oporder_mixed.txt`) that is mostly correct
but has two realistic problems an editor would miss on a quick read.

## Where the data came from

A sanitized training stand-in for an OPORD excerpt. All content is illustrative
only; no real operational detail.

## Intentional defects

1. One coordinating-instruction line has **no portion marking** ->
   `PORTION-MISSING` (ERROR).
2. The front matter has a `Document ID:` but **no `Date:`** ->
   `FRONTMATTER-DATE` (WARNING).

Banner (`SECRET`) and the highest portion (`(S)`) agree, so there is no
banner/portion mismatch — this shows the linter isolating real defects without
false positives on the parts that are correct.

## What to expect

`FAIL`: 1 error (`PORTION-MISSING` at L8), 1 warning (`FRONTMATTER-DATE`).
Exit code 1.

## Run it

```sh
python -m milstdlint lint demos/03-mixed/oporder_mixed.txt
```

## How to act

Add a portion marking to the flagged line and a `Date:` front-matter line, then
re-run — it should pass.
