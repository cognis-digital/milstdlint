"""MILSTDLINT MCP server — exposes lint_file() as an MCP tool for Cognis.Studio."""
from __future__ import annotations

import json

from milstdlint.core import lint_file


def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-milstdlint[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-milstdlint[mcp]'")
        return 1
    app = FastMCP("milstdlint")

    @app.tool()
    def milstdlint_scan(target: str) -> str:
        """Lint a document against MIL-STD / DoD formatting and
        classification-marking rules. Returns JSON findings."""
        if not target or not target.strip():
            return json.dumps({"error": "target path must not be empty"})
        try:
            result = lint_file(target)
        except (OSError, ValueError) as exc:
            return json.dumps({"error": str(exc)})
        return json.dumps(result.to_dict())

    app.run()
    return 0
