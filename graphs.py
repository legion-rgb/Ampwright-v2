"""Frequencies, simulation, status window, graphs and plots."""
import io
import re
import time

from matplotlib.figure import Figure

import helpers as h
from connection import awr, find

CATEGORY = {0: "error", 1: "warning", 2: "info"}
ANALYZE_STATE = {1: "before_simulate", 2: "simulating", 3: "ended"}
GRAPH_TYPE = {"rectangular": 3, "rectangular_complex": 0, "polar": 1, "smith": 2, "tabular": 4,
              "antenna": 5, "histogram": 6, "3d": 7, "constellation": 8}  # mwGraphType


def status_messages_sync(level="all", limit=200):
    msgs = []
    for g in awr().Status.Groups:
        for it in g.Items:
            cat = CATEGORY.get(int(it.Category), str(it.Category))
            if level in ("all", cat):
                msgs.append({"group": g.Name, "level": cat, "time": str(it.Time), "text": it.Text})
    return msgs[-limit:]


def clear_status_messages_sync():
    awr().Status.RemoveAllItems()
    return {"cleared": True}


def _has_data(m):
    try:
        return bool(m.XValues)
    except Exception:  # raises 'Measurement data is not available' when nothing was computed
        return False


def simulate_sync(wait_seconds=0, graph=None):
    awr().Status.RemoveAllItems()  # so the errors returned belong to this run only
    if graph:
        # SimulateMeasurements is blocking (checked live: 28 s for 400k points) and leaves AnalyzeState at 3 ("ended").
        g = find(awr().Project.Graphs, graph)
        g.SimulateMeasurements()
        # "ended, 0 errors" also comes back when the solver never ran (Analyst input rejected): no data is the real failure
        empty = [m.Name for m in g.Measurements if not _has_data(m)]
        if empty:
            raise RuntimeError(f"Simulation ended without data for {empty}; the solver probably rejected the input. Check em_simulation_log and check_em_setup. State: {simulation_state_sync()}")
        return {**simulation_state_sync(), "graph": graph}
    awr().Project.Simulator.AnalyzeAsync()  # state reads 2 (simulating) right after this returns
    return wait_for_simulation_sync(wait_seconds)


def wait_for_simulation_sync(timeout_s=600):
    sim = awr().Project.Simulator
    deadline = time.time() + min(timeout_s, 3600)  # hard cap: this loop holds the COM thread
    while time.time() < deadline and int(sim.AnalyzeState) != 3:
        time.sleep(1)
    out = simulation_state_sync()
    out["timed_out"] = out["state"] != "ended" and timeout_s > 0
    return out


def simulation_state_sync():
    state = int(awr().Project.Simulator.AnalyzeState)
    errors = status_messages_sync("error", 50)
    return {"state": ANALYZE_STATE.get(state, state), "error_count": len(errors), "errors": errors}


def set_frequencies_sync(start_hz, stop_hz, points=None, step=None, log=False, document=None):
    freqs = h.freq_list(start_hz, stop_hz, points, step, log)
    if document:
        try:
            doc = find(awr().Project.Schematics, document)
        except ValueError:
            doc = find(awr().Project.EMStructures, document)  # an EM structure has its own sweep too
        doc.UseProjectFrequencies = False
        coll = doc.Frequencies
    else:
        coll = awr().Project.Frequencies
    coll.Clear()
    coll.AddMultiple(freqs)
    return {"document": document or "project", "count": coll.Count, "first_hz": freqs[0], "last_hz": freqs[-1]}


def create_graph_sync(name, type="rectangular"):
    if type not in GRAPH_TYPE:
        raise ValueError(f"type must be one of {list(GRAPH_TYPE)}")
    return {"graph": awr().Project.Graphs.Add(name, GRAPH_TYPE[type]).Name}


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _simulator_ids():
    """{friendly name: AWR simulator short name}, from SimulatorInfos. '' = the document's default simulator."""
    ids = {"default": "", "harmonic_balance": "", "linear": ""}  # AWR's own sims have a blank short name and run by default
    for s in awr().SimulatorInfos:
        if s.ShortName:  # e.g. 'AP_DC' for 'APLAC DC'
            ids.setdefault(_norm(s.LongName), s.ShortName)
            ids.setdefault(_norm(s.ShortName), s.ShortName)
    return ids


def add_measurement_sync(graph, source_doc, measurement, simulator=None):
    # The simulator is part of the source name: "<doc>.<ShortName>" (e.g. "AP_IV.AP_DC") runs that document with APLAC DC (checked live).
    if simulator:
        ids = _simulator_ids()
        if _norm(simulator) not in ids:
            raise ValueError(f"Unknown simulator '{simulator}'. Use one of: {sorted(ids)}")
        short = ids[_norm(simulator)]
        source_doc = f"{source_doc}.{short}" if short else source_doc
    m = find(awr().Project.Graphs, graph).Measurements.Add(source_doc, measurement)
    return {"graph": graph, "measurement": m.Name, "simulator": simulator or "default"}


def delete_graph_sync(name):
    awr().Project.Graphs.Remove(find(awr().Project.Graphs, name).Name)
    return {"deleted": name}


