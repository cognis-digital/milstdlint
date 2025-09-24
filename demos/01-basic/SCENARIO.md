# Demo 01 - Basic classification-marking lint

This demo shows MILSTDLINT catching real DoD/MIL-STD documentation defects in a
sample SECRET working paper (`sample_secret_memo.txt`).

## What the sample contains (intentional defects)

1. The overall banner at the top says `CONFIDENTIAL`, but a paragraph carries a
   `(S)` (SECRET) portion marking. Under DoDM 5200.01 the banner must reflect
   the **most restrictive** portion, so this is a `BANNER-PORTION-MISMATCH`
   error (the document is under-marked).
2. The bottom banner says `SECRET` while the top says `CONFIDENTIAL` -> a
   `BANNER-MISMATCH` error (top and bottom must be identical).
3. One paragraph has **no portion marking** -> `PORTION-MISSING` error.
4. Missing `Date:` front matter -> `FRONTMATTER-DATE` warning.
5. Trailing whitespace on a line -> `FORMAT-TRAILING-WS` warning.

## Run it

```sh
# Human-readable table
python -m milstdlint lint demos/01-basic/sample_secret_memo.txt

# Machine-readable JSON for piping into compliance pipelines
python -m milstdlint lint demos/01-basic/sample_secret_memo.txt --format json
```

The command exits non-zero because ERROR-severity findings are present, so it
can gate a CI / document-release pipeline.

## Expected outcome

`FAIL` with several ERROR findings (banner/portion mismatches, missing portion
mark) and a couple of WARNINGs (front matter, formatting).
