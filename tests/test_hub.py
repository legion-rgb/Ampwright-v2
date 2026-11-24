"""Hub test, no AWR needed. Run: uv run --with "mcp>=1.2,<2" --with pywin32 python tests/test_hub.py"""
import asyncio
import json
import os
import queue
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import win32file
from mcp.types import ToolAnnotations

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
h = win32file.CreateFile(name, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None,
                         win32file.OPEN_EXISTING, 0, None)
msgs = queue.Queue()


def reader():
    buf = b""
    try:
        while True:
            buf += hub.read_some(h)
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                msgs.put(json.loads(line))
    except Exception:
        pass


threading.Thread(target=reader, daemon=True).start()


def call(i, tool, **args):
    win32file.WriteFile(h, (json.dumps({"id": i, "call": tool, "args": args}) + "\n").encode())
    while True:
        m = msgs.get(timeout=5)
        if m.get("id") == i:
            return m


assert msgs.get(timeout=5)["event"] == "hello"
r = call(1, "rd", x=7)
assert r["result"] == {"x": 7}, r
r = call(2, "wr", x=1)
assert "not allowed from the GUI" in r["error"], r
asyncio.run(mcp.call_tool("wr", {"x": 2}))  # simulates Claude
while True:
    m = msgs.get(timeout=5)
    if m.get("event") == "activity" and m["tool"] == "wr":
        break
assert m["source"] == "claude" and m["ok"], m
r = call(3, "activity", since=0)
tools = [(e["tool"], e["source"]) for e in r["result"]]
assert tools == [("rd", "gui"), ("wr", "claude")], tools

# a second client that never reads must not stall Claude's calls (pipe buffer is 64 KB)
import time
stuck = win32file.CreateFile(name, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None,
                             win32file.OPEN_EXISTING, 0, None)
time.sleep(0.2)
t0 = time.perf_counter()


async def burst():
    for i in range(2500):
        await mcp.call_tool("wr", {"x": i})


asyncio.run(burst())
assert time.perf_counter() - t0 < 10, "a stalled GUI client blocked tool calls"
assert len(mcp._clients) <= 2, "stalled client was not dropped"

# a client can disconnect and a new one connect (needs FILE_CREATE_PIPE_INSTANCE on later instances)
win32file.CloseHandle(stuck)
h2 = win32file.CreateFile(name, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None,
                          win32file.OPEN_EXISTING, 0, None)
assert json.loads(hub.read_some(h2).split(b"\n")[0])["event"] == "hello"
print("OK", flush=True)
os._exit(0)  # daemon pipe threads sit in blocking Win32 calls
