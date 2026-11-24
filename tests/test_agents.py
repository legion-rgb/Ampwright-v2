"""Phase A check, no AWR needed: agent files are well formed and their tool permissions are safe.
Run: uv run --with "mcp>=1.2,<2" --with pywin32 python tests/test_agents.py"""
import glob
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
src = open(os.path.join(ROOT, "server.py"), encoding="utf-8").read()
# tool name -> read-only?
tools = {m.group(2): bool(m.group(1)) for m in re.finditer(
    r"@mcp\.tool\((annotations=ToolAnnotations\(readOnlyHint=True\))?\)\s*\nasync def (\w+)", src)}
assert len(tools) > 30 and tools["project_info"] and not tools["save_project"], tools
tools["reply"] = False  # registered in hub.py

READ_ONLY_AGENTS = {"verification-judge", "circuit-evaluator", "design-reviewer", "test-runner", "lesson-keeper"}
NO_AWR = {"circuit-theory"}
FORBIDDEN = {"save_project", "new_project", "delete_schematic", "delete_em_structure", "delete_graph"}
EXPECTED = READ_ONLY_AGENTS | NO_AWR | {"awr-builder", "circuit-fixer"}

seen = set()
for path in glob.glob(os.path.join(ROOT, ".claude", "agents", "*.md")):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n(.+)", text, re.S)
    assert m, path + ": no frontmatter"
    fm = dict(l.split(":", 1) for l in m.group(1).splitlines())
    fm = {k.strip(): v.strip() for k, v in fm.items()}
    name = fm.get("name")
    if name not in EXPECTED:
        continue  # v1 dev agents (fieldnote-*) are not part of the loop
    seen.add(name)
    assert name == os.path.basename(path)[:-3], path + ": name does not match file"
    assert fm.get("description") and fm.get("model") in ("opus", "sonnet", "haiku"), name
    listed = [t.strip() for t in fm.get("tools", "").split(",") if t.strip()]
    mcp = [t.split("__")[-1] for t in listed if t.startswith("mcp__")]
    for t in listed:
        if t.startswith("mcp__"):
            assert t.startswith("mcp__AWRMWO-mcp__"), (name, t)
    for t in mcp:
        assert t in tools, (name, "unknown tool", t)
        assert t not in FORBIDDEN, (name, "forbidden tool", t)
        if name in READ_ONLY_AGENTS:
            assert tools[t], (name, "read-only agent has write tool", t)
    if name in NO_AWR:
        assert not mcp, (name, "must not touch AWR")
    if name == "test-runner":
        assert fm["model"] == "haiku"
    if name == "verification-judge":
        assert fm["model"] == "opus"
    body = m.group(2)
    if name != "lesson-keeper":  # only the keeper edits the lessons (errors.md E014)
        assert not re.search(r"[Aa]dd (a|one) (line to `?playbook|playbook line)", body), (name, "writes playbook.md")
        if name != "test-runner":
            assert "errors.md" in body, (name, "does not read errors.md")

assert seen == EXPECTED, ("missing agents", EXPECTED - seen)
for f in ("CLAUDE.md", "AGENTIC_PLAN.md", "playbook.md", "errors.md", ".mcp.json"):
    assert os.path.isfile(os.path.join(ROOT, f)), f
# every errors.md entry carries all fields, a known status, and unique E-numbers
cat = open(os.path.join(ROOT, "errors.md"), encoding="utf-8").read()
entries = re.findall(r"\n## (E\d{3}) [^\n]+\n(.*?)(?=\n## |\Z)", cat, re.S)
assert entries and len({e for e, _ in entries}) == len(entries), "errors.md: missing or duplicate E-numbers"
for e, body in entries:
    for field in ("Symptom", "Cause", "Fix", "Status", "Seen", "Recheck"):
        assert f"**{field}:**" in body, (e, "missing", field)
    st = re.search(r"\*\*Status:\*\* (\S+)", body).group(1)
    assert st in ("fixed-in-code", "workaround", "open", "retired"), (e, st)
print("OK", len(seen), "agents,", len(tools), "tools")
