"""Stand-in for claude.exe: reads stream-json user lines, prints init / assistant / tool_result / result lines.
Prompts: 'fail...' -> the tool errors; 'hang...' -> a tool starts and never finishes (to test Stop)."""
import json
import sys
import time

a = sys.argv
sid = a[a.index("--resume") + 1] if "--resume" in a else "sess-1"
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": sid})
n = 0
for line in sys.stdin:
    text = json.loads(line)["message"]["content"][0]["text"]
    n += 1
    tid = "tu%d" % n
    out({"type": "assistant", "session_id": sid, "message": {"content": [
        {"type": "text", "text": "echo %s resume=%s" % (text, "--resume" in a)},
        {"type": "tool_use", "id": tid, "name": "mcp__AWRMWO-mcp__create_schematic", "input": {"name": "rc_lpf"}}]}})
    if text.startswith("hang"):
        time.sleep(600)
    bad = text.startswith("fail")
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "is_error": bad,
                                                  "content": [{"type": "text", "text": "no such schematic" if bad else "ok"}]}]}})
    out({"type": "result", "session_id": sid, "is_error": False, "usage": {"output_tokens": 5}})
