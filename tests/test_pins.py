"""Assert checks for the pure logic in helpers.py. No AWR needed: python Ampwright/tests/test_pins.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import helpers as h

# pins
assert h.parse_pin("R1:2") == ("R1", 2)
assert h.parse_pin("GND#2:1") == ("GND#2", 1)
for bad in ("R1", "R1:", ":2", "R1:x", "R1:0"):
    try:
        h.parse_pin(bad)
        raise AssertionError(f"accepted {bad!r}")
    except ValueError:
        pass

# placement: empty sheet -> origin; a RES at the origin pushes the next part one cell right
assert h.free_spot([]) == (0, 0)
res_box = (0, -470, 1001, 121)
assert h.free_spot([res_box]) == (h.CELL, 0)
# near a part: closest free cell, ties to the right
assert h.free_spot([res_box], near=(0, 0)) == (h.CELL, 0)
assert h.free_spot([res_box, (h.CELL, -470, h.CELL + 1001, 121)], near=(h.CELL, 0)) == (2 * h.CELL, 0)
# a full first row wraps to the next row
row = [(c * h.CELL, -470, c * h.CELL + 1001, 121) for c in range(8)]
assert h.free_spot(row) == (0, h.CELL)

# sides and symbol rotation (body direction at rotation 0: PORT left, GND down)
assert h.pin_side((0, 0), (500, -175)) == "left"
assert h.pin_side((1000, 0), (500, -175)) == "right"
assert h.pin_side((3000, 1000), (2900, 500)) == "down"
assert h.pin_side((3000, 0), (2900, 500)) == "up"
assert [h.rotation("left", s) for s in ("left", "right", "up", "down")] == [0, 180, 270, 90]
assert [h.rotation("down", s) for s in ("down", "right", "up", "left")] == [0, 90, 180, 270]
assert h.offset((1000, 0), "right", 1000) == (2000, 0)
assert h.offset((0, 0), "up", 500) == (0, -500)

# wire routes
assert h.route((0, 0), (1000, 0)) == [(0, 0, 1000, 0)]
assert h.route((0, 0), (1000, 2000)) == [(0, 0, 1000, 0), (1000, 0, 1000, 2000)]
# a pin on the horizontal-first L forces vertical-first; blocked both ways -> None; endpoints never block
assert h.route((0, 0), (3000, -1000), [(1000, 0)]) == [(0, 0, 0, -1000), (0, -1000, 3000, -1000)]
assert h.route((0, 0), (3000, -1000), [(1000, 0), (0, -500)]) is None
assert h.route((0, 0), (3000, 0), [(1500, 0)]) is None
assert h.route((0, 0), (3000, 0), [(0, 0), (3000, 0), (1500, 100)]) == [(0, 0, 3000, 0)]
# a corner landing mid-way on an existing wire would join it: take the other L, or refuse
mid = [(1000, -2000, 1000, 2000)]
assert h.route((0, 0), (1000, 1000), [(0, 0), (1000, 1000)], mid) == [(0, 0, 0, 1000), (0, 1000, 1000, 1000)]
assert h.route((0, 0), (1000, 1000), [(0, 0), (1000, 1000)], mid + [(-500, 1000, 500, 1000)]) is None

# frequency lists
f = h.freq_list(1e4, 1e7, points=4, log=True)
assert len(f) == 4 and abs(f[1] - 1e5) < 1e-6 and abs(f[-1] - 1e7) < 1e-3
assert h.freq_list(1e9, 2e9, step=0.25e9) == [1e9, 1.25e9, 1.5e9, 1.75e9, 2e9]
assert h.freq_list(1e9, 2e9, points=3) == [1e9, 1.5e9, 2e9]
# tidy_freqs: 2 decimals in the span's own unit; a finer unit only when rounding would move something
f = h.freq_list(50e3, 500e3, step=25e3)  # 200 kHz asked for: 50..500 kHz step 25 kHz stays kHz
assert len(f) == 19 and h.tidy_freqs(f, True)[1:3] == ("kHz", 1e3) and h.tidy_freqs(f, True)[0] == f
assert h.tidy_freqs(h.freq_list(1.99e9, 2.01e9, step=1e6), True)[1] == "MHz"  # GHz would move 1.991
assert h.tidy_freqs(h.freq_list(1.5915e9, 3e9, points=5), False)[1] == "MHz"  # GHz would move the start
g, unit, *_ = h.tidy_freqs(h.freq_list(1e4, 1e7, points=5, log=True), False)
assert unit == "MHz" and g[0] == 1e4 and g[-1] == 1e7 and g[1] == 60000.0, (g, unit)
assert h.tidy_freqs([1000.0, 1000.004], False)[1] == "Hz"
for kw in ({}, {"points": 3, "step": 1.0}, {"step": 1.0, "log": True}):
    try:
        h.freq_list(1e9, 2e9, **kw)
        raise AssertionError(f"accepted {kw}")
    except ValueError:
        pass

# trace summary
s = h.summarize([1, 2, 3, 4, 5], [0, -3, -10, -4, -1])
assert s["min"] == -10 and s["x_at_min"] == 3 and s["max"] == 0 and s["x_at_max"] == 1
assert s["samples"] == [[1, 0], [2, -3], [3, -10], [4, -4], [5, -1]]
assert h.summarize([], []) == {"points": 0}

print("test_pins: all passed")
