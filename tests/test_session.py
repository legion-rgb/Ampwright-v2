"""Session against the fake claude, no AWR and no real Claude: python tests/test_session.py"""
import os
import queue
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "fieldnote"))
import session

ev = queue.Queue()


def get(kind):
    while True:
        m = ev.get(timeout=10)
        if m["event"] == kind:
            return m


s = session.Session(sys.executable, HERE, "pipe", ev.put, extra_args=[os.path.join(HERE, "fake_claude.py")])
s.send("hello")
assert get("reply")["text"] == "echo hello resume=False"
tu = get("tool_use")
assert tu["id"] == "tu1" and tu["tool"].endswith("create_schematic") and tu["input"] == {"name": "rc_lpf"}, tu
tr = get("tool_result")
assert tr["id"] == "tu1" and tr["is_error"] is False and tr["text"] == "ok", tr
assert get("turn_end")["is_error"] is False and s.session_id == "sess-1"

s.send("fail please")  # same process, second turn
get("reply")
tr = get("tool_result")
assert tr["id"] == "tu2" and tr["is_error"] is True and tr["text"] == "no such schematic", tr
get("turn_end")

s.send("hang")  # a tool that never finishes: Stop must kill the process, and say nothing more
get("tool_use")
pid = s._proc.pid
s.stop()
assert not s.running()
assert str(pid) not in os.popen('tasklist /FI "PID eq %d"' % pid).read(), "child still alive"
s.send("again")  # restarts and resumes the same conversation
assert get("reply")["text"] == "echo again resume=True"
s.stop()
la = session.lean_args("pipe")  # the channel reply tool is hidden: the app shows Claude's own answer
assert la[la.index("--disallowedTools") + 1] == "mcp__AWRMWO-mcp__reply", la
print("OK: replies, tool calls, tool results (ok and error), stop kills the child, resume works, reply tool hidden")
