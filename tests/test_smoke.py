"""Smoke tests for MILSTDLINT. Standard library only, no network."""
import json
import os
import subprocess
import sys
import unittest

from milstdlint import (
    TOOL_NAME,
    TOOL_VERSION,
    lint_text,
    Severity,
    CLASSIFICATION_LEVELS,
)
from milstdlint.cli import main, _render_json


GOOD_DOC = "\n".join([
    "SECRET",
    "Document ID: WP-2026-0608-A",
    "Date: 2026-06-08",
    "",
    "(U) This is an unclassified introductory paragraph.",
    "(S) This paragraph is SECRET, matching the overall banner.",
    "",
    "SECRET",
])

UNDER_MARKED_DOC = "\n".join([
    "CONFIDENTIAL",
    "Document ID: X-1",
    "Date: 2026-06-08",
    "",
    "(C) A confidential paragraph.",
    "(S) A secret paragraph that should force a SECRET banner.",
    "",
    "CONFIDENTIAL",
])


class TestMetadata(unittest.TestCase):
    def test_version_constants(self):
        self.assertEqual(TOOL_NAME, "milstdlint")
        self.assertTrue(TOOL_VERSION.count(".") >= 2)

    def test_levels_ordered(self):
        self.assertEqual(CLASSIFICATION_LEVELS[0], "U")
        self.assertEqual(CLASSIFICATION_LEVELS[-1], "TS")


class TestEngine(unittest.TestCase):
    def test_good_doc_passes(self):
        res = lint_text(GOOD_DOC, path="good")
        self.assertTrue(res.ok, msg=[f.to_dict() for f in res.findings])
        self.assertEqual(res.error_count, 0)
        self.assertEqual(res.declared_banner, "S")
        self.assertEqual(res.derived_banner, "S")

    def test_missing_banner_is_error(self):
        res = lint_text("(U) just one paragraph, no banner.", path="nob")
        rules = {f.rule for f in res.findings}
        self.assertIn("BANNER-MISSING", rules)
        self.assertFalse(res.ok)

    def test_under_marked_banner_detected(self):
        res = lint_text(UNDER_MARKED_DOC, path="under")
        rules = {f.rule for f in res.findings}
        self.assertIn("BANNER-PORTION-MISMATCH", rules)
        self.assertEqual(res.derived_banner, "S")
        self.assertEqual(res.declared_banner, "C")
        self.assertFalse(res.ok)

    def test_missing_portion_marking(self):
        doc = "SECRET\n\n(S) marked.\nunmarked paragraph here.\n\nSECRET"
        res = lint_text(doc, path="pm")
        self.assertIn("PORTION-MISSING", {f.rule for f in res.findings})

    def test_banner_mismatch_top_bottom(self):
        doc = "SECRET\n\n(S) body.\n\nCONFIDENTIAL"
        res = lint_text(doc, path="mm")
        self.assertIn("BANNER-MISMATCH", {f.rule for f in res.findings})

    def test_strict_promotes_warnings(self):
        doc = "SECRET\nDocument ID: A\nDate: 2026-01-01\n\n(S) body has trailing ws   \n\nSECRET"
        lax = lint_text(doc, path="lax")
        strict = lint_text(doc, path="strict", strict=True)
        self.assertTrue(lax.ok)
        self.assertFalse(strict.ok)


class TestJsonAndCli(unittest.TestCase):
    def test_json_renderer_is_valid_json(self):
        res = lint_text(GOOD_DOC, path="good")
        payload = json.loads(_render_json([res]))
        self.assertEqual(payload["tool"], TOOL_NAME)
        self.assertEqual(payload["summary"]["files"], 1)

    def test_main_exit_codes(self, ):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            good = os.path.join(d, "good.txt")
            bad = os.path.join(d, "bad.txt")
            with open(good, "w", encoding="utf-8") as fh:
                fh.write(GOOD_DOC)
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write(UNDER_MARKED_DOC)
            self.assertEqual(main(["lint", good]), 0)
            self.assertEqual(main(["lint", bad]), 1)
            self.assertEqual(main(["lint", good, "--format", "json"]), 0)

    def test_no_command_returns_usage(self):
        self.assertEqual(main([]), 2)

    def test_module_runs_as_subprocess(self):
        # Verify python -m milstdlint --version works end to end.
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        proc = subprocess.run(
            [sys.executable, "-m", "milstdlint", "--version"],
            cwd=root, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn(TOOL_VERSION, proc.stdout)


if __name__ == "__main__":
    unittest.main()
