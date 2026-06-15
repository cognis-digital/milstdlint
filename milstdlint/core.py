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
    ranked = [(_level_rank(lvl), lvl) for lvl in levels if _level_rank(lvl) >= 0]
    if not ranked:
        return None
    return max(ranked, key=lambda t: t[0])[1]


MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MiB — refuse to lint absurdly large files


def lint_text(text: str, path: str = "<text>", strict: bool = False) -> LintResult:
    """Lint a document given as text. Returns a LintResult.

    If ``strict`` is True, formatting WARNINGs are promoted to ERRORs so that
    they affect the exit status.

    Raises ``TypeError`` if *text* is not a ``str``.
    """
    if not isinstance(text, str):
        raise TypeError(f"lint_text: expected str, got {type(text).__name__!r}")
    if len(text) > MAX_FILE_BYTES:
        raise ValueError(
            f"{path}: file too large ({len(text):,} bytes); "
            f"limit is {MAX_FILE_BYTES:,} bytes"
        )
    if not text.strip():
        # Empty or whitespace-only document: no banner, nothing to check.
        result = LintResult(path=path)
        result.findings.append(Finding(
            rule="BANNER-MISSING",
            severity=Severity.ERROR,
            line=0,
            message="Document is empty; no content to evaluate.",
        ))
        return result
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
        first_nonblank = next(
            (i for i, ln in enumerate(lines, start=1) if ln.strip()), None
        )
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
    has_id = any(_FRONT_MATTER_ID_RE.match(ln) for ln in lines)
    has_date = any(_FRONT_MATTER_DATE_RE.match(ln) for ln in lines)
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
    """Read *path* from disk and lint it.

    Re-raises ``OSError`` (including ``FileNotFoundError`` /
    ``PermissionError``) so the caller can surface a clean error message.
    Raises ``ValueError`` if the file exceeds *MAX_FILE_BYTES*.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        # Read in bounded chunks to catch oversized files without loading
        # the entire thing into memory first.
        chunks: list[str] = []
        total = 0
        for chunk in iter(lambda: fh.read(65536), ""):
            total += len(chunk.encode("utf-8", errors="replace"))
            if total > MAX_FILE_BYTES:
                raise ValueError(
                    f"{path}: file too large (>{MAX_FILE_BYTES:,} bytes); "
                    "lint aborted"
                )
            chunks.append(chunk)
        text = "".join(chunks)
    return lint_text(text, path=path, strict=strict)
