"""Hardening tests: edge cases, bad input, and error-path coverage."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

from milstdlint.core import lint_text, lint_file, MAX_FILE_BYTES
from milstdlint.cli import main


class TestEmptyAndWhitespace(unittest.TestCase):
    """lint_text must handle empty / whitespace-only documents gracefully."""

    def test_empty_string_returns_error(self):
        res = lint_text("", path="empty")
        self.assertFalse(res.ok)
        rules = {f.rule for f in res.findings}
        self.assertIn("BANNER-MISSING", rules)

    def test_whitespace_only_returns_error(self):
        res = lint_text("   \n\n\t\n  ", path="blank")
        self.assertFalse(res.ok)
        rules = {f.rule for f in res.findings}
        self.assertIn("BANNER-MISSING", rules)

    def test_single_newline_returns_error(self):
        res = lint_text("\n", path="newline")
        self.assertFalse(res.ok)


class TestTypeValidation(unittest.TestCase):
    """lint_text must reject non-string input with a clear TypeError."""

    def test_none_raises_type_error(self):
        with self.assertRaises(TypeError):
            lint_text(None, path="none")  # type: ignore[arg-type]

    def test_bytes_raises_type_error(self):
        with self.assertRaises(TypeError):
            lint_text(b"SECRET\n(S) body.\nSECRET", path="bytes")  # type: ignore[arg-type]


class TestOversizedFile(unittest.TestCase):
    """Files exceeding MAX_FILE_BYTES must raise ValueError, not hang."""

    def test_lint_text_large_raises(self):
        big = "S" * (MAX_FILE_BYTES + 1)
        with self.assertRaises(ValueError) as ctx:
            lint_text(big, path="huge")
        self.assertIn("too large", str(ctx.exception))

    def test_lint_file_large_raises(self):
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".txt", delete=False
        ) as fh:
            # Write just over the limit; repeat a valid ASCII pattern.
            chunk = b"SECRET\n" * 1024
            written = 0
            while written <= MAX_FILE_BYTES:
                fh.write(chunk)
                written += len(chunk)
            path = fh.name
        try:
            with self.assertRaises(ValueError) as ctx:
                lint_file(path)
            self.assertIn("too large", str(ctx.exception))
        finally:
            os.unlink(path)


class TestMissingFile(unittest.TestCase):
    """CLI must return exit code 2 and print a message for missing files."""

    def test_missing_file_exits_2(self):
        code = main(["lint", "/nonexistent/path/to/file_xyz_12345.txt"])
        self.assertEqual(code, 2)

    def test_missing_file_in_subprocess(self):
        import subprocess
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        proc = subprocess.run(
            [sys.executable, "-m", "milstdlint", "lint", "/no/such/file.txt"],
            cwd=root, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 2)
        # Message should appear on stderr, not stdout.
        self.assertNotEqual(proc.stderr.strip(), "")
        self.assertEqual(proc.stdout.strip(), "")


class TestCliEdgeCases(unittest.TestCase):
    """CLI edge cases that require programmatic invocation."""

    def test_no_files_arg_returns_2(self):
        # When "lint" subcommand is given without any file arguments, argparse
        # raises SystemExit(2) because files is nargs="+".
        import io
        from contextlib import redirect_stderr
        buf = io.StringIO()
        with redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                main(["lint"])
        self.assertEqual(ctx.exception.code, 2)

    def test_json_output_is_valid_for_bad_doc(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.txt")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("no banner at all\n(U) some paragraph\n")
            code = main(["lint", bad, "--format", "json"])
            # Should be exit 1 (findings present), not 2.
            self.assertEqual(code, 1)


class TestMcpServerImports(unittest.TestCase):
    """mcp_server module must import cleanly (no ImportError on core symbols)."""

    def test_mcp_server_importable(self):
        # Just importing must not raise AttributeError / ImportError.
        import importlib
        mod = importlib.import_module("milstdlint.mcp_server")
        self.assertTrue(callable(getattr(mod, "serve", None)))


if __name__ == "__main__":
    unittest.main()
