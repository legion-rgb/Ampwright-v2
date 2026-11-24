"""Assert checks for optimize.py logic. No AWR needed: python tests/test_optimize.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import optimize as o

rows = [{"measurement": "v2_a:DB(|S(2,1)|)", "x": [1e6, 1e7, 1e8], "y": [-3.5, -6.5, -23.5]}]
assert o._y_at(rows, "DB(|S(2,1)|)", 1e7) == -6.5
assert abs(o._y_at(rows, "v2_a:DB(|S(2,1)|)", 5.5e6) - -5.0) < 1e-12
for bad in ("DB(|S(1,1)|)", None):
    try:
        o._y_at(rows, bad, 1e7) if bad else o._y_at(rows, "DB(|S(2,1)|)", 1e9)
        raise AssertionError("accepted")
    except ValueError:
        pass


class Opt:  # stands in for awr().Project.Optimizer
    TypeCount, Type = 2, 1

    def TypeName(self, i):
        return ["Simplex Optimizer", "Random"][i - 1]


class Proj:
    Optimizer = Opt()


o.awr = lambda: type("A", (), {"Project": Proj()})()
o._goals = lambda: [{"name": "g", "schematic": "v2_a", "enabled": True}, {"name": "h", "schematic": "Schematic 1", "enabled": False}]
o._opt_params = lambda only=None: [("v2_b", "C1", "C", None)] if only in (None, "v2_b") else []
try:  # a flagged parameter in another document must block the run
    o.run_optimizer_sync("v2_a")
    raise AssertionError("ran with a foreign optimize flag")
except ValueError as e:
    assert "v2_b.C1.C" in str(e) and "Schematic 1" not in str(e), e  # disabled goals don't count
print("OK")
