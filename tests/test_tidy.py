"""Tidy check on built-in fixtures, no AWR needed: python tests/test_tidy.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "checks"))
import check_tidy  # noqa: E402


def _el(id_, *pins):
    return {"id": id_, "pins": [{"pin": i, "x": x, "y": y} for i, (x, y) in enumerate(pins, 1)]}


def _w(x1, y1, x2, y2, net):
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "net": net}


ELEMS = [_el("R1", (0, 0), (1000, 0)), _el("R2", (3000, 0), (4000, 0)), _el("GND1", (0, 1000))]
GOOD = [_w(1000, 0, 3000, 0, "N1"), _w(2000, 0, 2000, 1000, "N1"), _w(0, 0, 0, 1000, "N2"), _w(4000, 0, 5000, 0, "N3")]
CASES = {
    "pass": (GOOD, []),
    "cross": (GOOD + [_w(2500, -500, 2500, 500, "N9")], ["crossing"]),
    "body": (GOOD + [_w(500, -1000, 500, 1000, "N5")], ["body"]),
    "pin": (GOOD[:3] + [_w(4000, -1000, 4000, 1000, "N6")], ["pin"]),
}
for name, (wires, want) in CASES.items():
    got = sorted({i["kind"] for i in check_tidy.check(ELEMS, wires)})
    assert got == want, (name, got)
kinds = lambda w: [i["kind"] for i in check_tidy.check([], w)]
assert kinds([_w(0, 0, 2000, 0, "A"), _w(1000, 0, 3000, 0, "B")]) == ["overlap"]
assert kinds([_w(0, 500, 2000, 500, "A"), _w(1000, 0, 1000, 1000, "A")]) == ["crossing"]
assert kinds([_w(0, 500, 2000, 500, "A"), _w(1000, 500, 1000, 1000, "A")]) == []  # same-net T is fine
print("OK")
