"""PreToolUse hook for AWRMWO-mcp tools (see .claude/settings.json).
- save_project / new_project: always ask the user.
- any other write tool whose target document is not named v2_*: deny.
Read-only tools (readOnlyHint in server.py) pass. Set AWRMWO_GUARD=off to disable for manual work."""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DOC_ARGS = ("schematic", "name", "em", "graph", "document", "source_doc")
ASK = {"save_project", "new_project"}
PROJECT_WIDE = {"set_frequencies", "add_equation"}  # no document = project sweep / Global Definitions


def read_only_tools():
    src = open(os.path.join(ROOT, "server.py"), encoding="utf-8").read()
    return set(re.findall(r"@mcp\.tool\(annotations=ToolAnnotations\(readOnlyHint=True\)\)\s*\nasync def (\w+)", src))


def decide(tool_name, tool_input, ro=None):
    """Returns (decision, reason) or None to let the call through."""
    tool = tool_name.rsplit("__", 1)[-1]
    if tool in ASK:
        return "ask", f"{tool} changes the user's project file: the user must approve it."
    if tool in (ro if ro is not None else read_only_tools()) or tool == "reply":
        return None
    if tool in PROJECT_WIDE and not (tool_input or {}).get("document"):
        return "deny", f"{tool} without document changes the whole project. Pass document='v2_<slug>...'."
    for k in DOC_ARGS:
        v = (tool_input or {}).get(k)
        if isinstance(v, str) and v and not v.startswith("v2_"):
            return "deny", f"{tool} targets '{v}', which is not a v2_* document. Agents only change documents they created (named v2_<slug>...)."
    return None


def main():
    if os.environ.get("AWRMWO_GUARD", "").lower() == "off":
        return
    ev = json.load(sys.stdin)
    d = decide(ev.get("tool_name", ""), ev.get("tool_input"))
    if d:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": d[0], "permissionDecisionReason": d[1]}}))


if __name__ == "__main__":
    main()
