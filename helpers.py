"""Pure logic for the AWR server (no COM), so it can be tested without AWR.

AWR schematic coordinates: integer database units, grid 100, y grows downward.
A 2-pin part such as RES is 1000 long with pin 1 at its origin.
"""

CELL = 3000  # placement grid pitch; a cell keeps 1000 clear of a 1000-long part at any rotation
# Rotating a part by +90 maps right -> up -> left -> down (checked live on PORT and GND).
DIRS = {"right": (1, 0), "up": (0, -1), "left": (-1, 0), "down": (0, 1)}
ORDER = list(DIRS)


def parse_pin(ref):
    """'R1:2' -> ('R1', 2). The pin number is the element's 1-based node index."""
    elem, sep, num = ref.rpartition(":")
    if not sep or not elem or not num.isdigit() or int(num) < 1:
        raise ValueError(f"Pin must look like 'R1:2' (element ID, colon, pin number), got '{ref}'")
    return elem, int(num)


def free_spot(boxes, near=None, cols=8, rows=50):
    """First free grid cell for a new part. boxes: (left, top, right, bottom) of existing parts.
    With near=(x, y), the free cell closest to that point; ties go to the right, then down."""
    def free(x, y):
        return all(r <= x - 1000 or l >= x + 2000 or b <= y - 1000 or t >= y + 2000 for l, t, r, b in boxes)

    cells = [(c * CELL, r * CELL) for r in range(rows) for c in range(cols)]
    if near:
        cells.sort(key=lambda p: abs(p[0] - near[0]) + abs(p[1] - near[1]))  # stable sort keeps row-major ties
    for p in cells:
        if free(*p):
            return p
    raise RuntimeError("No free placement cell left")  # shortcut: fixed 8x50 grid, grow it if real designs hit this


def pin_side(pin, center):
    """Which side of its part a pin sits on: the dominant axis of center -> pin."""
    dx, dy = pin[0] - center[0], pin[1] - center[1]
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy >= 0 else "up"


def offset(pin, side, length):
    dx, dy = DIRS[side]
    return pin[0] + dx * length, pin[1] + dy * length


def rotation(body, side):
    """Rotation (deg) that turns a symbol whose body points `body` at rotation 0 so it points `side`."""
    return 90 * ((ORDER.index(side) - ORDER.index(body)) % 4)


def on_segment(p, s):
    (x, y), (x1, y1, x2, y2) = p, s
    return (min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)
            and (x2 - x1) * (y - y1) == (y2 - y1) * (x - x1))


def route(a, b, obstacles=(), segments=()):
    """Wire segments a -> b that touch no obstacle point (other pins, wire ends), since AWR joins anything
    a wire touches. Straight if aligned, else an L: horizontal-first, then vertical-first. None if all are blocked."""
    (x1, y1), (x2, y2) = a, b
    options = ([[(x1, y1, x2, y2)]] if x1 == x2 or y1 == y2 else
               [[(x1, y1, x2, y1), (x2, y1, x2, y2)], [(x1, y1, x1, y2), (x1, y2, x2, y2)]])
    pts = [p for p in obstacles if p != a and p != b]
    ends = set(obstacles)

    def clean(segs):  # a new corner or end lying mid-way on an existing wire would join that net
        new = {(s[0], s[1]) for s in segs} | {(s[2], s[3]) for s in segs}
        return not any(on_segment(p, w) for p in new - ends for w in segments)
    # shortcut: no detours; a wire lying collinear over a longer existing wire is not detected either
    return next((segs for segs in options if clean(segs) and not any(on_segment(p, s) for p in pts for s in segs)), None)


def freq_list(start, stop, points=None, step=None, log=False):
    if (points is None) == (step is None):
        raise ValueError("Give exactly one of points or step")
    if not 0 < start <= stop:
        raise ValueError("Need 0 < start_hz <= stop_hz")
    if step is not None:
        if log or step <= 0:
            raise ValueError("step must be > 0 and only works with a linear sweep")
        return [start + i * step for i in range(int((stop - start) / step + 1e-9) + 1)]
    if points < 2:
        return [start]
    if log:
        return [start * (stop / start) ** (i / (points - 1)) for i in range(points)]
    return [start + (stop - start) * i / (points - 1) for i in range(points)]


