# /// script
# dependencies = ["pywin32"]
# ///
"""Schematic tidiness check. uv run checks/check_tidy.py <schematic> | --fixture file.json
Fixture: {"elements": <list_elements output>, "wires": <list_wires output>}. Prints JSON, exit 1 if issues."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from helpers import on_segment  # noqa: E402

BODY_MARGIN = 100  # one 100-unit grid step each side of a 2-pin part's axis (RES is 1000 long)


def _seg(w):
    return (w["x1"], w["y1"], w["x2"], w["y2"])


def _ends(s):
    return {(s[0], s[1]), (s[2], s[3])}


def _pair(a, b):
    """'overlap' | 'cross' (both interiors) | 'touch' (any other shared point, e.g. T or corner) | None.
    shortcut: orthogonal segments only (AWR wires are), diagonals are not handled."""
    ah, bh = a[1] == a[3], b[1] == b[3]
    if ah == bh:  # parallel
        i, j = (1, 0) if ah else (0, 1)  # i: constant axis, j: running axis
        if a[i] != b[i]:
            return None
        lo = max(min(a[j], a[j + 2]), min(b[j], b[j + 2]))
        hi = min(max(a[j], a[j + 2]), max(b[j], b[j + 2]))
        return "overlap" if lo < hi else ("touch" if lo == hi else None)
    h, v = (a, b) if ah else (b, a)
    x, y = v[0], h[1]
    if not (min(h[0], h[2]) <= x <= max(h[0], h[2]) and min(v[1], v[3]) <= y <= max(v[1], v[3])):
        return None
    inner = (x, y) not in _ends(h) and (x, y) not in _ends(v)
    return "cross" if inner else "touch"


def _through(s, box):
    """Segment passes through the open interior of box (l, t, r, b)."""
    l, t, r, b = box
    if s[1] == s[3]:
        return t < s[1] < b and max(min(s[0], s[2]), l) < min(max(s[0], s[2]), r)
    return l < s[0] < r and max(min(s[1], s[3]), t) < min(max(s[1], s[3]), b)


def check(elements, wires):
    issues = []

    def add(kind, detail):
        issues.append({"kind": kind, "detail": detail})

    segs = [(_seg(w), w.get("net")) for w in wires if _seg(w)[:2] != _seg(w)[2:]]  # zero-length wires carry no geometry
    for n, (a, na) in enumerate(segs):
        for b, nb in segs[n + 1:]:
            hit, same = _pair(a, b), na is not None and na == nb
            if hit == "overlap":
                add("overlap", f"{a} and {b} run over each other (nets {na}, {nb})")
            elif hit == "cross":
                add("crossing", f"{a} and {b} cross (nets {na}, {nb})")
            elif hit == "touch" and not same and not (_ends(a) & _ends(b)):
                add("crossing", f"{a} and {b} of different nets meet mid-wire (nets {na}, {nb})")
    pins = [((e["id"], p["pin"]), (p["x"], p["y"])) for e in elements for p in e["pins"]]
    for s, net in segs:
        for ref, xy in pins:
            if xy not in _ends(s) and on_segment(xy, s):
                add("pin", f"wire {s} (net {net}) passes over pin {ref[0]}:{ref[1]} at {xy}")
    for e in elements:
        pts = [(p["x"], p["y"]) for p in e["pins"]]
        if len(pts) < 2:
            continue  # one-pin parts (ground, port) have no body
        l, r = min(p[0] for p in pts), max(p[0] for p in pts)
        t, b = min(p[1] for p in pts), max(p[1] for p in pts)
        if l == r:
            l, r = l - BODY_MARGIN, r + BODY_MARGIN
        if t == b:
            t, b = t - BODY_MARGIN, b + BODY_MARGIN
        for s, net in segs:
            if _through(s, (l, t, r, b)):
                add("body", f"wire {s} (net {net}) runs through the body of {e['id']}")
    return issues


def main(argv):
    if len(argv) == 3 and argv[1] == "--fixture":
        d = json.load(open(argv[2], encoding="utf-8-sig"))
        elements, wires = d["elements"], d["wires"]
    elif len(argv) == 2:
        from _awr import call_list as call
        elements, wires = call("list_elements", schematic=argv[1]), call("list_wires", schematic=argv[1])
    else:
        sys.exit("usage: check_tidy.py <schematic> | --fixture file.json")
    issues = check(elements, wires)
    print(json.dumps({"ok": not issues, "issues": issues}, indent=1))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
