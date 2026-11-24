import json, sys
sys.path.insert(0, "tests")
import numpy as np, rf_theory as r
exec(open("tests/_out/gen5.py").read().split("Z=70")[0])  # reuse mk/E/C/P/G
H, ER = 1.6e-3, 4.4
W50 = round(3.062e-3, 6)
W70 = r.ms_synthesis(50 * 2 ** 0.5 * 1.0 * 1.0 / 1.0 * 0 + 70.71067811865476, H, ER)
EE70 = r.ms_analysis(W70, H, ER)[1]
L70 = r.C0 / (2e9 * np.sqrt(EE70)) / 4
print("W70 mm", W70 * 1e3, "L70 mm", L70 * 1e3, "ee", EE70)
def sub(s): return E(s, "MSUB", None, {"Er": ER, "H": H, "T": 0, "Rho": 0, "Tand": 0, "Name": "MSUB"})
s = "V_MS_50"
a = mk(s, [sub(s), E(s, "MLIN", "M1", {"W": W50, "L": 20.53e-3, "MSUB": "MSUB"}, near="MSUB"), P(s, "M1:1", 1), P(s, "M1:2", 2)], 0.5e9, 4e9, 351)
s = "V_MS_QWT"
b = mk(s, [sub(s), E(s, "MLIN", "M1", {"W": round(W70, 7), "L": round(L70, 7), "MSUB": "MSUB"}, near="MSUB"), P(s, "M1:1", 1, 50), P(s, "M1:2", 2, 100)], 1e9, 3e9, 801)
json.dump(a, open("tests/circuits/ms_50.json", "w"), indent=1)
json.dump(b, open("tests/circuits/ms_qwt.json", "w"), indent=1)