UNITS = (("GHz", 1e9, 9), ("MHz", 1e6, 8), ("kHz", 1e3, 7), ("Hz", 1.0, 6))  # name, Hz per unit, AWR MultType


def tidy_freqs(freqs, exact):
    """Round to 2 decimals in the sweep's own unit (a 500 kHz sweep stays kHz), as (freqs, unit name, Hz per unit, MultType).
    A finer unit is used only if rounding would move an endpoint, merge two points, or (exact: a step sweep) move any point."""
    keep = freqs if exact else [freqs[0], freqs[-1]]
    for name, scale, mult in UNITS:
        if scale > max(freqs) and scale > 1:
            continue
        out = [round(f / scale, 2) for f in freqs]
        if len(set(out)) == len(out) and all(abs(round(f / scale, 2) - f / scale) < 1e-6 for f in keep):
            return [round(v * scale, 3) for v in out], name, scale, mult
    out = [round(f, 2) for f in freqs]  # below 1 Hz: Hz with 2 decimals
    return out, "Hz", 1.0, 6


def summarize(xs, ys, samples=5):
    """min, max, x at each and a few evenly spaced points of one trace."""
    if not ys:
        return {"points": 0}
    lo = min(range(len(ys)), key=ys.__getitem__)
    hi = max(range(len(ys)), key=ys.__getitem__)
    idx = sorted({round(k * (len(ys) - 1) / max(samples - 1, 1)) for k in range(samples)})
    return {"points": len(ys), "x_range": [xs[0], xs[-1]], "min": ys[lo], "x_at_min": xs[lo],
            "max": ys[hi], "x_at_max": xs[hi], "samples": [[xs[i], ys[i]] for i in idx]}


# ---- EM layout (metres inside the API, millimetres in tool I/O) ----

C0 = 299792458.0
TOL_MM = 1e-6
# IEMPort.Flags -> kind, decoded from the port's own InfoText text (Analyst); 32 = AXIEM "Auto" edge port.
PORT_KIND = {5: "lumped_down", 7: "lumped_up", 13: "lumped_up_down", 21: "lumped_as_in_child",
             64: "wave", 192: "wave_custom", 256: "lumped_diff", 32: "edge", 0: "edge"}
OPEN = ("approx_open", "infinite_waveguide", "pml")


