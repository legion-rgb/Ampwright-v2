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
sys.path.insert(0, os.path.join(HERE, "..", "fieldnote"))
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
print("OK: chat, step status (done, failed, stopped), stop and resume, history saved and cleared")
