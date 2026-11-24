"""Writes the EM validation build batches tests/circuits/em_*.json (run: python tests/gen_em.py)."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "circuits"
H, ER, W50 = 1.6, 4.4, 3.062
PEC = "2:Perfect Conductor"


def stack(em, x, y, air=30, sim="AXIEM", grid=0.5, er=ER, top="approx_open"):
    return [
        {"tool": "create_em_structure", "args": {"name": em, "simulator": sim}},
        {"tool": "set_em_stackup", "args": {"em": em,
            "dielectrics": [{"thickness_mm": air, "er": 1.0, "tand": 0}, {"thickness_mm": H, "er": er, "tand": 0}],
            "conductors": [{"name": "MS_PEC", "sigma": "perfect", "thickness_mm": 0}],
            "enclosure": {"x_mm": x, "y_mm": y, "grid_mm": grid},
            "boundaries": {"top": top, "bottom": "perfect_conductor", "sides": "perfect_conductor"}}}]


def rect(em, x, y, w, h):
    return {"tool": "add_em_shape", "args": {"em": em, "kind": "rect", "layer": PEC, "x": x, "y": y, "w": w, "h": h}}


def poly(em, pts):
    return {"tool": "add_em_shape", "args": {"em": em, "kind": "polygon", "layer": PEC, "points": pts}}


def port(em, n, edge, shape=1, z=50, deembed=None):
    a = {"em": em, "type": "edge", "at": {"layer": PEC, "n": shape, "edge": edge}, "number": n}
    if z != 50:
        a["impedance"] = z
    if deembed is not None:
        a["deembed"] = deembed
    return {"tool": "add_em_port", "args": a}


def run(em, f0, f1, n, meas, g=None, maxp=60):
    g = g or em + "_G"
    return ([{"tool": "set_frequencies", "args": {"start_hz": f0, "stop_hz": f1, "points": n, "document": em}},
             {"tool": "check_em_setup", "args": {"em": em}}, {"tool": "create_graph", "args": {"name": g}}] +
            [{"tool": "add_measurement", "args": {"graph": g, "source_doc": em, "measurement": m}} for m in meas] +
            [{"tool": "clear_status_messages"}, {"tool": "simulate", "args": {"graph": g}},
             {"tool": "graph_data", "args": {"graph": g, "max_points": maxp}},
             {"tool": "em_ports", "args": {"em_structure": em}},
             {"tool": "em_simulation_log", "args": {"em_structure": em, "tail_chars": 400}}])


S = ["DB(|S(1,1)|)", "DB(|S(2,1)|)", "Ang(S(2,1))"]


def line(em, L, deembed=None, grid=0.5, air=30, X=60, Y=40, er=ER, top="approx_open", w=W50, fmax=3e9, npts=11):
    x0, y0 = (X - L) / 2, Y / 2 - w / 2
    return (stack(em, X, Y, air=air, grid=grid, er=er, top=top) + [rect(em, x0, y0, L, w), port(em, 1, "left", deembed=deembed), port(em, 2, "right", deembed=deembed)]
            + run(em, 1e9, fmax, npts, S))


def stub(em, ls, X=60, Y=56, y0=16, L=30):
    """50 Ohm through line with a shunt open stub of length ls (mm, from the line edge) at its middle, one T polygon."""
    x0, x1, xc, w = (X - L) / 2, (X + L) / 2, X / 2, W50
    pts = [[x0, y0], [x1, y0], [x1, y0 + w], [xc + w / 2, y0 + w], [xc + w / 2, y0 + w + ls], [xc - w / 2, y0 + w + ls],
           [xc - w / 2, y0 + w], [x0, y0 + w]]
    return (stack(em, X, Y) + [poly(em, pts), port(em, 1, "left"), port(em, 2, "right")]
            + run(em, 1.6e9, 2.4e9, 17, ["DB(|S(1,1)|)", "DB(|S(2,1)|)"]))


def qwt(em, w70=1.61507, l70=20.957, lf=10, X=60, Y=40, de2=None, meas=("DB(|S(1,1)|)", "DB(|S(2,1)|)")):
    yc, x0 = Y / 2, (X - lf - l70) / 2
    xj, xe = x0 + lf, x0 + lf + l70
    pts = [[x0, yc - W50 / 2], [xj, yc - W50 / 2], [xj, yc - w70 / 2], [xe, yc - w70 / 2], [xe, yc + w70 / 2], [xj, yc + w70 / 2],
           [xj, yc + W50 / 2], [x0, yc + W50 / 2]]
    return (stack(em, X, Y) + [poly(em, pts), port(em, 1, "left"), port(em, 2, "right", z=100, deembed=de2)]
            + run(em, 1.6e9, 2.4e9, 17, list(meas)))


def patch(em, W=38.01, Lp=29.42, lf=2, X=64, Y=70):
    x0 = 16.0
    xp = x0 + lf
    yc = Y / 2
    pts = [[x0, yc - W50 / 2], [xp, yc - W50 / 2], [xp, yc - W / 2], [xp + Lp, yc - W / 2], [xp + Lp, yc + W / 2], [xp, yc + W / 2],
           [xp, yc + W50 / 2], [x0, yc + W50 / 2]]
    return (stack(em, X, Y) + [poly(em, pts), port(em, 1, "left")]
            + run(em, 2.1e9, 2.7e9, 13, ["Re(Z(1,1))", "Im(Z(1,1))", "DB(|S(1,1)|)"]))


def anl(em, L, air=15, Y=30, fs=(1e9, 3e9, 5)):
    """Analyst: closed box (PEC lid, floor and sides), the 50 Ohm line spans the whole box in x, wave ports on the two x edges."""
    st = stack(em, L, Y, air=air, sim="Analyst", top="perfect_conductor")
    st[1]["args"]["conductors"] = [{"name": "TR", "sigma": "perfect", "em_layer": 2}]
    tr = {"tool": "add_em_shape", "args": {"em": em, "kind": "rect", "layer": "TR", "x": 0, "y": Y / 2 - W50 / 2, "w": L, "h": W50}}
    pt = lambda n, e: {"tool": "add_em_port", "args": {"em": em, "type": "wave", "at": {"layer": "TR", "edge": e}, "number": n, "deembed": False}}
    opt = {"tool": "set_em_option", "args": {"em": em, "name": "Em3DP_AMR_Tolerance", "value": 0.005}}  # default 0.02 leaves the 41 mm line 6% off in eeff
    return st + [opt, tr, pt(1, "left"), pt(2, "right")] + run(em, fs[0], fs[1], fs[2], S + ["Ang(S(1,1))"])


def save(name, steps):
    (OUT / f"em_{name}.json").write_text(json.dumps(steps, indent=1))


if __name__ == "__main__":
    save("ms_L1", line("L1", 20.53))
    save("ms_L2", line("L2", 41.06))
    save("ms_diag2", line("A1", 20.53, er=1.0) + line("A2", 41.06, er=1.0)
         + line("F1", 20.53, grid=0.15, X=50, Y=30) + line("F2", 41.06, grid=0.15, X=60, Y=30))
    save("ms_diag3", line("T1", 20.53, top="perfect_conductor") + line("T2", 41.06, top="perfect_conductor")
         + line("M1", 20.53, air=10) + line("M2", 41.06, air=10))
    save("ms_diag4", line("W1", 20.53, er=1.0, w=7.859) + line("W2", 41.06, er=1.0, w=7.859))
    save("ms_diag5", line("G1", 20.53, fmax=6e9, npts=6) + line("G2", 41.06, fmax=6e9, npts=6)
         + line("V1", 20.53, er=1.0, w=7.859, fmax=6e9, npts=6) + line("V2", 41.06, er=1.0, w=7.859, fmax=6e9, npts=6))
    save("ms_Z50", stack("Z50", 60, 40) + [rect("Z50", 19.735, 18.469, 20.53, W50), port("Z50", 1, "left"), port("Z50", 2, "right")]
         + run("Z50", 1e9, 3e9, 11, S + ["Ang(S(1,1))"]))
    save("stub_a", stub("STA", 19.79))
    save("stub_b", stub("STB", 20.53))
    save("qwt", qwt("QWT"))
    save("qwt_z", qwt("QWT3", meas=[f"{p}(Z({a},{b}))" for p in ("Re", "Im") for a, b in ((1, 1), (1, 2), (2, 2))]))
    save("patch", patch("PAT"))
    save("anl_L1", anl("ANL1", 20.53))
    save("anl_L2", anl("ANL2", 41.06))
    save("ms_diag6", line("B1", 20.53, er=1.0, w=7.859, Y=100) + line("B2", 41.06, er=1.0, w=7.859, Y=100)
         + line("C1", 20.53, er=1.0, w=7.859, air=3.2, top="perfect_conductor") + line("C2", 41.06, er=1.0, w=7.859, air=3.2, top="perfect_conductor"))
    # diagnosis variants: de-embedding off, finer cell, thinner air
    save("ms_diag", line("L1n", 20.53, deembed=False) [:-0 or None] + line("L2n", 41.06, deembed=False)[0:] )
