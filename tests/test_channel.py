"""Channel test, no AWR and no Claude. Run: uv run --with "mcp>=1.2,<2" --with pywin32 python tests/test_channel.py"""
import asyncio
import json
import logging
import os
import queue
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import anyio
import win32file
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage, JSONRPCNotification, JSONRPCRequest, ToolAnnotations

import hub

mcp = hub.HubMCP("test")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def rd(x: int) -> dict:
    return {"x": x}


bad = []  # session validation failures would be logged here


class _H(logging.Handler):
    def emit(self, r):
        if "validate" in r.getMessage().lower():
            bad.append(r.getMessage())


logging.getLogger().addHandler(_H())

from_server = queue.Queue()  # JSON-RPC dicts the server wrote
state = {}
ready = threading.Event()


async def amain():
    c2s_w, c2s_r = anyio.create_memory_object_stream(10)
    s2c_w, s2c_r = anyio.create_memory_object_stream(10)
    state["loop"], state["c2s_w"] = asyncio.get_running_loop(), c2s_w
    asyncio.ensure_future(mcp.run_streams(c2s_r, s2c_w))

    async def collect():
        async for item in s2c_r:
            from_server.put(json.loads(item.message.model_dump_json(by_alias=True, exclude_none=True)))

    asyncio.ensure_future(collect())
    ready.set()
    await asyncio.sleep(3600)


threading.Thread(target=lambda: asyncio.run(amain()), daemon=True).start()
ready.wait(5)


def send(msg):
    asyncio.run_coroutine_threadsafe(state["c2s_w"].send(SessionMessage(message=JSONRPCMessage(msg))),
                                     state["loop"]).result(5)


def wait_for(pred, q=from_server):
    while True:
        m = q.get(timeout=5)
        if pred(m):
            return m


send(JSONRPCRequest(jsonrpc="2.0", id=1, method="initialize", params={
    "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}))
init = wait_for(lambda m: m.get("id") == 1)
exp = init["result"]["capabilities"]["experimental"]
assert "claude/channel" in exp and "claude/channel/permission" in exp, exp
send(JSONRPCNotification(jsonrpc="2.0", method="notifications/initialized"))

name = hub.start(mcp)
h = win32file.CreateFile(name, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None,
                         win32file.OPEN_EXISTING, 0, None)
pipe = queue.Queue()


def reader():
    buf = b""
    try:
        while True:
            buf += hub.read_some(h)
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                pipe.put(json.loads(line))
    except Exception:
        pass


threading.Thread(target=reader, daemon=True).start()


def call(i, tool, **args):
    win32file.WriteFile(h, (json.dumps({"id": i, "call": tool, "args": args}) + "\n").encode())
    return wait_for(lambda m: m.get("id") == i, pipe)


assert pipe.get(timeout=5)["event"] == "hello"

assert call(1, "chat", text="hi there")["result"] == {"sent": True}
m = wait_for(lambda m: m.get("method") == "notifications/claude/channel")
assert m["params"] == {"content": "hi there", "meta": {"sender": "fieldnote"}}, m
assert "text" in call(2, "chat")["error"]

send(JSONRPCNotification(jsonrpc="2.0", method="notifications/claude/channel/permission_request", params={
    "request_id": "abcde", "tool_name": "save_project", "description": "save", "input_preview": "{}"}))
e = wait_for(lambda m: m.get("event") == "permission_request", pipe)
assert e["request_id"] == "abcde" and e["tool_name"] == "save_project", e

assert "behavior" in call(3, "permission", request_id="abcde", behavior="maybe")["error"]
assert call(4, "permission", request_id="abcde", behavior="allow")["result"] == {"sent": True}
m = wait_for(lambda m: m.get("method") == "notifications/claude/channel/permission")
assert m["params"] == {"request_id": "abcde", "behavior": "allow"}, m

send(JSONRPCRequest(jsonrpc="2.0", id=2, method="tools/call", params={"name": "reply", "arguments": {"text": "done"}}))
e = wait_for(lambda m: m.get("event") == "reply", pipe)
assert e["text"] == "done", e
r = wait_for(lambda m: m.get("id") == 2)
assert "delivered_to" in json.dumps(r), r

assert not bad, bad
print("OK", flush=True)
os._exit(0)  # daemon pipe threads sit in blocking Win32 calls
