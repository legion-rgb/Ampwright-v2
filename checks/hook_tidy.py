# /// script
# dependencies = ["pywin32"]
# ///
"""PostToolUse hook after Ampwright connect: runs the tidiness check and tells the agent about crossings.
Never blocks; if AWR or the hub pipe can't be reached it stays silent."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    ev = json.load(sys.stdin)
    sch = (ev.get("tool_input") or {}).get("schematic")
    if not sch:
        return
    try:
        from _awr import call_list as call
        from check_tidy import check
        issues = check(call("list_elements", schematic=sch), call("list_wires", schematic=sch))
    except Exception:
        return  # shortcut: silent when the hub is unreachable; check_tidy is still run by the reviewer
    if issues:
        text = "Tidiness check on %s found %d issue(s) (rule in CLAUDE.md); fix placement before calling it done:\n" % (
            sch, len(issues)) + "\n".join("- %s: %s" % (i["kind"], i["detail"]) for i in issues[:10])
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}))


if __name__ == "__main__":
    main()
