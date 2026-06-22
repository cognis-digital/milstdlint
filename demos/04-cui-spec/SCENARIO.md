# Demo 04 - Clean CUI interface control document

A correctly marked Controlled Unclassified Information (CUI) Interface Control
Document (`cui_interface_spec.txt`). Demonstrates that `CUI` is handled as a
first-class banner/portion level between `U` and `C`.

## Where the data came from

A sanitized training stand-in for an ICD. Marking conventions follow 32 CFR
2002 / DoDM 5200.01; all technical content is illustrative only.

## What to expect

`PASS`, no findings. Banner `CUI`, derived `CUI`. Exit 0.

## Run it

```sh
python -m milstdlint lint demos/04-cui-spec/cui_interface_spec.txt
```

## How to act

This is a positive control for CUI handling. If it fails, a CUI-related rule
regressed.
