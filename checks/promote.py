"""Promote a passing design to the verified block library (AGENTIC_PLAN E.2).
python checks/promote.py <slug> <block> "<one-line description>"  -> library/<block>/ plus a row in library/README.md.
Refuses unless designs/<slug> is PASS: state phase "pass", verdict PASS, every spec goal met. Never overwrites a block."""
import json
import os
import re
import shutil
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FILES = ("spec.md", "spec.json", "theory.md", "predictions.json", "build_log.md", "results.json", "verdict.md", "report.md")
INDEX_HEAD = "# Verified block library\n\nPassing designs, promoted with `checks/promote.py`. Theory reuses them; the Builder rebuilds from `build_log.md`.\n\n| block | from design | what it does |\n|---|---|---|\n"


def _load(path):
    return json.load(open(path, encoding="utf-8-sig"))


def passing(d):
    """[] when designs/<slug> is a clean PASS, else the reasons."""
    why = []
    try:
        st, res, spec = _load(os.path.join(d, "state.json")), _load(os.path.join(d, "results.json")), _load(os.path.join(d, "spec.json"))
        verdict = open(os.path.join(d, "verdict.md"), encoding="utf-8").read()
    except (OSError, ValueError) as e:
        return [f"incomplete dossier ({type(e).__name__}: {e})"]
    if st.get("phase") != "pass":
        why.append(f"phase {st.get('phase')!r}")
    if not re.search(r"VERDICT:\W*PASS", verdict):
        why.append("verdict not PASS")
    if res.get("_sim") != "ok" or not all(res.get(g["id"], {}).get("meets") for g in spec["goals"]):
        why.append("goals not all met")
    return why


def promote(slug, block, desc, root=ROOT):
    d, lib = os.path.join(root, "designs", slug), os.path.join(root, "library")
    if not re.fullmatch(r"[a-z0-9_]+", block):
        raise ValueError("block name: lower case, digits and _ only")
    why = passing(d)
    if why:
        raise ValueError(f"{slug} is not a clean PASS: {', '.join(why)}")
    dst = os.path.join(lib, block)
    if os.path.exists(dst):
        raise ValueError(f"library/{block} already exists")
    os.makedirs(dst)
    for f in FILES:
        if os.path.exists(os.path.join(d, f)):
            shutil.copy2(os.path.join(d, f), dst)
    idx = os.path.join(lib, "README.md")
    head = "" if os.path.exists(idx) else INDEX_HEAD
    with open(idx, "a", encoding="utf-8") as fh:
        fh.write(head + f"| [{block}]({block}/) | {slug} | {desc} |\n")
    return dst


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    print(promote(*sys.argv[1:]))
