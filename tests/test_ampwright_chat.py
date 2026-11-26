# /// script
# dependencies = ["pywin32", "pywebview"]
# ///
"""Chat backend against the fake claude, no window, no AWR: send, step tracking, stop, saved history."""
import os
import sys
import tempfile
import time

os.environ["APPDATA"] = tempfile.mkdtemp()  # never touch the user's history
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ampwright"))
import app
import session


def make():
    a = app.Api(claude_path=sys.executable, extra_args=[os.path.join(HERE, "fake_claude.py")])
    a._session = session.Session(sys.executable, HERE, "pipe", a._on_session, None, a._extra_args)
    a._set(claude="up", awr="up")
    a._boot = lambda: restarts.append(1)  # no AWR server here: a restart is only counted
    return a


def wait(cond, what, s=10):
    end = time.time() + s
    while time.time() < end:
        if cond():
            return
        time.sleep(0.05)
    raise AssertionError("timed out: " + what)


restarts = []
a = make()
assert a.send("   ")["ok"] is False
assert a.send("hello")["ok"] is True
assert a.send("second")["ok"] is False and "still working" in a.send("second")["error"]
wait(lambda: a.state()["turn"] == "idle", "turn end")
h = a.history()
assert [i["kind"] for i in h] == ["user", "claude", "step"], h
assert h[2]["tool"] == "create_schematic" and h[2]["summary"] == "name=rc_lpf" and h[2]["status"] == "done", h[2]

a.send("fail now")
wait(lambda: a.state()["turn"] == "idle", "second turn")
st = [i for i in a.history() if i["kind"] == "step"]
assert st[1]["status"] == "failed" and st[1]["error"] == "no such schematic", st

a.send("hang")
wait(lambda: a.history()[-1]["kind"] == "step" and a.history()[-1]["status"] == "running", "running step")
assert a.stop_turn() is True
last = a.history()
assert last[-2]["status"] == "stopped" and last[-1]["kind"] == "note" and a.state()["turn"] == "idle", last[-3:]
wait(lambda: restarts, "restart after stop")
assert a.stop_turn() is False  # nothing to stop now

a.send("after stop")  # same conversation continues after the restart
wait(lambda: a.state()["turn"] == "idle", "turn after stop")
assert "resume=True" in [i for i in a.history() if i["kind"] == "claude"][-1]["text"]
a._session.stop()

n = len(a.history())  # a new start shows the same history; a step left running is shown as stopped
a._update_step(a.history()[-1]["id"], status="running")
b = app.Api()
assert len(b.history()) == n and b.history()[-1]["status"] == "stopped"
assert b.clear_history() and app.Api().history() == []

# a denied or unanswered approval is the user's choice: "denied", no error line; a real error stays "failed"
for sid, text, want in (("d1", "the user denied this in Ampwright", "denied"), ("d2", "timed out waiting for the user", "denied"),
                        ("d3", "no such graph", "failed")):
    b._on_session({"event": "tool_use", "id": sid, "tool": "mcp__AWRMWO-mcp__delete_graph", "input": {"name": "g"}})
    b._on_session({"event": "tool_result", "id": sid, "is_error": True, "text": text})
    it = b.history()[-1]
    assert it["status"] == want and ("error" in it) == (want == "failed"), it

# summaries are cut at a word, with an ellipsis
assert app.cut("Done. I added a graph called S11_dB showing", 30) == "Done. I added a graph called…"
assert app.cut("short", 30) == "short" and app.cut("x" * 40, 10) == "x" * 9 + "…"
s = app.summarize({"text": "Done. I added a graph called S11_dB showing DB(|S(1,1)|)", "graph": "S11_dB"})
assert s == "text=Done. I added a graph called…, graph=S11_dB", s
assert len(app.summarize({k: "word " * 20 for k in "abcd"})) <= 90
# Quick/Design mode: saved, refused mid-turn, a switch restarts; each mode keeps its own folder and conversation
restarts.clear()
m = make()
assert m.state()["mode"] == "quick" and app.load_settings()["mode"] == "quick"
assert m.set_mode("bogus")["ok"] is False
m._set(turn="working")
assert m.set_mode("design")["ok"] is False and app.load_settings()["mode"] == "quick"
m._set(turn="idle")
m._session.session_id = "q1"
assert m.set_mode("design")["ok"] is True
r2 = m.set_mode("quick")  # a second click while the first restart runs: refused, so no second session
wait(lambda: restarts, "restart on mode switch")
time.sleep(0.3)
assert r2["ok"] is False and "still starting" in r2["error"] and len(restarts) == 1, (r2, restarts)
assert app.load_settings()["mode"] == "design" and m.state()["mode"] == "design" and m.state()["claude"] == "connecting"
m._set(claude="up")  # the stubbed _boot never gets there itself
assert m.history()[-1]["text"] == "Switched to Design mode."
m._make_session(sys.executable)
assert m._session.mode == "design" and m._session.workspace == app.WORKSPACES["design"] and m._session.session_id is None
assert os.path.isfile(os.path.join(m._session.workspace, "AGENTIC_PLAN.md"))  # really the v2 folder
m._session.session_id = "d1"
m.save_settings({"mode": "quick"})
m._make_session(sys.executable)
assert (m._session.mode, m._session.workspace, m._session.session_id) == ("quick", app.WORKSPACE, "q1")
m.save_settings({"mode": "design"})
m._make_session(sys.executable)
assert m._session.session_id == "d1"
assert m.set_mode("design")["ok"] is True and len(restarts) == 1  # already in it: no restart
with open(app.SETTINGS, "w", encoding="utf-8") as f:
    f.write('{"mode": "x"}')
assert app.load_settings()["mode"] == "quick"  # an unknown saved mode falls back
# Design mode: an Agent call is one row named after the subagent; its steps carry the parent; its own text stays out of the chat
m.clear_history()
m._on_session({"event": "tool_use", "id": "A1", "tool": "Agent", "parent": None,
               "input": {"subagent_type": "awr-builder", "description": "Build rc_lpf", "prompt": "long brief " * 50}})
m._on_session({"event": "reply", "text": "subagent thinking aloud", "parent": "A1"})
m._on_session({"event": "tool_use", "id": "s1", "tool": "mcp__AWRMWO-mcp__add_element", "input": {"name": "RES"}, "parent": "A1"})
m._on_session({"event": "tool_result", "id": "s1", "is_error": False, "text": "ok", "parent": "A1"})
m._on_session({"event": "tool_result", "id": "A1", "is_error": False, "text": "built", "parent": None})
m._on_session({"event": "reply", "text": "Built. Next the evaluator.", "parent": None})
h = m.history()
assert [i["kind"] for i in h] == ["step", "step", "claude"], h
assert (h[0]["tool"], h[0]["summary"], h[0]["agent"], h[0]["status"], "parent" in h[0]) == ("awr-builder", "Build rc_lpf", True, "done", False), h[0]
assert (h[1]["tool"], h[1]["parent"], h[1]["status"]) == ("add_element", "A1", "done"), h[1]
assert h[2]["text"] == "Built. Next the evaluator."
print("OK: chat, step status (done, failed, stopped, denied), stop and resume, history saved and cleared, word-safe summaries, "
      "Quick/Design mode switch, subagent rows and nested steps")
