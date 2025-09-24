"""MILSTDLINT MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from milstdlint.core import scan, to_json

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
        """Lint documents against MIL-STD / DoD formatting and classification-marking rules.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
