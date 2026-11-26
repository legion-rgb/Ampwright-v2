"""Check, no AWR needed: the tidy axis maths. Run: uv run --with matplotlib --with pywin32 --with "mcp>=1.2,<2" python tests/test_graph_tidy.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from graphs import nice_axis  # noqa: E402

for lo, hi, want in [(-16.86, -0.04, (-18, 0, 3)), (0.1, 10, (0, 10, 2)), (-80, 0.3, (-80, 5, 5)), (2.4e0, 2.45, (2.4, 2.46, 0.01)),
                     (7, 7, (6.3, 7.7, 0.2)), (0, 1, (0, 1, 0.2)), (-0.0, 130, (0, 140, 20))]:
    got = nice_axis(lo, hi)
    print(lo, hi, "->", got)
    a, b, s = got
    assert a <= lo and b >= hi and 4 <= round((b - a) / s) <= 10 and s > 0, (lo, hi, got)
    mant = s / 10 ** __import__("math").floor(__import__("math").log10(s))
    assert min(abs(mant - m) for m in (1, 2, 5, 10)) < 1e-6, ("step not 1/2/5", got)
print("OK")
