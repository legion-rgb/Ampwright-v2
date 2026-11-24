# /// script
# dependencies = ["pywin32"]
# ///
"""Evaluate spec.json goals against graph data. uv run checks/check_spec.py designs/<slug> [--data file.json]
--data: {graph name: graph_data(summary=False) output}. Writes <slug>/results.json, exit 1 if any goal fails.
Values are compared in the trace's own base units (Hz, A, V, ...), not display units."""
import json
import os
import sys


def _trace(rows, goal):
    m = goal.get("measurement")
    hits = [r for r in rows if m in r.get("measurement", "") or m in r.get("label", "")] if m else rows
    if len(hits) != 1:
        raise ValueError(f"{len(hits)} traces match measurement={m!r}; have {[r.get('measurement') for r in rows]}")
    return hits[0]


def _goal(g, rows):
    t = _trace(rows, g)
    pts = sorted(zip(t["x"], t["y"]))
    if not pts:
        raise ValueError(f"trace {t.get('measurement')!r} has no points (not simulated yet?)")
    if t.get("truncated"):
        raise ValueError(f"trace {t.get('measurement')!r} was truncated by graph_data max_points")
    op, target = g["op"], g["value"]
    if "over_hz" in g:
        lo, hi = g["over_hz"]
        ys = [y for x, y in pts if lo <= x <= hi]
        if not ys:
            raise ValueError(f"no points in {lo}..{hi} Hz (x range {pts[0][0]}..{pts[-1][0]})")
        if op == "<=":
            v = max(ys)
        elif op == ">=":
            v = min(ys)
        else:
            v = max(ys, key=lambda y: abs(y - target))
        how = f"worst case ({op}) over {lo:g}..{hi:g} Hz of {t['measurement']}"
    elif "at" in g:
        (var, x), = g["at"].items()
        k = next((i for i in range(len(pts) - 1) if pts[i][0] <= x <= pts[i + 1][0]), None)
        if k is None:
            raise ValueError(f"{var}={x} outside trace x range {pts[0][0]}..{pts[-1][0]}")
        (x0, y0), (x1, y1) = pts[k], pts[k + 1]
        v = y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        how = f"linear interpolation of {t['measurement']} at {var}={x:g}"
    else:
        raise ValueError("goal needs 'over_hz' or 'at'")
    if op == "<=":
        ok = v <= target
    elif op == ">=":
        ok = v >= target
    elif op == "within":
        ok = abs(v - target) <= g["tol"]
    else:
        raise ValueError(f"unknown op {op!r}")
    return {"measured": v, "meets": bool(ok), "how": how}


def evaluate(spec, data):
    out = {"_sim": "ok"}
    for g in spec["goals"]:
        try:
            rows = data[g["graph"]]
            if isinstance(rows, str):  # a fetch error recorded by main()
                raise ValueError(rows)
            out[g["id"]] = _goal(g, rows)
        except (ValueError, KeyError) as e:
            out[g["id"]] = {"measured": None, "meets": False, "how": f"error: {e!r}"}
    return out


def main(argv):
    if len(argv) < 2:
        sys.exit("usage: check_spec.py designs/<slug> [--data file.json]")
    d = argv[1]
    spec = json.load(open(os.path.join(d, "spec.json"), encoding="utf-8-sig"))  # -sig: tolerate a BOM
    if len(argv) == 4 and argv[2] == "--data":
        data = json.load(open(argv[3], encoding="utf-8-sig"))
    else:
        from _awr import call_list as call
        data = {}
        for name in {g["graph"] for g in spec["goals"]}:
            try:
                data[name] = call("graph_data", graph=name, summary=False, max_points=10**6)  # default 2000 cut long sweeps
            except Exception as e:  # keep going: the other graphs may still be readable
                data[name] = f"{type(e).__name__}: {e}"
    res = evaluate(spec, data)
    bad = {k: v for k, v in data.items() if isinstance(v, str)}
    if bad:
        res["_sim"] = "error: " + "; ".join(f"{k}: {v}" for k, v in bad.items())
    with open(os.path.join(d, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))
    return 0 if res["_sim"] == "ok" and all(v["meets"] for k, v in res.items() if k != "_sim") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
