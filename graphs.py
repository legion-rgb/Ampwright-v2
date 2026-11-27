"""Frequencies, simulation, status window, graphs and plots."""
import io
import math
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


def simulate_sync(wait_seconds=0, graph=None, tidy=True):
    awr().Status.RemoveAllItems()  # so the errors returned belong to this run only
    if graph:
        # SimulateMeasurements is blocking (checked live: 28 s for 400k points) and leaves AnalyzeState at 3 ("ended").
        g = find(awr().Project.Graphs, graph)
        g.SimulateMeasurements()
        # "ended, 0 errors" also comes back when the solver never ran (Analyst input rejected): no data is the real failure
        empty = [m.Name for m in g.Measurements if not _has_data(m)]
        if empty:
            raise RuntimeError(f"Simulation ended without data for {empty}; the solver probably rejected the input. Check em_simulation_log and check_em_setup. State: {simulation_state_sync()}")
        out = {**simulation_state_sync(), "graph": graph}
        if tidy:  # every graph leaves a simulation readable; tidy=False keeps hand-set axes
            out["tidy"] = tidy_graph_sync(graph)
        return out
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


def set_frequencies_sync(start_hz=None, stop_hz=None, points=None, step=None, log=False, document=None, around_hz=None):
    if around_hz is not None:  # one frequency asked for: f/4 to 2.5 f in steps of f/8 (200 kHz -> 50 to 500 kHz, step 25 kHz)
        if any(v is not None for v in (start_hz, stop_hz, points, step)) or log:
            raise ValueError("around_hz stands alone: don't pass start_hz, stop_hz, points, step_hz or log")
        if around_hz <= 0:
            raise ValueError("around_hz must be > 0")
        start_hz, stop_hz, step = around_hz / 4, around_hz * 2.5, around_hz / 8
    elif start_hz is None or stop_hz is None:
        raise ValueError("Give start_hz and stop_hz, or around_hz")
    freqs, unit, scale, mult = h.tidy_freqs(h.freq_list(start_hz, stop_hz, points, step, log), exact=step is not None)
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
    next(u for u in awr().Project.Units if int(u.Type) == 1).MultType = mult  # AWR shows frequency in the sweep's unit too
    return {"document": document or "project", "count": coll.Count, "first_hz": freqs[0], "last_hz": freqs[-1],
            "unit": unit, "first": freqs[0] / scale, "last": freqs[-1] / scale}


def create_graph_sync(name, type="rectangular"):
    if type not in GRAPH_TYPE:
        raise ValueError(f"type must be one of {list(GRAPH_TYPE)}")
    return {"graph": awr().Project.Graphs.Add(name, GRAPH_TYPE[type]).Name}


AXIS = {"x": 1, "y": 2, "y2": 3}  # Graph.Axes(i): 1 = x, 2 = first y axis, 3 = second y axis (only if the graph has one)


def set_graph_axis_sync(graph, axis="y", min=None, max=None, step=None, auto=False, label=None):
    """Set an axis range, grid step and/or label. auto=True hands the axis back to AWR (min/max/step then ignored).
    shortcut: log scale left out, the mwScaleType values are not documented here."""
    if axis not in AXIS:
        raise ValueError(f"axis must be one of {list(AXIS)}")
    if not auto and min is not None and max is not None and min >= max:
        raise ValueError("min must be below max")
    g = find(awr().Project.Graphs, graph)
    if AXIS[axis] > int(g.Axes.Count):
        raise ValueError(f"'{graph}' has {g.Axes.Count} axes; no '{axis}'")
    ax = g.Axes.Item(AXIS[axis])
    if auto:
        ax.AutoScale = True
        ax.MajorGridlinesAutoStep = True
    else:
        if min is not None or max is not None:
            ax.AutoScale = False
            if min is not None:
                ax.MinimumScale = min
            if max is not None:
                ax.MaximumScale = max
        if step is not None:
            ax.MajorGridlinesAutoStep = False
            ax.MajorGridlinesStep = step
    if label is not None:
        ax.LabelVisible = True  # LabelText can only be set while the label is visible
        ax.LabelText = label
    return {"graph": graph, "axis": axis, "auto": bool(ax.AutoScale), "min": ax.MinimumScale, "max": ax.MaximumScale,
            "step": ax.MajorGridlinesStep, "label": ax.LabelText}


DASH = {"solid": 1, "thick": 2, "thin": 3, "thick_thin": 4}  # mwDashStyle
SYMBOL = {"triangle": 1, "square": 2, "diamond": 3, "x": 4, "horizontal_bar": 5, "vertical_bar": 6, "forward_slash": 7,
          "back_slash": 8, "arrow": 9, "circle": 10, "small_x": 11, "cross": 12}  # mwTraceSymbols; "none" hides the symbol


def _traces(g, trace):
    """trace: None = all, a 1-based index, or part of a measurement name ('S(2,1)')."""
    ts = list(g.Traces)
    hits = ts if trace is None else [ts[trace - 1]] if isinstance(trace, int) and 1 <= trace <= len(ts) else \
        [t for t in ts if isinstance(trace, str) and trace in t.Name]
    if not hits:
        raise ValueError(f"No trace '{trace}' on '{g.Name}'. Have: {[t.Name for t in ts]}")
    return hits


