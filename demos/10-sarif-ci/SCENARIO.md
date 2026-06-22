# Demo 10 - SARIF 2.1.0 output for GitHub code scanning

A release-gate sample (`release_gate.txt`) with several defects, exported as
SARIF 2.1.0 so findings appear inline in GitHub's "Code scanning" tab (or any
SARIF viewer / Azure DevOps).

## Where the data came from

A sanitized training stand-in built to trigger multiple rules at once.

## Defects present

- Top banner `CONFIDENTIAL`, bottom banner `SECRET` -> `BANNER-MISMATCH` (error)
- An unmarked paragraph -> `PORTION-MISSING` (error)
- No `Date:` front matter -> `FRONTMATTER-DATE` (warning)

## What to expect

`--format sarif` prints a valid SARIF log: `version` `2.1.0`, a `runs[0].tool.
driver.rules` catalog of the triggered rules, and one `result` per finding with
`level` (`error`/`warning`/`note`) and a `startLine` region.

## Run it

```sh
# Emit SARIF
python -m milstdlint lint demos/10-sarif-ci/release_gate.txt --format sarif

# Save for upload to GitHub code scanning
python -m milstdlint lint demos/10-sarif-ci/release_gate.txt --format sarif > milstdlint.sarif
```

Example CI step:

```yaml
- run: python -m milstdlint lint docs/**/*.txt --format sarif > milstdlint.sarif
  continue-on-error: true
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: milstdlint.sarif
```

## How to act

Open the Code scanning tab after the SARIF upload; each finding links to the
exact line. Fix the marking/format defects and re-run.
