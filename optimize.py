"""AWR optimizer and parameter sweeps (AGENTIC_PLAN E.1). Checked live 21 Nov on v2_opt_probe: goal x in Hz, y in the
measurement's own unit (dB for DB(...)), constraints in SI; Simplex took C1 from 1 nF to 477.2 pF in 0.7 s."""
import time

import graphs as gr
import schematic as sc
from connection import awr, find

GOAL_TYPE = {"=": 0, "<": 1, ">": 2}  # mwOptGoalType
UT_FREQUENCY, UT_NONE = 1, 0  # mwUnitType


def _goals():
    return [{"name": g.Name, "schematic": g.CircuitName, "measurement": g.MeasName, "enabled": bool(g.Enable),
             "cost": float(g.Cost)} for g in awr().Project.OptGoals]


def _methods(o):
    return [o.TypeName(i) for i in range(1, o.TypeCount + 1)]  # 1-based (index 0 raises)


def _opt_params(only=None):
    """(schematic, element, parameter, COM param) for every parameter flagged Optimize, in every schematic or one."""
    out = []
    for s in awr().Project.Schematics:
        if only and s.Name != only:
            continue
        for ref, e in sc._refs(s):
            for p in e.Parameters:
                if p.Optimize:
                    out.append((s.Name, ref, p.Name, p))
    return out


def _var(s, ref, name, p):
    return {"schematic": s, "element": ref, "parameter": name, "value": p.ValueAsString, "unit": p.UnitString,
            "si": p.ValueAsDouble, "lower": p.LowerConstraint if p.Constrain else None,
            "upper": p.UpperConstraint if p.Constrain else None}


def opt_state_sync():
    o = awr().Project.Optimizer
    return {"goals": _goals(), "variables": [_var(*v) for v in _opt_params()], "method": _methods(o)[o.Type - 1],
            "methods": _methods(o)}


def set_opt_variable_sync(schematic, element, parameter, optimize=True, lower=None, upper=None):
    p = find(sc._elem(sc._sch(schematic), element).Parameters, parameter)
    if optimize and (lower is None or upper is None):
        raise ValueError("give lower and upper (SI units) so the optimizer stays in a sane range")
    p.Optimize = bool(optimize)
    if optimize:
        if not lower < upper:
            raise ValueError(f"lower {lower} must be below upper {upper}")
        p.Constrain, p.LowerConstraint, p.UpperConstraint = True, float(lower), float(upper)
    return _var(schematic, element, parameter, p)


def add_opt_goal_sync(schematic, measurement, op, value, start_hz, stop_hz, weight=1.0):
    if op not in GOAL_TYPE:
        raise ValueError(f"op must be one of {list(GOAL_TYPE)}")
    sc._sch(schematic)  # fail early on a wrong name
    g = awr().Project.OptGoals.Add(schematic, measurement, GOAL_TYPE[op], float(weight), 2, float(start_hz), float(stop_hz),
                                   UT_FREQUENCY, float(value), float(value), UT_NONE)
    return {"name": g.Name, "cost": float(g.Cost)}


def delete_opt_goals_sync(schematic):
    goals = awr().Project.OptGoals
    names = [g.Name for g in goals if g.CircuitName == schematic]
    for n in names:
        goals.Remove(n)
    return {"deleted": names}


def run_optimizer_sync(schematic, method="Simplex Optimizer", iterations=200, timeout_s=300):
    """Optimizes only when every enabled goal and every Optimize flag belongs to `schematic`: the optimizer is
    project-wide, so anything else would change documents the agent does not own."""
    p, o = awr().Project, awr().Project.Optimizer
    other = [g["name"] for g in _goals() if g["enabled"] and g["schematic"] != schematic]
    other += [f"{s}.{r}.{n}" for s, r, n, _ in _opt_params() if s != schematic]
    if other:
        raise ValueError(f"other documents have enabled goals or optimize flags: {other}. Only {schematic} may take part.")
    if not p.OptGoals.Count or not _opt_params(schematic):
        raise ValueError("needs at least one goal (add_opt_goal) and one variable (set_opt_variable) first")
    names = _methods(o)
    if method not in names:
        raise ValueError(f"unknown method {method!r}. Use one of: {names}")
    o.Type, o.MaxIterations, o.StopAtMin = names.index(method) + 1, int(iterations), True
    start = float(p.OptGoals.TotalCost)
    t0, deadline = time.time(), time.time() + min(timeout_s, 1800)  # cap: this loop holds the COM thread
    o.start()
    while o.Running and time.time() < deadline:
        time.sleep(0.5)
    timed_out = bool(o.Running)
    if timed_out:
        o.stop()
    return {"method": method, "iterations": int(o.Iteration), "seconds": round(time.time() - t0, 1), "timed_out": timed_out,
            "start_cost": start, "best_cost": float(o.BestCost), "goals": _goals(),
            "variables": [_var(*v) for v in _opt_params(schematic)]}


def _y_at(rows, measurement, x):
    hits = [r for r in rows if r["measurement"].split(":", 1)[-1] == measurement or r["measurement"] == measurement]
    if len(hits) != 1:
        raise ValueError(f"measurement {measurement!r} {'is ambiguous' if hits else 'not found'}: {[r['measurement'] for r in rows]}")
    pts = sorted(zip(hits[0]["x"], hits[0]["y"]))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    raise ValueError(f"x={x} outside the trace ({pts[0][0]}..{pts[-1][0]})" if pts else "trace has no points")


def sweep_sync(schematic, element, parameter, values, graph, measurement, at_hz):
    """Set the parameter to each value, simulate the graph, read the measurement at at_hz; then restore the old value."""
    p = find(sc._elem(sc._sch(schematic), element).Parameters, parameter)
    old = p.ValueAsString
    table = []
    try:
        for v in values:
            sc._set_param(sc._elem(sc._sch(schematic), element), parameter, v)
            gr.simulate_sync(graph=graph)
            table.append({"value": v, "y": _y_at(gr.graph_data_sync(graph, max_points=10**6), measurement, at_hz)})
    finally:
        p.ValueAsString = old
        gr.simulate_sync(graph=graph)  # so the graph shows the restored design again
    return {"parameter": f"{element}.{parameter}", "restored": old, "at_hz": at_hz, "table": table}