def set_graph_trace_sync(graph, trace=None, color=None, dash=None, symbol=None, symbol_size=None, legend=None):
    """color '#RRGGBB'; dash solid|thick|thin|thick_thin; symbol none|<SYMBOL name>; legend = legend text."""
    if dash is not None and dash not in DASH:
        raise ValueError(f"dash must be one of {list(DASH)}")
    if symbol is not None and symbol != "none" and symbol not in SYMBOL:
        raise ValueError(f"symbol must be 'none' or one of {list(SYMBOL)}")
    if color is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError("color must look like '#RRGGBB'")
    out = []
    for t in _traces(find(awr().Project.Graphs, graph), trace):
        if color is not None:
            r, gn, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
            t.Color = r | gn << 8 | b << 16  # AWR colours are BGR longs
        if dash is not None:
            t.DashStyle = DASH[dash]
        if symbol == "none":
            t.SymbolVisible = False
        elif symbol is not None:
            t.Symbol = SYMBOL[symbol]
            t.SymbolVisible = True
        if symbol_size is not None:
            t.SymbolSize = symbol_size
        if legend is not None:
            t.UseDefaultLegendText = False
            t.LegendText = legend
        c = int(t.Color)
        out.append({"trace": t.Name, "color": f"#{c & 255:02x}{c >> 8 & 255:02x}{c >> 16 & 255:02x}", "dash": int(t.DashStyle),
                    "symbol": int(t.Symbol), "symbol_visible": bool(t.SymbolVisible), "symbol_size": int(t.SymbolSize)})
    return out


PALETTE = ["#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7", "#56B4E9", "#000000", "#F0E442"]  # Okabe-Ito: readable on white, colour-blind safe
DB_FLOOR = 150  # dB below the peak: a match dip (-100 dB) must show; only numerical-noise nulls beyond this are cut


def nice_axis(lo, hi, ticks=6):
    """Round (lo, hi, step) that cover the data, with a 1/2/5 x 10^n step and 4 to 10 grid lines, like a hand-drawn plot."""
    if hi - lo < 1e-12 * max(abs(lo), abs(hi), 1e-300):  # flat trace: open the window so the line is not on the frame
        pad = abs(hi) * 0.1 or 1.0
        lo, hi = lo - pad, hi + pad
    raw = (hi - lo) / ticks
    mag = 10 ** math.floor(math.log10(raw))
    for k in (1, 2, 5, 10):
        step = k * mag
        a, b = math.floor(lo / step + 1e-9) * step, math.ceil(hi / step - 1e-9) * step
        if round((b - a) / step) <= 10:
            break
    clean = lambda v: round(v, 12) + 0.0  # no -0.0 or 0.30000000000000004 in the axis
    return clean(a), clean(b), clean(step)


def tidy_graph_sync(graph):
    """What a reviewing engineer would fix: round axis ends and steps that cover every point, titles with units,
    distinct colour-blind-safe trace colours, short legend text, no symbol clutter on dense traces, no stray second y axis.
    Rectangular graphs with simulated data only; anything else is reported as skipped."""
    g = find(awr().Project.Graphs, graph)
    if int(g.Type) != GRAPH_TYPE["rectangular"]:
        return {"graph": graph, "skipped": "not a rectangular graph"}
    rows = graph_data_sync(graph, max_points=10**9, display=True, span_units=False)
    if not rows or not all(r["x"] for r in rows):
        return {"graph": graph, "skipped": "no simulated data yet; simulate first"}
    traces, done = list(g.Traces), {}
    one_doc = len({t.Name.split(":")[0] for t in traces if ":" in t.Name}) == 1
    for i, t in enumerate(traces):  # style
        rgb = int(PALETTE[i % len(PALETTE)][1:], 16)
        t.Color = (rgb & 255) << 16 | (rgb >> 8 & 255) << 8 | rgb >> 16  # RGB -> AWR's BGR
        t.SymbolVisible = len(rows[min(i, len(rows) - 1)]["x"]) <= 20  # a symbol on every one of 100 points is noise
        if one_doc and ":" in t.Name:
            t.UseDefaultLegendText = False
            t.LegendText = t.Name.split(":", 1)[1]
    left = all(int(t.PlotAxis) == 0 for t in traces)
    xs = [x / r["x_scale"] for r in rows for x in r["x"]]
    ys = [y / r["y_scale"] for r in rows for y in r["y"]]
    if rows[0]["y_unit"] == "dB" and ys:
        ys = [max(y, max(ys) - DB_FLOOR) for y in ys]
    plan = [("x", xs, "x_axis")] + ([("y", ys, "y_axis")] if left else [])
    for axis, vals, title in plan:
        lo, hi, step = nice_axis(min(vals), max(vals))
        ax = g.Axes.Item(AXIS[axis])
        ax.AutoScale, ax.MinimumScale, ax.MaximumScale = False, lo, hi
        ax.MajorGridlinesAutoStep, ax.MajorGridlinesStep = False, step
        ax.MajorGridlinesVisible, ax.MinorGridlinesVisible = True, False
        names = list(dict.fromkeys(r[title] for r in rows))
        if len(names) > 1 and axis == "y":  # several measurements share the axis: name the quantity, not each measurement
            units = list(dict.fromkeys(r["y_disp"] for r in rows if r["y_disp"]))
            names = [f"Magnitude ({units[0]})" if units == ["dB"] else f"Value ({', '.join(units)})" if units else "Value"]
        if axis == "x":  # AWR appends the project's unit to the x title itself: "Frequency (GHz)" would show as "Frequency (GHz) (MHz)"
            names = [n.split(" (")[0] for n in names]
        ax.LabelVisible, ax.LabelText = True, " / ".join(names)
        done[axis] = {"min": lo, "max": hi, "step": step, "label": ax.LabelText}
    if left and int(g.Axes.Count) > 2:  # the unused right axis would show a meaningless 0 to 10 scale
        ax = g.Axes.Item(AXIS["y2"])
        ax.GridlineLabelsVisible = ax.LabelVisible = ax.MajorGridlinesVisible = ax.MinorGridlinesVisible = False
    return {"graph": graph, "axes": done, "traces": len(traces)}