def delete_measurement_sync(graph, measurement):
    ms = find(awr().Project.Graphs, graph).Measurements
    hits = [m.Name for m in ms if measurement in (m.Name, m.Name.split(":", 1)[-1])]
    if len(hits) != 1:
        raise ValueError(f"Measurement '{measurement}' {'is ambiguous' if hits else 'not found'} on '{graph}'. Have: {[m.Name for m in ms]}")
    ms.Remove(hits[0])
    return {"graph": graph, "deleted": hits[0]}


KIND = {1: "Frequency", 2: "Capacitance", 3: "Inductance", 4: "Resistance", 5: "Conductance", 6: "Length", 8: "Temperature",
        9: "Angle", 10: "Time", 11: "Voltage", 12: "Current", 13: "Power", 14: "Power"}  # mwUnitType; others plot as plain "x"


def _units():
    """{unit type: (base unit, project display unit, display unit per base unit)}, e.g. 12 -> ('A', 'mA', 0.001)."""
    return {int(u.Type): (u.BaseUnitString, u.UnitString, u.MultValue) for u in awr().Project.Units}


def _unit(m, dim, units):
    try:
        return units.get(int(m.UnitType(dim)), ("", "", 1.0))  # dim 1 = x, 2 = first data dimension
    except Exception:
        return ("", "", 1.0)


def _sweep_text(s, units):
    base, disp, per = units.get(int(s.UnitType), ("", "", 1.0))
    return f"{s.Name} = {s.Value / per:.4g}" + (f" {disp}" if disp else "")


def graph_data_sync(graph, max_points=2000, summary=False, display=False):
    """display=True adds x_axis/y_axis text and x_scale/y_scale (base unit -> project display unit) for plotting."""
    ms = list(find(awr().Project.Graphs, graph).Measurements)
    units = _units()
    out = []
    for m in ms:
        # shortcut: only data dimension 1 (real part / magnitude); complex traces need YValues(2) too
        xs = list(m.XValues or [])
        n = int(m.TraceCount)  # >1 for a family (IV curves): TraceValues(k) is then trace k, named "<meas>#k"
        (xb, xd, xp), (yb, yd, yp) = _unit(m, 1, units), _unit(m, 2, units)
        if not yb and m.MeasName.upper().startswith("DB"):
            yb = yd = "dB"  # shortcut: COM reports no unit type for DB(...), so it is recognised by name only
        if display and int(m.UnitType(1)) == 1 and xs:  # frequency: pick Hz/kHz/MHz/GHz from the span instead of the project unit
            xd, xp = next((u, s) for u, s in (("GHz", 1e9), ("MHz", 1e6), ("kHz", 1e3), ("Hz", 1)) if max(xs) >= s or s == 1)
        for k in range(1, n + 1) if n > 1 else [1]:
            # YValues(k) is data dimension k (complex: re, im pairs), not trace k; TraceValues(k) rows are (x, re[, im])
            ys = [r[1] for r in m.TraceValues(k)] if n > 1 else list(m.YValues(1) or [])
            name = f"{m.Name}#{k}" if n > 1 else m.Name
            label = m.Name
            if n > 1:  # a family is named by the value swept to make it, e.g. "Vstep = -3 V"
                try:
                    label = ", ".join(_sweep_text(s, units) for s in m.SweepLabels(k))
                    label = f"{m.Name} {label}" if len(ms) > 1 else label
                except Exception:
                    label = name
            row = {"measurement": name, "label": label, "x_unit": xb, "y_unit": yb}  # arrays stay in base units (Hz, A, Rad...)
            if display:
                kind = KIND.get(int(m.UnitType(1)), "x")
                row |= {"x_axis": f"{kind} ({xd})" if xd else kind, "y_axis": f"{m.MeasName} ({yd})" if yd else m.MeasName,
                        "y_disp": yd, "x_scale": xp, "y_scale": yp}
            if summary:
                out.append({**row, **h.summarize(xs, ys)})
            else:
                out.append({**row, "x": xs[:max_points], "y": ys[:max_points], "truncated": len(ys) > max_points})
    return out


def graph_png(graph, traces):
    fig = Figure(figsize=(8, 4.5))  # Figure without pyplot: thread-safe, no GUI backend
    ax = fig.subplots()
    for t in traces:  # plotted in the project's display units (GHz, mA, deg...)
        ax.plot([x / t["x_scale"] for x in t["x"]], [y / t["y_scale"] for y in t["y"]], label=t["label"])
    xs = [x / t["x_scale"] for t in traces for x in t["x"]]
    if xs and min(xs) > 0 and max(xs) / min(xs) >= 100:
        ax.set_xscale("log")
    ax.set(title=graph, xlabel=" / ".join(dict.fromkeys(t["x_axis"] for t in traces)),
           ylabel=" / ".join(y) if len(y := list(dict.fromkeys(t["y_axis"] for t in traces))) == 1 else "value (" + ", ".join(dict.fromkeys(t["y_disp"] for t in traces)) + ")")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    return buf.getvalue()
