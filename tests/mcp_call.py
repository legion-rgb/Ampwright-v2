# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2"]
# ///
"""Call AWRMWO-mcp tools over stdio, the way Claude Code does.

  uv run --script AWRMWO-mcp/tests/mcp_call.py <tool> '<json args>'
  uv run --script AWRMWO-mcp/tests/mcp_call.py --batch steps.json   # [{"tool": ..., "args": {...}}, ...] in one session
Images are saved to %TEMP%/AWRMWO-mcp/<tool>_<n>.png and their path is printed.
"""
import asyncio
import base64
import json
import os
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parents[1] / "server.py"
TOTAL_S = int(os.environ.get("AWR_CALL_TIMEOUT", 900))  # whole run; the server also caps each call at 15 min
OUT = Path(tempfile.gettempdir()) / "AWRMWO-mcp"


def show(tool, n, result):
    print(f"--- {tool}{'  [ERROR]' if result.isError else ''}")
    for c in result.content:
        if c.type == "image":
            OUT.mkdir(exist_ok=True)
            path = OUT / f"{tool}_{n}.png"
            path.write_bytes(base64.b64decode(c.data))
            print(f"image saved: {path}")
        else:
            print(c.text)


async def main(steps):
    """Runs every step even after an error (so expected refusals can be tested); returns the error count."""
    params = StdioServerParameters(command="uv", args=["run", "--script", str(SERVER)])
    errors = 0
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        for n, step in enumerate(steps):
            res = await s.call_tool(step["tool"], step.get("args", {}))
            show(step["tool"], n, res)
            errors += bool(res.isError)
    return errors


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "--batch":
        steps = json.loads(Path(a[1]).read_text())
    else:
        steps = [{"tool": a[0], "args": json.loads(a[1]) if len(a) > 1 else {}}]
    try:
        # leaving stdio_client's context on cancel also terminates the server child
        sys.exit(1 if asyncio.run(asyncio.wait_for(main(steps), TOTAL_S)) else 0)
    except (asyncio.TimeoutError, TimeoutError):
        sys.exit(f"TIMEOUT after {TOTAL_S}s (set AWR_CALL_TIMEOUT to change); server child stopped")
