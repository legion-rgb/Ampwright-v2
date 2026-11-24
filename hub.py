"""Activity hub: records every MCP tool call and serves a per-user named pipe to the GUI.

STDOUT is the MCP stream: log to stderr only.
Protocol: UTF-8 JSON lines (see UI_PLAN.md, Phase 1).
"""
import asyncio
import collections
import contextvars
import datetime
import itertools
import json
import os
import queue
import sys
import threading
import time

import pywintypes
import win32api
import win32con
import win32file
import win32pipe
import win32security
from mcp.server.fastmcp import FastMCP

_source = contextvars.ContextVar("source", default="claude")
_TRUNC = 300


def _log(*a):
    print("[hub]", *a, file=sys.stderr, flush=True)


def _cut(s):
    s = str(s)
    return s if len(s) <= _TRUNC else s[:_TRUNC] + "..."


def to_jsonable(res):
    """Turn a FastMCP call_tool result (content blocks, dict, or (content, structured)) into JSON data."""
    if isinstance(res, tuple) and len(res) == 2:
        res = res[1] if isinstance(res[1], dict) else res[0]
    if isinstance(res, dict):
        # FastMCP wraps non-dict returns as {"result": ...}
        return res["result"] if list(res) == ["result"] else res
    out = []
    for b in res:
        if getattr(b, "type", None) == "image":
            out.append({"image_base64": b.data, "mime": b.mimeType})
            continue
        t = getattr(b, "text", None)
        try:
            out.append(json.loads(t))
        except (TypeError, ValueError):
            out.append(t)
    return out[0] if len(out) == 1 else out


def read_some(h):
    """Poll-then-read: a blocking ReadFile on a synchronous handle would block every WriteFile on it."""
    while True:
        n = win32pipe.PeekNamedPipe(h, 0)[1]  # raises pywintypes.error when the peer is gone
        if n:
            return bytes(win32file.ReadFile(h, n)[1])
        time.sleep(0.02)


class _Client:
    """Writes go through a queue and one writer thread, so a GUI that stops reading never blocks a tool call."""

    def __init__(self, handle, on_dead):
        self.h = handle
        self.q = queue.Queue(maxsize=1000)
        self.on_dead = on_dead
        threading.Thread(target=self._writer, daemon=True).start()

    def send(self, obj):
        try:
            self.q.put_nowait((json.dumps(obj, default=str) + "\n").encode("utf-8"))
        except queue.Full:  # client is not reading: drop it rather than stall Claude
            self.on_dead(self)

    def _writer(self):
        while True:
            data = self.q.get()
            if data is None:
                return
            try:
                win32file.WriteFile(self.h, data)
            except pywintypes.error:
                self.on_dead(self)
                return


