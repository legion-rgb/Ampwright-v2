"""Assert check for schematic._set_param value typing. No AWR needed: python tests/test_params.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import schematic as s


class P:  # stands in for an AWR parameter; records which setter ran
    def __setattr__(self, k, v):
        object.__setattr__(self, "set", (k, v))


def setp(name, value):
    p = P()
    s.find = lambda coll, n: p
    s._set_param(type("E", (), {"Parameters": None})(), name, value)
    return p.set


assert setp("C", 4.775e-9) == ("ValueAsDouble", 4.775e-9)
assert setp("C", "4.775e-9") == ("ValueAsDouble", 4.775e-9)  # numeric text is SI now
assert setp("C", "477.5") == ("ValueAsDouble", 477.5)
assert setp("C", "4.775*100") == ("ValueAsString", "4.775*100")  # expression stays display units
assert setp("C", "Cval") == ("ValueAsString", "Cval")
assert setp("ID", "1") == ("ValueAsString", "1")
print("OK")
