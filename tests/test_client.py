"""Client test, no AWR needed. Run: uv run --with "mcp>=1.2,<2" --with pywin32 python tests/test_client.py"""
import asyncio
import os
import queue
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mcp.types import ToolAnnotations

import ampwright_client as fc
import hub

mcp = hub.HubMCP("test")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def rd(x: int) -> dict:
    return {"x": x}


@mcp.tool()
async def wr(x: int) -> dict:
    return {"wrote": x}


name = hub.start(mcp)
assert name, "hub did not start"
sess = [s for s in fc.list_sessions() if s["pid"] == os.getpid()]
assert sess and sess[0]["pipe"] == name, sess
ev = queue.Queue()
c = fc.PipeClient(name, ev.put)
assert ev.get(timeout=5)["event"] == "hello"
assert c.request("rd", {"x": 7}, timeout=5) == {"x": 7}
try:
    c.request("wr", {"x": 1}, timeout=5)
    raise AssertionError("write tool was not refused")
except RuntimeError as e:
    assert "not allowed" in str(e), e
asyncio.run(mcp.call_tool("wr", {"x": 2}))
while True:
    m = ev.get(timeout=5)
    if m.get("event") == "activity" and m["tool"] == "wr":
        break
c.close()
print("OK", flush=True)
os._exit(0)  # daemon pipe threads sit in blocking Win32 calls
