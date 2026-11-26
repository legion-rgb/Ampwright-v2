"""Phase C check, no AWR needed: the guard hook's decisions, and the real hook commands on stdin.
Run: uv run python tests/test_hooks.py"""
import json
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "checks"))
from hook_guard import decide, read_only_tools  # noqa: E402

ro = read_only_tools()
assert {"project_info", "list_wires", "graph_data"} <= ro and "connect" not in ro, ro
P = "mcp__Ampwright__"
assert decide(P + "save_project", {"user_confirmed": True}, ro)[0] == "ask"
assert decide(P + "new_project", {}, ro)[0] == "ask"
assert decide(P + "delete_schematic", {"name": "Schematic 1"}, ro)[0] == "deny"
assert decide(P + "set_parameter", {"schematic": "test", "element": "R1"}, ro)[0] == "deny"
assert decide(P + "add_measurement", {"graph": "v2_x_s", "source_doc": "mine"}, ro)[0] == "deny"
assert decide(P + "set_parameter", {"schematic": "v2_rc", "element": "R1"}, ro) is None
assert decide(P + "create_graph", {"name": "v2_rc_s"}, ro) is None
assert decide(P + "set_graph_axis", {"graph": "v2_rc_s", "min": -60}, ro) is None
assert decide(P + "set_graph_axis", {"graph": "mine", "min": -60}, ro)[0] == "deny"  # not a v2_ graph
assert decide(P + "set_graph_trace", {"graph": "mine", "color": "#ff0000"}, ro)[0] == "deny"
assert decide(P + "add_graph_marker", {"graph": "v2_rc_s", "measurement": 1, "x": 1e9}, ro) is None
assert decide(P + "clear_graph_markers", {"graph": "LMatch_Response"}, ro)[0] == "deny"
assert decide(P + "list_elements", {"schematic": "Schematic 1"}, ro) is None  # reads are fine
assert decide(P + "simulate", {}, ro) is None
assert decide(P + "set_frequencies", {"start_hz": 1, "stop_hz": 2}, ro)[0] == "deny"  # project-wide sweep
assert decide(P + "add_equation", {"expression": "a=1"}, ro)[0] == "deny"  # Global Definitions
assert decide(P + "set_frequencies", {"start_hz": 1, "stop_hz": 2, "document": "v2_rc"}, ro) is None
assert decide(P + "add_equation", {"expression": "a=1", "document": "Schematic 1"}, ro)[0] == "deny"

# the real hook command, as Claude Code runs it: JSON on stdin, JSON decision on stdout
def run(script, ev, env=None):
    p = subprocess.run([sys.executable, os.path.join(ROOT, "checks", script)], input=json.dumps(ev),
                       capture_output=True, text=True, env={**os.environ, **(env or {})}, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout) if p.stdout.strip() else None

out = run("hook_guard.py", {"tool_name": P + "delete_element", "tool_input": {"schematic": "test", "element": "R1"}})
assert out["hookSpecificOutput"]["permissionDecision"] == "deny", out
assert run("hook_guard.py", {"tool_name": P + "delete_element", "tool_input": {"schematic": "test"}},
           {"AWRMWO_GUARD": "off"}) is None
assert run("hook_guard.py", {"tool_name": P + "project_info", "tool_input": {}}) is None

# E.1 optimizer tools: same v2_* rule; opt_state is read-only
assert run("hook_guard.py", {"tool_name": P + "run_optimizer", "tool_input": {"schematic": "Schematic 1"}})["hookSpecificOutput"]["permissionDecision"] == "deny"
assert run("hook_guard.py", {"tool_name": P + "sweep", "tool_input": {"schematic": "v2_x", "graph": "user_graph"}})["hookSpecificOutput"]["permissionDecision"] == "deny"
assert run("hook_guard.py", {"tool_name": P + "add_opt_goal", "tool_input": {"schematic": "v2_x"}}) is None
assert run("hook_guard.py", {"tool_name": P + "opt_state", "tool_input": {}}) is None

settings = json.load(open(os.path.join(ROOT, ".claude", "settings.json"), encoding="utf-8"))
assert settings["hooks"]["PreToolUse"][0]["matcher"] == P + ".*"
print("OK")
