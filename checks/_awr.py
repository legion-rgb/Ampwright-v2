"""Call one read-only tool on the running AWRMWO-mcp hub over its named pipe (no second COM owner)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def call(tool, **args):
    import fieldnote_client as fc
    sessions = fc.list_sessions()
    if not sessions:
        raise RuntimeError("no AWRMWO hub session found (is AWR + the server running?)")
    pid = int(os.environ.get("AWRMWO_PID", sessions[-1]["pid"]))  # list_sessions is sorted by pid: last = highest
    pipe = next((s["pipe"] for s in sessions if s["pid"] == pid), None)
    if pipe is None:
        raise RuntimeError(f"no hub session with pid {pid}")
    c = fc.PipeClient(pipe, lambda m: None)
    try:
        r = c.request(tool, args)
    finally:
        c.close()
    return json.loads(r) if isinstance(r, str) else r


def call_list(tool, **args):
    """For tools that return a list: the hub unwraps a one-item list into the bare item, so wrap it back."""
    r = call(tool, **args)
    return [r] if isinstance(r, dict) else r