def add_graph_marker_sync(graph, measurement, x):
    """A marker at x (the sweep value in base units, e.g. Hz) on a measurement: its 1-based index or part of its name."""
    g = find(awr().Project.Graphs, graph)
    names = [t.Name for t in g.Traces]
    i = measurement if isinstance(measurement, int) else next((k + 1 for k, n in enumerate(names) if measurement in n), 0)
    if not 1 <= i <= len(names):
        raise ValueError(f"No measurement '{measurement}' on '{graph}'. Have: {names}")
    m = g.Markers.Add(names[i - 1], 1, x)
    return {"graph": graph, "marker": m.Name, "measurement": names[i - 1], "sweep": m.SweepValue, "value": m.DataValue(int(m.NumDataValueDim))}  # a method in COM; dimension 1 is x, the last one is y (re/im for complex)


def clear_graph_markers_sync(graph):
    g = find(awr().Project.Graphs, graph)
    g.Markers.RemoveAll()
    return {"graph": graph, "markers": int(g.Markers.Count)}


def arrange_windows_sync(schematic, graph=None, direction="horizontal", only=True):
    """Show the schematic and its graph(s) stacked (horizontal, the default: circuit on top, graphs below in the given order) or side by side
    (vertical), each zoomed to fit (View All). graph: one name or a list (S-parameter plot, Smith chart...).
    only=True minimises every other window so these fill the area. Display only: no document changes."""
    if direction not in ("vertical", "horizontal"):
        raise ValueError("direction must be 'horizontal' (stacked) or 'vertical' (side by side)")
    app = awr()
    graphs = [graph] if isinstance(graph, str) else list(graph or [])
    docs = [(find(app.Project.Schematics, schematic), True)] + [(find(app.Project.Graphs, g), False) for g in graphs]
    names = [d.Name for d, _ in docs]
    wins = {w.Caption: w for w in app.Windows}  # a window is captioned with its document's name
    shown = [wins[d.Name] if d.Name in wins else d.NewWindow() for d, _ in docs]
    for w in app.Windows:
        if only and w.Caption not in names:
            w.WindowState = 2  # mwWS_Minimized
    for w in shown:
        w.WindowState = 3  # mwWS_Normal: Tile does not move a maximised window
    for w in reversed(shown):
        w.Activate()  # Tile follows the stacking order: the window activated last comes first (top / left)
    app.Windows.Tile(1 if direction == "vertical" else 0)  # mwWTD_Vertical / mwWTD_Horizontal
    if len(shown) > 2:  # Tile makes a grid (1 on top, 2 below); with 3+ windows place them in one clean stack / row instead
        W, H = max(w.Left + w.Width for w in shown), max(w.Top + w.Height for w in shown)
        n = len(shown)
        for i, w in enumerate(shown):
            if direction == "horizontal":
                w.Left, w.Top, w.Width, w.Height = 0, i * H // n, W, H // n
            else:
                w.Left, w.Top, w.Width, w.Height = i * W // n, 0, W // n, H
    for w in shown:
        w.Activate()
        w.ViewAll()  # after the tile: the fit depends on the final window size
    return {"windows": names, "direction": direction, "minimised_others": only}


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


def graph_data_sync(graph, max_points=2000, summary=False, display=False, span_units=True):
    """display=True adds x_axis/y_axis text and x_scale/y_scale (base unit -> display unit) for plotting.
    span_units=False keeps the project's frequency unit: AWR axes are in that unit, so tidy_graph needs it."""
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
        if display and span_units and int(m.UnitType(1)) == 1 and xs:  # frequency: pick Hz/kHz/MHz/GHz from the span instead of the project unit
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
