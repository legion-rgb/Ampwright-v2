"""Unit asserts for the EM pre-flight lint and edge helper (no AWR needed): python tests/test_em.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import helpers as h


def base(**kw):
    info = {"simulator": "Analyst", "enclosure": {"x_mm": 10, "y_mm": 10}, "z_top_mm": 2.0,
            "boundaries": {"top": "perfect_conductor", "bottom": "perfect_conductor"}, "frequencies_hz": [1e9],
            "boundary": {"bbox_mm": [0, 0, 10, 10], "n_edges": 4, "edges": {k: "perfect_conductor" for k in ("left", "right", "top", "bottom")}}, "shapes": [{"em_layer": 2, "z_mm": 1.0, "bbox_mm": [2, 2, 8, 8]}],
            "ports": [{"number": 1, "kind": "lumped_down", "em_layer": 2, "segment_mm": [(2, 2), (2, 8)], "associated": True}]}
    info.update(kw)
    return info


def rules(info):
    return {r["rule"] for r in h.lint_em(info)}


assert rules(base()) == set()
assert rules(base(ports=[])) == {"no_ports"}
p = base()["ports"][0]
assert "port_numbering" in rules(base(ports=[{**p, "number": 2}]))
assert "diff_missing_negative" in rules(base(ports=[{**p, "kind": "lumped_diff"}]))
assert "diff_missing_negative" not in rules(base(ports=[{**p, "kind": "lumped_diff"}, {**p, "kind": "lumped_diff", "number": -1}]))
assert "wave_port_off_edge" in rules(base(ports=[{**p, "kind": "wave", "segment_mm": [(2, 2), (2, 8)]}]))
assert "wave_port_off_edge" not in rules(base(ports=[{**p, "kind": "wave", "segment_mm": [(0, 2), (0, 8)]}]))
assert "wave_custom_outside" in rules(base(ports=[{**p, "kind": "wave_custom", "segment_mm": [(2, 2), (2, 12)]}]))
assert "port_not_on_shape" in rules(base(ports=[{**p, "segment_mm": [(9, 9), (9, 9.5)]}]))
assert "lumped_down_no_ground" in rules(base(boundaries={"top": "approx_open", "bottom": "approx_open"}, ports=[p]))
assert "air_margin" in rules(base(boundaries={"top": "approx_open", "bottom": "perfect_conductor"}))  # lambda/4 = 75 mm at 1 GHz
assert {r["severity"] for r in h.lint_em(base(simulator="AXIEM", boundaries={"top": "approx_open", "bottom": "perfect_conductor"}))} == {"warning"}
assert "boundary_not_rectangular" in rules(base(boundary={"n_edges": 8, "bbox_mm": [0, 0, 10, 10], "edges": {}}))
assert "no_boundary" in rules(base(boundary=None))
# air margin: error only for Analyst with an open top, an open side or radiating=True; a bottom-only open is a warning; closed boxes are silent
sev = lambda **kw: {r["severity"] for r in h.lint_em(base(**kw)) if r["rule"] == "air_margin"}
assert sev() == set()
assert sev(boundaries={"top": "perfect_conductor", "bottom": "approx_open"}) == {"warning"}
assert sev(radiating=True) == {"error"}
assert sev(boundaries={"top": "approx_open", "bottom": "perfect_conductor"}) == {"error"}
assert sev(boundary={"bbox_mm": [0, 0, 10, 10], "n_edges": 4, "edges": {"left": "approx_open", "right": "perfect_conductor"}}) == {"error"}
assert h.edge_segment([(0, 0), (4, 0), (4, 2), (0, 2)], "left") == ((0, 0), (0, 2))
assert h.edge_segment([(0, 0), (4, 0), (4, 2), (0, 2)], "top") == ((0, 2), (4, 2))
try:
    h.edge_segment([(0, 0), (4, 0), (2, 2)], "top")
    raise SystemExit("expected ValueError")
except ValueError:
    pass
print("test_em ok")
