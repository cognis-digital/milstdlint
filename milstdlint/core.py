"""Core lint engine for MILSTDLINT.

Standard library only. No network access.

The engine is rule-based. Each rule inspects a parsed document and emits zero or
more Finding objects. Rules model a defensible subset of DoD / MIL-STD
documentation conventions:

  - DoDM 5200.01 / ISOO marking conventions: overall (banner) markings appear at
    the top and bottom of the document; each portion (paragraph) carries a
    portion marking like ``(U)``, ``(CUI)``, ``(C)``, ``(S)``, ``(TS)``.
  - MIL-STD-963 style front matter: a document identifier and a date.
  - General formatting hygiene used across MIL-STD deliverables.

Nothing here controls hardware or weapons; it only reads and reports on text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# Ordered from least to most restrictive. Used for banner derivation.
CLASSIFICATION_LEVELS = [
    "U",      # UNCLASSIFIED
    "CUI",    # Controlled Unclassified Information
    "C",      # CONFIDENTIAL
    "S",      # SECRET
    "TS",     # TOP SECRET
]

_BANNER_ALIASES = {
    "UNCLASSIFIED": "U",
    "U": "U",
    "CUI": "CUI",
    "CONTROLLED UNCLASSIFIED INFORMATION": "CUI",
    "CONFIDENTIAL": "C",
    "C": "C",
    "SECRET": "S",
    "S": "S",
    "TOP SECRET": "TS",
    "TS": "TS",
}

# A portion marking at the start of a paragraph, e.g. "(U)", "(CUI)", "(S//NF)".
PORTION_MARK_RE = re.compile(r"^\s*\(([A-Z]{1,3})(?://[A-Z/]+)?\)\s*")

# A banner line is a line that is ONLY a classification token (optionally with
# control markings) and nothing else of substance.
_BANNER_RE = re.compile(
    r"^\s*(UNCLASSIFIED|CUI|CONTROLLED UNCLASSIFIED INFORMATION|CONFIDENTIAL|SECRET|TOP SECRET|U|C|S|TS)"
    r"(\s*//\s*[A-Z0-9/ ]+)?\s*$"
)

_FRONT_MATTER_ID_RE = re.compile(r"^\s*(document\s+(id|identifier)|doc\s*id)\s*[:=]", re.IGNORECASE)
_FRONT_MATTER_DATE_RE = re.compile(r"^\s*date\s*[:=]", re.IGNORECASE)

MAX_LINE_LEN = 100


@dataclass
class Finding:
    rule: str
    severity: Severity
    line: int          # 1-based; 0 means document-level
    message: str
    excerpt: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class LintResult:
    path: str
    findings: List[Finding] = field(default_factory=list)
    derived_banner: Optional[str] = None
    declared_banner: Optional[str] = None

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def ok(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "ok": self.ok,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "derived_banner": self.derived_banner,
            "declared_banner": self.declared_banner,
            "findings": [f.to_dict() for f in self.findings],
        }


def _normalize_level(token: str) -> Optional[str]:
    return _BANNER_ALIASES.get(token.strip().upper())


def _level_rank(level: str) -> int:
    try:
        return CLASSIFICATION_LEVELS.index(level)
    except ValueError:
        return -1


def _banner_level_of_line(line: str) -> Optional[str]:
    m = _BANNER_RE.match(line)
    if not m:
        return None
    return _normalize_level(m.group(1))


def _highest(levels: List[str]) -> Optional[str]:
    ranked = [(_level_rank(l), l) for l in levels if _level_rank(l) >= 0]
    if not ranked:
        return None
    return max(ranked, key=lambda t: t[0])[1]


def lint_text(text: str, path: str = "<text>", strict: bool = False) -> LintResult:
    """Lint a document given as text. Returns a LintResult.

    If ``strict`` is True, formatting WARNINGs are promoted to ERRORs so that
    they affect the exit status.
    """
    lines = text.splitlines()
    result = LintResult(path=path)

    # --- Collect banner lines (overall markings) -------------------------
    banner_levels: List[str] = []
    first_banner_line = None
    last_banner_line = None
    for idx, line in enumerate(lines, start=1):
        lvl = _banner_level_of_line(line)
        if lvl is not None:
            banner_levels.append(lvl)
            if first_banner_line is None:
                first_banner_line = idx
            last_banner_line = idx

    declared_banner = _highest(banner_levels) if banner_levels else None
    result.declared_banner = declared_banner

    # --- Collect portion markings ---------------------------------------
    portion_levels: List[str] = []
    body_paragraph_lines = []  # (lineno, text) for non-blank, non-banner lines
    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if _banner_level_of_line(line) is not None:
            continue
        if _FRONT_MATTER_ID_RE.match(line) or _FRONT_MATTER_DATE_RE.match(line):
            continue
        body_paragraph_lines.append((idx, line))
        m = PORTION_MARK_RE.match(line)
        if m:
            lvl = _normalize_level(m.group(1))
            if lvl is not None:
                portion_levels.append(lvl)
            else:
                result.findings.append(Finding(
                    rule="PORTION-UNKNOWN",
                    severity=Severity.WARNING,
                    line=idx,
                    message=f"Unrecognized portion marking token '({m.group(1)})'.",
                    excerpt=line.strip()[:80],
                ))

    derived_banner = _highest(portion_levels) if portion_levels else None
    result.derived_banner = derived_banner

    # --- RULE: banner present at top and bottom -------------------------
    if not banner_levels:
        result.findings.append(Finding(
            rule="BANNER-MISSING",
            severity=Severity.ERROR,
            line=0,
            message="No overall classification banner found. A banner marking "
                    "must appear at the top and bottom of the document.",
        ))
    else:
        # Top banner should be among the first non-blank lines.
        first_nonblank = next((i for i, l in enumerate(lines, start=1) if l.strip()), None)
        if first_banner_line is not None and first_nonblank is not None and first_banner_line != first_nonblank:
            result.findings.append(Finding(
                rule="BANNER-TOP",
                severity=Severity.WARNING,
                line=first_nonblank,
                message="First content line is not the classification banner; "
                        "the overall marking should be the topmost line.",
                excerpt=lines[first_nonblank - 1].strip()[:80],
            ))
        # Bottom banner should be among the last non-blank lines.
        last_nonblank = None
        for i in range(len(lines), 0, -1):
            if lines[i - 1].strip():
                last_nonblank = i
                break
        if last_banner_line is not None and last_nonblank is not None and last_banner_line != last_nonblank:
            result.findings.append(Finding(
                rule="BANNER-BOTTOM",
                severity=Severity.WARNING,
                line=last_nonblank,
                message="Last content line is not the classification banner; "
                        "the overall marking should also appear at the bottom.",
                excerpt=lines[last_nonblank - 1].strip()[:80],
            ))
        elif len(banner_levels) < 2:
            result.findings.append(Finding(
                rule="BANNER-BOTTOM",
                severity=Severity.ERROR,
                line=0,
                message="Banner marking appears only once; it must be present at "
                        "both the top and the bottom of the document.",
            ))

    # --- RULE: top and bottom banners must match ------------------------
    if len(set(banner_levels)) > 1:
        result.findings.append(Finding(
            rule="BANNER-MISMATCH",
            severity=Severity.ERROR,
            line=0,
            message="Top and bottom banner markings disagree: "
                    f"{sorted(set(banner_levels))}. They must be identical.",
        ))

    # --- RULE: portion markings required on every paragraph --------------
    unmarked = [
        (ln, txt) for (ln, txt) in body_paragraph_lines
        if not PORTION_MARK_RE.match(txt)
    ]
    for ln, txt in unmarked:
        result.findings.append(Finding(
            rule="PORTION-MISSING",
            severity=Severity.ERROR,
            line=ln,
            message="Paragraph is missing a portion marking, e.g. '(U)' or '(S)'.",
            excerpt=txt.strip()[:80],
        ))

    # --- RULE: banner must equal highest portion marking ----------------
    if declared_banner and derived_banner:
        if _level_rank(declared_banner) != _level_rank(derived_banner):
            sev = Severity.ERROR
            # Under-marking the banner relative to content is the serious case.
            result.findings.append(Finding(
                rule="BANNER-PORTION-MISMATCH",
                severity=sev,
                line=first_banner_line or 0,
                message=(
                    f"Overall banner '{declared_banner}' does not match the "
                    f"highest portion marking '{derived_banner}'. The banner "
                    "must reflect the most restrictive portion."
                ),
            ))

    # --- RULE: MIL-STD-963 front matter ---------------------------------
    has_id = any(_FRONT_MATTER_ID_RE.match(l) for l in lines)
    has_date = any(_FRONT_MATTER_DATE_RE.match(l) for l in lines)
    if not has_id:
        result.findings.append(Finding(
            rule="FRONTMATTER-ID",
            severity=Severity.WARNING,
            line=0,
            message="Missing document identifier front matter (e.g. 'Document ID: ...').",
        ))
    if not has_date:
        result.findings.append(Finding(
            rule="FRONTMATTER-DATE",
            severity=Severity.WARNING,
            line=0,
            message="Missing document date front matter (e.g. 'Date: ...').",
        ))

    # --- RULE: formatting hygiene ---------------------------------------
    for idx, line in enumerate(lines, start=1):
        if "\t" in line:
            result.findings.append(Finding(
                rule="FORMAT-TAB",
                severity=Severity.WARNING,
                line=idx,
                message="Tab character found; use spaces for MIL-STD layout.",
            ))
        if line != line.rstrip():
            result.findings.append(Finding(
                rule="FORMAT-TRAILING-WS",
                severity=Severity.WARNING,
                line=idx,
                message="Trailing whitespace.",
            ))
        if len(line) > MAX_LINE_LEN:
            result.findings.append(Finding(
                rule="FORMAT-LINE-LENGTH",
                severity=Severity.WARNING,
                line=idx,
                message=f"Line exceeds {MAX_LINE_LEN} characters ({len(line)}).",
            ))

    if strict:
        for f in result.findings:
            if f.severity == Severity.WARNING:
                f.severity = Severity.ERROR

    # Stable ordering: document-level first, then by line, then by rule.
    result.findings.sort(key=lambda f: (f.line, f.rule))
    return result


def lint_file(path: str, strict: bool = False) -> LintResult:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return lint_text(text, path=path, strict=strict)


# --- SARIF 2.1.0 export ---------------------------------------------------
# SARIF (OASIS Static Analysis Results Interchange Format) lets milstdlint
# findings flow into GitHub code scanning, Azure DevOps, and any SARIF viewer.

_SARIF_LEVEL = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
}

# Short, human-readable descriptions for each rule milstdlint can emit. Used to
# populate the SARIF `rules` (driver.rules) catalog so viewers can show help.
RULE_DESCRIPTIONS = {
    "BANNER-MISSING": "No overall classification banner found at top and bottom.",
    "BANNER-TOP": "First content line is not the classification banner.",
    "BANNER-BOTTOM": "Classification banner is missing from the bottom of the document.",
    "BANNER-MISMATCH": "Top and bottom banner markings disagree.",
    "BANNER-PORTION-MISMATCH": "Overall banner does not match the highest portion marking.",
    "PORTION-MISSING": "Paragraph is missing a required portion marking.",
    "PORTION-UNKNOWN": "Unrecognized portion-marking token.",
    "FRONTMATTER-ID": "Missing document identifier front matter.",
    "FRONTMATTER-DATE": "Missing document date front matter.",
    "FORMAT-TAB": "Tab character found; MIL-STD layout uses spaces.",
    "FORMAT-TRAILING-WS": "Trailing whitespace.",
    "FORMAT-LINE-LENGTH": f"Line exceeds {MAX_LINE_LEN} characters.",
}


def to_sarif(results: List[LintResult], tool_name: str = "milstdlint",
             tool_version: str = "0.0.0") -> dict:
    """Render lint results as a SARIF 2.1.0 log (returns a JSON-able dict).

    One SARIF run is produced. Each Finding becomes a SARIF `result`; rules are
    collected into the driver `rules` catalog with stable ``MIL-<RULE>`` ids.
    """
    # Collect the set of rules actually triggered, preserving a stable order.
    seen_rules: List[str] = []
    for res in results:
        for f in res.findings:
            if f.rule not in seen_rules:
                seen_rules.append(f.rule)

    rule_index = {rule: i for i, rule in enumerate(seen_rules)}
    rules = [
        {
            "id": rule,
            "name": rule.replace("-", ""),
            "shortDescription": {
                "text": RULE_DESCRIPTIONS.get(rule, rule),
            },
            "defaultConfiguration": {"level": "warning"},
        }
        for rule in seen_rules
    ]

    sarif_results = []
    for res in results:
        for f in res.findings:
            location = {
                "physicalLocation": {
                    "artifactLocation": {"uri": res.path},
                }
            }
            if f.line and f.line > 0:
                location["physicalLocation"]["region"] = {"startLine": f.line}
            entry = {
                "ruleId": f.rule,
                "ruleIndex": rule_index[f.rule],
                "level": _SARIF_LEVEL.get(f.severity, "warning"),
                "message": {"text": f.message},
                "locations": [location],
            }
            if f.excerpt:
                entry["message"]["text"] = f"{f.message} (excerpt: {f.excerpt})"
            sarif_results.append(entry)

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": tool_name,
                        "version": tool_version,
                        "informationUri": "https://github.com/cognis-digital/milstdlint",
                        "rules": rules,
                    }
                },
                "results": sarif_results,
            }
        ],
    }
