# /// script
# dependencies = ["mcp>=1.2,<2", "pywin32", "pywebview"]
# ///
"""Approval dialog. (a) a real hub and the real pipe client: approve() waits for the app's answer.
(b) the dialog in a hidden window: texts, Deny focused, Allow, Deny, Escape. No AWR, no Claude."""
import asyncio
import json
import os
import sys
import tempfile
import threading
import time

os.environ["APPDATA"] = tempfile.mkdtemp()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "fieldnote"))
sys.path.insert(0, os.path.join(HERE, ".."))
import app
import hub
import pipe
import webview


def until(cond, what, s=10):
    end = time.time() + s
    while time.time() < end:
        v = cond()
        if v:
            return v
        time.sleep(0.05)
    raise AssertionError("timed out: " + what)


# ---- (a) real hub, real pipe ----
hub.APPROVE_TIMEOUT = 2
app.APPROVE_WAIT = 2
mcp = hub.HubMCP("test")


@mcp.tool()
async def add_element(model: str) -> dict:
    return {}


api = app.Api()
api._client = pipe.PipeClient(hub.start(mcp), api._on_pipe)
ask = lambda tool, inp: asyncio.run_coroutine_threadsafe(mcp.approve(tool, inp), mcp.loop)
waiting = lambda: [i for i in api.history() if i["kind"] == "approval" and i["status"] == "waiting"]

r = json.loads(ask("mcp__AWRMWO-mcp__add_element", {"model": "RES"}).result(5))  # building never asks
assert r["behavior"] == "allow" and not waiting() and not api.history(), r
assert json.loads(ask("Read", {"file_path": "x"}).result(5))["behavior"] == "allow"
# Design mode: dossier writes inside the v2 folder never ask; .emp files, other folders and shell commands do
for inp in ({"file_path": "designs/rc_lpf/spec.md"}, {"file_path": os.path.join(os.path.dirname(hub.__file__), "PROGRESS.md")}):
    assert json.loads(ask("Write", inp).result(5))["behavior"] == "allow", inp
assert json.loads(ask("Agent", {"subagent_type": "circuit-theory"}).result(5))["behavior"] == "allow"
assert not waiting() and not api.history()
assert not hub._writes_inside("Write", {"file_path": "../CLAUDE.md"}) and not hub._writes_inside("Edit", {"file_path": "x.EMP"})
assert not hub._writes_inside("Write", {"file_path": r"D:\elsewhere\a.txt"}) and not hub._writes_inside("Write", {"file_path": 3})
assert not hub._writes_inside("Write", {}) and not hub._writes_inside("Bash", {"file_path": "a.txt"})
for p in ("hub.py", ".claude/settings.json", "checks/hook_guard.py", "CLAUDE.md", ".claude/agents/awr-builder.md",
          "designs", "designs/../hub.py", "designs/x/model.emp"):  # the safety checks themselves always ask
    assert not hub._writes_inside("Edit", {"file_path": p}), p
assert hub._writes_inside("Edit", {"file_path": "errors.md"}) and hub._writes_inside("Write", {"file_path": "designs/a/state.json"})
# the sweep and equations on one schematic never ask; project-wide ones (no document) do
for tool, inp in (("set_frequencies", {"start_hz": 1e9, "stop_hz": 2e9, "points": 11, "document": "FN_RC"}),
                  ("add_equation", {"expression": "C1=1e-12", "document": "FN_RC"})):
    assert json.loads(ask("mcp__AWRMWO-mcp__" + tool, inp).result(5))["behavior"] == "allow", tool
assert not waiting()
for tool, inp in (("Write", {"file_path": r"C:\Users\me\MyDesign.emp"}), ("Bash", {"command": "del x"}),
                  ("mcp__AWRMWO-mcp__set_frequencies", {"around_hz": 1e9}),
                  ("mcp__AWRMWO-mcp__add_equation", {"expression": "C1=1e-12", "document": ""})):
    f = ask(tool, inp)
    it = until(waiting, tool + " request shown")[0]
    assert it["tool"] == tool.removeprefix("mcp__AWRMWO-mcp__"), it
    api.answer(it["id"], "deny")
    assert json.loads(f.result(5))["behavior"] == "deny", tool
api.clear_history()

f = ask("mcp__AWRMWO-mcp__save_project", {"name": "x"})
it = until(waiting, "save request shown")[0]
assert it["tool"] == "save_project" and "x" in it["preview"], it
assert api.answer(it["id"], "maybe")["ok"] is False
assert api.answer(it["id"], "allow")["ok"] is True
assert json.loads(f.result(5))["behavior"] == "allow"
assert api.answer(it["id"], "allow")["ok"] is False  # already answered

