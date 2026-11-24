"""EM checks of saved AWR outputs (_out/em_*.txt, built from circuits/em_*.json by gen_em.py + mcp_call.py --batch).
Run: uv run --with numpy tests/validate_em.py   -> PASS/FAIL per check."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rf_theory as rf  # noqa: E402

W50, H, ER = 3.062e-3, 1.6e-3, 4.4


def load(name):
    """{'L1:DB(|S(1,1)|)': (f, y)} for every graph_data trace in _out/<name>.txt."""
    t = (HERE / "_out" / f"{name}.txt").read_text()
    t = t[t.index("--- graph_data"):]
    dec, i, out = json.JSONDecoder(), 0, {}
    while (i := t.find("{", i)) >= 0:
        try:
            o, j = dec.raw_decode(t, i)
        except ValueError:
            i += 1
            continue
        i = j
        if isinstance(o, dict) and "measurement" in o and "x" in o:
            out[o["measurement"]] = (np.array(o["x"]), np.array(o["y"]))
    return out


def rec(test, check, exp, got, ok):
    print(f"{'PASS' if ok else 'FAIL'}  {test:<7} {check:<34} exp {exp:<22} got {got}")


def pair_eeff(a, b, na, nb):
    f, p1 = a[f"{na}:Ang(S(2,1))"]
    p2 = b[f"{nb}:Ang(S(2,1))"][1]
    for k in (np.argmin(abs(f - x)) for x in (1e9, 2e9, 3e9)):
        g = rf.ms_eeff_kj(W50, H, ER, f[k])
        e = rf.ms_eeff_from_phase(np.degrees(p2[k] - p1[k]), 20.53e-3, f[k], g)
        err = 100 * (e / g - 1)
        rec("T1a", f"two-line eeff @ {f[k] / 1e9:.0f} GHz", f"{g:.4f} +/-2%", f"{e:.4f} ({err:+.2f}%)", abs(err) <= 2)


def notch(name, ref_f, tol, label):
    d = load(name)
    f, db = next(v for k, v in d.items() if "S(2,1)" in k)
    f0, _ = rf.find_extremum(f, 10 ** (db / 10), "min")
    err = 100 * (f0 - ref_f) / ref_f
    rec("T3", label, f"{ref_f / 1e9:.4f} GHz +/-{tol}%", f"{f0 / 1e9:.4f} GHz ({err:+.2f}%)", abs(err) <= tol)
    return f0


def main():
    a, b = load("em_ms_L1"), load("em_ms_L2")
    pair_eeff(a, b, "L1", "L2")
    f, p = a["L1:Ang(S(2,1))"]
    k = int(np.argmin(abs(f - 2e9)))
    ref = rf.ms_s21_phase_deg(W50, H, ER, 20.53e-3, 2e9)
    rec("T1b", "single-line ANG(S21) @ 2 GHz", f"{ref:.2f} deg +/-1", f"{np.degrees(p[k]):.2f} deg", abs(np.degrees(p[k]) - ref) <= 1)
    pair_eeff(load("em_ms_diag"), load("em_ms_diag"), "L1n", "L2n")  # de-embedding off
    z = load("em_ms_Z50")
    s11 = 10 ** (z["Z50:DB(|S(1,1)|)"][1] / 20) * np.exp(1j * z["Z50:Ang(S(1,1))"][1])
    s21 = 10 ** (z["Z50:DB(|S(2,1)|)"][1] / 20) * np.exp(1j * z["Z50:Ang(S(2,1))"][1])
    z0 = 50 * np.sqrt(((1 + s11) ** 2 - s21 ** 2) / ((1 - s11) ** 2 - s21 ** 2))
    worst = np.abs(z0 - 50).max() / 50 * 100
    rec("T2", "max S11 over 1-3 GHz", "< -25 dB", f"{z['Z50:DB(|S(1,1)|)'][1].max():.1f} dB", z["Z50:DB(|S(1,1)|)"][1].max() < -25)
    rec("T2", "Z0 from S11+S21 (ABCD)", "50 Ohm +/-2%", f"{abs(z0).min():.2f}-{abs(z0).max():.2f} Ohm", worst <= 2)
    fa = rf.stub_open_notch_f(19.79e-3, W50, H, ER)
    fb = rf.stub_open_notch_f(20.53e-3, W50, H, ER)
    # The theory has the open end but no T-junction model, so absolute notches carry a constant junction offset
    # (+2.7% in AXIEM). The ratio of two stub lengths cancels it and tests the end effect and line physics exactly.
    na = notch("em_stub_a", 2.0e9, 3, "(a) 19.79 mm notch vs 2.00 GHz (no T model)")
    nb = notch("em_stub_b", fb, 3, f"(b) 20.53 mm notch vs ref {fb / 1e9:.3f} GHz (no T model)")
    rec("T3", "(b) lower than (a)", "fb < fa", f"{nb / 1e9:.4f} < {na / 1e9:.4f}", nb < na)
    r_sim, r_ref = nb / na, fb / fa
    rec("T3", "notch ratio (b)/(a), junction-free", f"{r_ref:.4f} +/-0.5%", f"{r_sim:.4f} ({100 * (r_sim / r_ref - 1):+.2f}%)", abs(r_sim / r_ref - 1) <= 0.005)
    rec("T3", "T-junction offset vs theory (a)", "informational", f"{(na - fa) / 1e6:+.1f} MHz", True)
    q = load("em_qwt")  # port 2 set to 100 Ohm, but AXIEM S-parameters stay 50 Ohm referenced (no null): record, then renormalise via Z
    # Known AWR v17 limit, not a tool bug: record it without failing the suite
    rec("T4", "port-2 Z=100 in S11 (AXIEM ignores it)", "informational", f"min {q['QWT:DB(|S(1,1)|)'][1].min():.1f} dB", True)
    z = load("em_qwt_z")
    g = lambda a, b: z[f"QWT3:Re(Z({a},{b}))"][1] + 1j * z[f"QWT3:Im(Z({a},{b}))"][1]
    zin = g(1, 1) - g(1, 2) ** 2 / (g(2, 2) + 100)  # port 2 terminated in 100 Ohm
    f = z["QWT3:Re(Z(1,1))"][0]
    s11 = abs((zin - 50) / (zin + 50)) ** 2
    f0, _ = rf.find_extremum(f, s11, "min")
    rec("T4", "S11 null vs 2 GHz (Z-renormalised)", "2.000 GHz +/-2%", f"{f0 / 1e9:.4f} GHz ({100 * (f0 - 2e9) / 2e9:+.2f}%), min {10 * np.log10(s11.min()):.1f} dB", abs(f0 - 2e9) <= 0.04e9)
    pt = load("em_patch")
    f, re_z = next(v for k, v in pt.items() if "Re(Z" in k)
    f0, r0 = rf.find_extremum(f, re_z, "max")
    rec("T5", "Re(Z11) peak vs 2.40 GHz", "2.40 GHz +/-4%", f"{f0 / 1e9:.4f} GHz ({100 * (f0 - 2.4e9) / 2.4e9:+.2f}%)", abs(f0 - 2.4e9) <= 0.096e9)
    rec("T5", "edge R at peak (theory ~160)", "informational", f"{r0:.0f} Ohm", True)
    # T6: Analyst (3D FEM) closed box, wave ports on the boundary, lines span the box (L1 20.53 mm, L2 41.06 mm)
    a, b = load("em_anl_L1"), load("em_anl_L2")
    s11 = max(v[1].max() for d, n in ((a, "ANL1"), (b, "ANL2")) for v in [d[f"{n}:DB(|S(1,1)|)"]])
    rec("T6", "Analyst max S11, 1-3 GHz, both lines", "< -20 dB", f"{s11:.1f} dB", s11 < -20)
    f, p = a["ANL1:Ang(S(2,1))"]
    k = int(np.argmin(abs(f - 2e9)))
    ref = rf.ms_s21_phase_deg(W50, H, ER, 20.53e-3, f[k])
    rec("T6", "Analyst single-line ANG(S21) @ 2 GHz", f"{ref:.2f} deg +/-3", f"{np.degrees(p[k]):.2f} deg", abs(np.degrees(p[k]) - ref) <= 3)
    g = rf.ms_eeff_kj(W50, H, ER, f[k])
    e = rf.ms_eeff_from_phase(np.degrees(b["ANL2:Ang(S(2,1))"][1][k] - p[k]), 20.53e-3, f[k], g)
    rec("T6", "Analyst two-line eeff @ 2 GHz", f"{g:.4f} +/-2%", f"{e:.4f} ({100 * (e / g - 1):+.2f}%)", abs(e / g - 1) <= 0.02)


if __name__ == "__main__":
    main()
