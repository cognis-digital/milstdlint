# Demo 06 - Formatting hygiene and the --strict gate

A technical-manual excerpt (`tm_formatting.txt`) that is correctly marked but
has formatting problems: a tab-indented paragraph and two over-length lines.
Shows the difference between the default gate and `--strict`.

## Where the data came from

A sanitized training stand-in for a TM page.

## Intentional defects

1. A paragraph starts with a tab character -> `FORMAT-TAB` (WARNING).
2. Two lines exceed the 100-character limit -> `FORMAT-LINE-LENGTH` (WARNING).

## What to expect

- Default: `PASS` with 3 warnings (warnings do not fail the build). Exit 0.
- `--strict`: warnings become errors -> `FAIL`. Exit 1.

## Run it

```sh
# Default — warnings only, exit 0
python -m milstdlint lint demos/06-line-length-tab/tm_formatting.txt

# Strict — promotes formatting warnings to errors, exit 1
python -m milstdlint lint --strict demos/06-line-length-tab/tm_formatting.txt
```

## How to act

Use `--strict` in CI when you want formatting hygiene to block a merge; leave it
off when you only want hard marking errors to fail.