f = ask("mcp__AWRMWO-mcp__delete_graph", {"name": "g"})
it = until(waiting, "delete request shown")[0]
assert api.answer(it["id"], "deny")["ok"] is True
r = json.loads(f.result(5))
assert r["behavior"] == "deny" and "denied" in r["message"], r

f = ask("mcp__AWRMWO-mcp__new_project", {})  # nobody answers: the server denies, the dialog closes
until(waiting, "new_project shown")
r = json.loads(f.result(5))
assert r["behavior"] == "deny"
until(lambda: not waiting(), "dialog closes on timeout")
assert [i["status"] for i in api.history() if i["kind"] == "approval"] == ["allowed", "denied", "expired"]
api._close_client()


# ---- (a2) a window call that never returns must not block the pipe reader (froze the live window, 25 Nov 2026) ----
class StuckWindow:
    title = "stuck"
    on_top = property(lambda s: False, lambda s, v: threading.Event().wait())  # setting it never returns

    def restore(self):
        threading.Event().wait()  # never returns

    def evaluate_js(self, _):
        pass


api._window = StuckWindow()
t0 = time.time()
api._ask({"request_id": "s1", "tool_name": "delete_graph", "input_preview": ""})
assert time.time() - t0 < 1 and api.history()[-1]["status"] == "waiting", "approval blocked on a stuck window"
api._window = None
api._resolve("s1", "expired")

# ---- (b) the dialog ----
app.APPROVE_WAIT = 120
api = app.Api()
api.clear_history()  # (a) saved its history
sent = []


class Fake:
    def request(self, call, args, timeout=0):
        sent.append((call, args))
        return {"sent": True}


api._client = Fake()
w = webview.create_window("test_approval", html=app.build_page(), js_api=api, hidden=True)
api._window = w
q, out = w.evaluate_js, {}
SHOWN = "[!$('approval').hidden, $('apTitle').textContent, document.activeElement.id, $('apPreview').textContent].join('|')"


def run():
    time.sleep(3)
    try:
        api._set(claude="up", awr="up")
        out["hidden"] = q("$('approval').hidden")
        api._on_pipe({"event": "permission_request", "request_id": "r1", "tool_name": "save_project", "input_preview": '{"x":1}'})
        until(lambda: q("!$('approval').hidden"), "dialog shows")
        out["save"] = q(SHOWN)
        q("$('apAllow').click(); 1")
        until(lambda: q("$('approval').hidden"), "closes after Allow")
        out["row1"] = q("document.querySelector('.note').textContent")

        api._on_pipe({"event": "permission_request", "request_id": "r2", "tool_name": "delete_graph", "input_preview": ""})
        until(lambda: q("!$('approval').hidden"), "second dialog")
        out["del"] = q(SHOWN)
        q("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'})); 1")
        until(lambda: q("$('approval').hidden"), "closes after Escape")

        api._on_pipe({"event": "permission_request", "request_id": "r3", "tool_name": "new_project", "input_preview": ""})
        until(lambda: q("!$('approval').hidden"), "third dialog")
        api._on_pipe({"event": "disconnected"})  # server gone: nothing left to answer
        until(lambda: q("$('approval').hidden"), "closes when the server is lost")
        out["rows"] = q("[...document.querySelectorAll('#feed .note')].map(n => n.textContent).join(' ; ')")
        out["err"] = q("$('bannerText').textContent.includes('window hit an error')")
    except Exception as e:
        out["error"] = repr(e)
    w.destroy()


webview.start(run)
assert "error" not in out, out
assert out["hidden"] is True, out
assert out["save"] == "true|Save the project?|apDeny|{\"x\":1}", out
assert out["row1"] == "Save the project: you allowed it", out
assert out["del"].startswith("true|Delete graph?|apDeny|"), out
assert sent == [("permission", {"request_id": "r1", "behavior": "allow"}), ("permission", {"request_id": "r2", "behavior": "deny"})], sent
assert out["rows"] == ("Save the project: you allowed it ; Delete graph: you denied it ; Start a new project: no answer, so it was denied"), out
assert out["err"] is False, out
print("OK: real hub round trip (building never asks; save/delete allow, deny, timeout), dialog texts, Deny focused, Escape denies, closes when the server is lost")
