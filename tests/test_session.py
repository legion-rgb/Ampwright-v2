"""Session against the fake claude, no AWR and no real Claude: python tests/test_session.py"""
import os
import queue
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ampwright"))
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
assert la[la.index("--disallowedTools") + 1] == "mcp__Ampwright__reply", la
assert la[la.index("--tools") + 1] == "Read,Glob,Grep" and la[la.index("--append-system-prompt") + 1] == session.PROMPT
ld = session.lean_args("pipe", "design")  # Design mode: dossier writes + the agent loop, Design Lead prompt, same approvals
assert ld[ld.index("--tools") + 1] == "Read,Glob,Grep,Write,Edit,Agent,Bash", ld
assert ld[ld.index("--append-system-prompt") + 1] == session.DESIGN_PROMPT, ld
assert ld[ld.index("--permission-prompt-tool") + 1] == "mcp__Ampwright__approve", ld
nested = queue.Queue()  # a subagent's step carries the id of the Agent call that started it
n = session.Session(sys.executable, HERE, "pipe", nested.put, mode="design")
n._handle({"type": "assistant", "parent_tool_use_id": "toolu_A", "message": {"content": [
    {"type": "tool_use", "id": "t9", "name": "Read", "input": {}}]}})
n._handle({"type": "user", "parent_tool_use_id": "toolu_A", "message": {"content": [
    {"type": "tool_result", "tool_use_id": "t9", "content": "x"}]}})
n._handle({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "toolu_A", "name": "Agent", "input": {}}]}})
assert [nested.get()["parent"] for _ in range(3)] == ["toolu_A", "toolu_A", None]
print("OK: replies, tool calls, tool results (ok and error), stop kills the child, resume works, reply tool hidden, "
      "Design args, subagent steps keep their parent")