def edge_segment(points, edge):
    """Straight run of `edge` ('left','right','top','bottom') of a shape given its vertices [(x, y)...]:
    the two extreme vertices lying on that side of the bounding box. Raises if fewer than two do."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    side = {"left": (0, min(xs)), "right": (0, max(xs)), "bottom": (1, min(ys)), "top": (1, max(ys))}
    if edge not in side:
        raise ValueError(f"edge must be one of {list(side)}")
    axis, v = side[edge]
    on = sorted({p for p in points if abs(p[axis] - v) <= TOL_MM}, key=lambda p: p[1 - axis])
    if len(on) < 2:
        raise ValueError(f"The {edge} side of this shape is not a straight edge (use at={{'p1':..,'p2':..}} instead)")
    return on[0], on[-1]


def _inside(p, box, tol=TOL_MM):
    return box[0] - tol <= p[0] <= box[2] + tol and box[1] - tol <= p[1] <= box[3] + tol


def lint_em(info):
    """Pre-flight lint of an em_info dict (mm, Hz). Returns [{severity, rule, message}]."""
    out = []

    def add(sev, rule, msg):
        out.append({"severity": sev, "rule": rule, "message": msg})

    ports, shapes = info["ports"], info["shapes"]
    enc, bnd = info["enclosure"], info["boundaries"]
    box = (0.0, 0.0, enc["x_mm"], enc["y_mm"])  # the enclosure spans 0..x, 0..y
    bd = info.get("boundary")
    if bd:
        if bd["n_edges"] != 4:
            add("warning", "boundary_not_rectangular", f"Boundary has {bd['n_edges']} edges, 4 expected")
        box = tuple(bd["bbox_mm"])
    elif info["simulator"] == "Analyst":
        add("error", "no_boundary", "Analyst structure has no simulation boundary (create_em_structure draws one; set_em_stackup enclosure redraws it)")
    if not ports:
        add("error", "no_ports", "The structure has no ports")
    nums = sorted({abs(p["number"]) for p in ports})
    if nums and nums != list(range(1, nums[-1] + 1)):
        add("error", "port_numbering", f"Port numbers must run 1..N with no gaps, found {nums}")
    for p in ports:
        n, k, seg = p["number"], p["kind"], p["segment_mm"]
        if k == "wave":
            on_edge = any(all(abs(q[i] - box[j]) <= TOL_MM for q in seg) for i, j in ((0, 0), (0, 2), (1, 1), (1, 3)))
            if not on_edge:
                add("error", "wave_port_off_edge", f"Wave port {n} is not exactly on the enclosure/boundary edge; Analyst drops it ('Missing port {n}')")
        if k == "wave_custom" and not all(_inside(q, box) for q in seg):
            add("error", "wave_custom_outside", f"Wave Custom Size port {n} lies outside the boundary")
        if k == "lumped_diff" and -n not in {q["number"] for q in ports}:
            add("error", "diff_missing_negative", f"Lumped differential port {n} has no port {-n} on the facing edge")
        if k == "lumped_down":
            mid = ((seg[0][0] + seg[1][0]) / 2, (seg[0][1] + seg[1][1]) / 2)
            below = any(s["em_layer"] and s["em_layer"] > p["em_layer"] and _inside(mid, s["bbox_mm"]) for s in shapes)
            if not below and bnd["bottom"] not in ("perfect_conductor", "real_conductor"):
                add("error", "lumped_down_no_ground", f"Lumped Down port {n} has no conductor below it (no shape on a deeper EM layer, bottom boundary is {bnd['bottom']})")
        if not p["associated"] or not any(_inside(q, s["bbox_mm"]) for s in shapes for q in seg):
            add("error", "port_not_on_shape", f"Port {n} does not touch any shape")
    freqs = info["frequencies_hz"]
    sides = (bd or {}).get("edges", {})
    # AXIEM's Approx Open is a planar boundary model that needs no lambda/4 of air (only a warning); Analyst's does, but only if it radiates
    open_ = info.get("radiating") or any(v in OPEN for v in (bnd["top"], bnd["bottom"], *sides.values()))
    if freqs and shapes and open_:
        lam4 = C0 / min(freqs) / 4 * 1e3
        # shortcut: shapes spanning the whole box (ground planes) do not count as the radiator
        rad = [s for s in shapes if not (s["bbox_mm"][0] <= box[0] + TOL_MM and s["bbox_mm"][1] <= box[1] + TOL_MM
                                         and s["bbox_mm"][2] >= box[2] - TOL_MM and s["bbox_mm"][3] >= box[3] - TOL_MM)] or shapes
        bb = [min(s["bbox_mm"][i] for s in rad) if i < 2 else max(s["bbox_mm"][i] for s in rad) for i in range(4)]
        margins = {"x_low": bb[0] - box[0], "x_high": box[2] - bb[2], "y_low": bb[1] - box[1], "y_high": box[3] - bb[3]}
        # shortcut: vertical margin is the whole stack above the highest conductor; ignores conductors on the lid side
        if bnd["top"] in OPEN:
            margins["above"] = info["z_top_mm"] - max(s["z_mm"] or 0 for s in rad)
        sev = "error" if info["simulator"] == "Analyst" and (info.get("radiating") or bnd["top"] in OPEN or any(v in OPEN for v in sides.values())) else "warning"
        tight = {k: round(v, 2) for k, v in margins.items() if v < lam4 and (k == "above" or info["simulator"] == "Analyst")}
        if tight:
            add(sev, "air_margin", f"Air margin below lambda/4 = {lam4:.1f} mm at {min(freqs) / 1e9:g} GHz: {tight}")
    return out