class HubMCP(FastMCP):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.ring = collections.deque(maxlen=500)
        self._seq = itertools.count(1)
        self._clients = set()
        self._clients_lock = threading.Lock()
        self.loop = None
        self._out = None
        self._mcp_loop = None
        self.add_tool(self.reply, name="reply", description=(
            "Send your answer to the user in the Fieldnote desktop app. Use it to answer every message "
            "that arrived as a <channel sender=\"fieldnote\"> tag; the user does not see the terminal."))

    def reply(self, text: str) -> dict:
        n = len(self._clients)
        self._broadcast({"event": "reply", "text": text})
        return {"delivered_to": n} if n else {"delivered_to": 0, "note": "no Fieldnote window is connected"}

    # ---- Claude Code channel (research preview) ----
    async def run_streams(self, read_stream, write_stream):
        import anyio
        from mcp.types import JSONRPCNotification
        self._out = write_stream
        self._mcp_loop = asyncio.get_running_loop()
        send, recv = anyio.create_memory_object_stream(0)

        async def pump():
            async with send:
                async for item in read_stream:
                    m = getattr(item, "message", None)
                    m = getattr(m, "root", m)
                    if isinstance(m, JSONRPCNotification) and m.method == "notifications/claude/channel/permission_request":
                        p = m.params or {}
                        self._broadcast({"event": "permission_request", **{
                            k: p.get(k) for k in ("request_id", "tool_name", "description", "input_preview")}})
                    else:
                        await send.send(item)

        async with anyio.create_task_group() as tg:
            tg.start_soon(pump)
            await self._mcp_server.run(recv, write_stream, self._mcp_server.create_initialization_options(
                experimental_capabilities={"claude/channel": {}, "claude/channel/permission": {}}))
            tg.cancel_scope.cancel()

    async def run_stdio_async(self):
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (r, w):
            await self.run_streams(r, w)

    def _notify(self, method, params):
        if self._out is None:
            raise RuntimeError("no Claude Code session attached")
        from mcp.shared.message import SessionMessage
        from mcp.types import JSONRPCMessage, JSONRPCNotification
        msg = SessionMessage(message=JSONRPCMessage(JSONRPCNotification(jsonrpc="2.0", method=method, params=params)))
        asyncio.run_coroutine_threadsafe(self._out.send(msg), self._mcp_loop).result(10)

    async def call_tool(self, name, arguments):
        t0 = time.perf_counter()
        ok, out = True, None
        try:
            res = await super().call_tool(name, arguments)
            out = res
            return res
        except BaseException as e:
            ok, out = False, repr(e)
            raise
        finally:
            if ok:
                try:
                    out = json.dumps(to_jsonable(out), default=str)
                except Exception:
                    out = str(out)
            self._record(name, arguments, ok, out, (time.perf_counter() - t0) * 1000)

    def _record(self, tool, args, ok, out, ms):
        try:
            a = json.dumps(args, default=str)
        except Exception:
            a = str(args)
        entry = {"seq": next(self._seq), "time": datetime.datetime.now().isoformat(timespec="milliseconds"),
                 "source": _source.get(), "tool": tool, "args": _cut(a), "ok": ok,
                 "result_or_error": _cut(out), "ms": round(ms, 1)}
        self.ring.append(entry)
        self._broadcast({"event": "activity", **entry})

    def _broadcast(self, msg):
        with self._clients_lock:
            clients = list(self._clients)
        for c in clients:
            c.send(msg)

    def _drop(self, c):
        with self._clients_lock:
            if c not in self._clients:
                return
            self._clients.discard(c)
        try:
            c.q.put_nowait(None)  # stop the writer
        except queue.Full:
            pass
        try:
            win32pipe.DisconnectNamedPipe(c.h)  # also unblocks the writer and the reader
            win32file.CloseHandle(c.h)
        except Exception:
            pass

    # ---- GUI side ----
    async def _gui_call(self, name, args):
        _source.set("gui")
        return to_jsonable(await self.call_tool(name, args))

    def _handle(self, req):
        call, args = req.get("call"), req.get("args") or {}
        if call == "activity":
            since = int(args.get("since", 0))
            return [e for e in list(self.ring) if e["seq"] > since]
        if call == "chat":
            text = args.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("text must be a non-empty string")
            self._notify("notifications/claude/channel", {"content": text, "meta": {"sender": "fieldnote"}})
            _source.set("gui")
            self._record("chat", args, True, "sent", 0)
            return {"sent": True}
        if call == "permission":
            rid, beh = args.get("request_id"), args.get("behavior")
            if not isinstance(rid, str) or not rid or beh not in ("allow", "deny"):
                raise ValueError("need request_id (str) and behavior 'allow' or 'deny'")
            self._notify("notifications/claude/channel/permission", {"request_id": rid, "behavior": beh})
            return {"sent": True}
        tool = self._tool_manager.get_tool(call)
        ann = getattr(tool, "annotations", None)
        if tool is None or not (ann and ann.readOnlyHint):
            raise PermissionError("not allowed from the GUI")
        return asyncio.run_coroutine_threadsafe(self._gui_call(call, args), self.loop).result()

    def _serve_client(self, c):
        buf = b""
        try:
            c.send({"event": "hello", "pid": os.getpid(), "server": "AWRMWO-mcp", "version": 1})
            while True:
                buf += read_some(c.h)
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    rid = None
                    try:
                        req = json.loads(line.decode("utf-8"))
                        rid = req.get("id")
                        c.send({"id": rid, "result": self._handle(req)})
                    except Exception as e:
                        c.send({"id": rid, "error": str(e) or repr(e)})
        except pywintypes.error:
            pass  # client went away
        except Exception as e:
            _log("client error:", repr(e))
        finally:
            self._drop(c)

    def _security(self):
        tok = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
        sid = win32security.GetTokenInformation(tok, win32security.TokenUser)[0]
        acl = win32security.ACL()
        # GENERIC_ALL (current user only): later CreateNamedPipe calls need FILE_CREATE_PIPE_INSTANCE too
        acl.AddAccessAllowedAce(win32security.ACL_REVISION, win32con.GENERIC_ALL, sid)
        sd = win32security.SECURITY_DESCRIPTOR()
        sd.SetSecurityDescriptorDacl(1, acl, 0)
        sa = pywintypes.SECURITY_ATTRIBUTES()
        sa.SECURITY_DESCRIPTOR = sd
        return sa

    def _accept_loop(self, name, created):
        sa = self._security()
        while True:
            try:
                h = win32pipe.CreateNamedPipe(
                    name, win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT
                    | win32pipe.PIPE_REJECT_REMOTE_CLIENTS,
                    win32pipe.PIPE_UNLIMITED_INSTANCES, 65536, 65536, 0, sa)
            except pywintypes.error as e:
                _log("pipe create failed, GUI cannot connect:", e)
                created.set()
                return
            created.set()
            try:
                win32pipe.ConnectNamedPipe(h, None)
            except pywintypes.error as e:
                if e.winerror != 535:  # ERROR_PIPE_CONNECTED: client got in before we called
                    win32file.CloseHandle(h)
                    continue
            c = _Client(h, self._drop)
            with self._clients_lock:
                self._clients.add(c)
            threading.Thread(target=self._serve_client, args=(c,), daemon=True).start()

    def start_hub(self):
        name = r"\\.\pipe\AWRMWO-%s-%d" % (os.environ.get("USERNAME", "user"), os.getpid())
        ready = threading.Event()

        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            ready.set()
            self.loop.run_forever()

        threading.Thread(target=run_loop, daemon=True).start()
        ready.wait()
        created = threading.Event()  # return only once the pipe exists, so an immediate connect finds it
        threading.Thread(target=self._accept_loop, args=(name, created), daemon=True).start()
        created.wait(5)
        return name


def start(mcp):
    """Start the hub; never raises (the MCP server must keep running). Returns the pipe name or None."""
    try:
        name = mcp.start_hub()
        _log("pipe", name)
        return name
    except Exception as e:
        _log("hub failed to start:", repr(e))
        return None
