"""Assert checks for checks/promote.py. No AWR needed: python tests/test_promote.py"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "checks"))
import promote as p

root = tempfile.mkdtemp()


def dossier(slug, phase="pass", verdict="VERDICT: PASS", meets=True):
    d = os.path.join(root, "designs", slug)
    os.makedirs(d)
    json.dump({"phase": phase, "round": 0}, open(os.path.join(d, "state.json"), "w"))
    json.dump({"goals": [{"id": "g"}]}, open(os.path.join(d, "spec.json"), "w"))
    json.dump({"_sim": "ok", "g": {"meets": meets}}, open(os.path.join(d, "results.json"), "w"))
    open(os.path.join(d, "verdict.md"), "w").write(verdict)


dossier("good")
dossier("bad", phase="fix", verdict="VERDICT: FAIL", meets=False)
dst = p.promote("good", "rc_block", "an RC", root)
assert sorted(os.listdir(dst)) == ["results.json", "spec.json", "verdict.md"], os.listdir(dst)
assert "| [rc_block](rc_block/) | good | an RC |" in open(os.path.join(root, "library", "README.md")).read()
for args in (("bad", "x", "d"), ("good", "rc_block", "again"), ("good", "Bad-Name", "d"), ("missing", "y", "d")):
    try:
        p.promote(*args, root=root)
        raise AssertionError(f"accepted {args}")
    except ValueError:
        pass
print("OK")
