"""Check saved AWR outputs (tests/_out/<name>.txt, from `mcp_call.py --batch circuits/<name>.json > _out/<name>.txt`) against rf_theory.
Run: uv run --with numpy tests/validate.py   -> PASS/FAIL per check."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rf_theory as rf  # noqa: E402

RESULTS = []


def load(name):
    """{'S21': (f, dB), 'S11': (f, dB), 'ANG21': (f, rad), ...} from the graph_data section of _out/<name>.txt."""
    t = (HERE / "_out" / f"{name}.txt").read_text()
    t = t[t.rindex("--- graph_data"):].split("\n", 1)[1]
    dec, i, out = json.JSONDecoder(), 0, {}
    while (i := t.find("{", i)) >= 0:
        d, i = dec.raw_decode(t, i)
        if "measurement" not in d:
            continue
        m = d["measurement"].split(":", 1)[1]
        key = ("S21" if "S(2,1)" in m else "S11" if "S(1,1)" in m else m)
        key = "ANG21" if m.startswith("Ang") else key
        out[key] = (np.array(d["x"]), np.array(d["y"]))
    return out


def rec(circuit, check, expected, measured, ok):
    RESULTS.append((circuit, check, expected, measured, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {circuit:<14} {check:<40} exp {expected:<22} got {measured}")


def curve(circuit, check, f, sim_db, ref_db, tol, floor=-60.0):
    e = np.abs(np.maximum(sim_db, floor) - np.maximum(ref_db, floor))
    rec(circuit, check, f"max err <= {tol} dB", f"max {e.max():.4f} dB @ {f[e.argmax()] / 1e9:.4g} GHz", e.max() <= tol)


def phase(circuit, f, sim_rad, ref_s21, tol_deg=0.5, floor_db=-40):
    m = rf.db(ref_s21) > floor_db
    e = np.degrees(np.abs(np.angle(np.exp(1j * (sim_rad - np.angle(ref_s21))))))[m]
    rec(circuit, "ANG(S21) vs ref (rad->deg)", f"max err <= {tol_deg} deg", f"max {e.max():.4f} deg", e.max() <= tol_deg)


def crossing(f, y, level, which=0):
    """Frequency where y crosses level, interpolated in log f (smooth for log sweeps)."""
    s = y - level
    i = np.nonzero(np.sign(s[:-1]) != np.sign(s[1:]))[0]
    if len(i) <= which:
        return float("nan")
    k = i[which]
    lf = np.log(f[k]) - s[k] * (np.log(f[k + 1]) - np.log(f[k])) / (s[k + 1] - s[k])
    return float(np.exp(lf))


def freqcheck(circuit, check, sim, ref, tol_pct):
    err = 100 * abs(sim - ref) / ref
    rec(circuit, check, f"{ref / 1e6:.5g} MHz +/-{tol_pct}%", f"{sim / 1e6:.5g} MHz ({err:.3f}%)", err <= tol_pct)


def has(name):
    ok = (HERE / "_out" / f"{name}.txt").exists()
    if not ok:
        print(f"SKIP  {name}: no _out/{name}.txt")
    return ok


def v_rc():
    if not has("rc"):
        return
    d = load("rc")
    f, s21 = d["S21"]
    _, s11 = d["S11"]
    _, r11, r21 = rf.rc_lowpass(f)
    curve("RC", "S21 whole curve", f, s21, rf.db(r21), 0.05)
    curve("RC", "S11 whole curve", f, s11, rf.db(r11), 0.05)
    freqcheck("RC", "-3.0103 dB corner vs DC", crossing(f, s21 - s21[0], rf.HALF_POWER_DB), 3.335e6, 1.0)


def v_rl():
    if has("rl_lpf"):
        d = load("rl_lpf")
        f, s21 = d["S21"]
        _, r11, r21 = rf.rl_lowpass(f)
        curve("RL_LPF", "S21 whole curve", f, s21, rf.db(r21), 0.05)
        curve("RL_LPF", "S11 whole curve", f, d["S11"][1], rf.db(r11), 0.05)
        freqcheck("RL_LPF", "-3.0103 dB corner vs DC", crossing(f, s21 - s21[0], rf.HALF_POWER_DB), 119.37e6, 1.0)
        rec("RL_LPF", "DC S21 (1 MHz)", "-3.52 dB +/-0.02", f"{s21[0]:.4f} dB", abs(s21[0] + 3.52) <= 0.02)
        phase("RL_LPF", f, d["ANG21"][1], r21)
    if has("rl_hpf"):
        d = load("rl_hpf")
        f, s21 = d["S21"]
        _, r11, r21 = rf.rl_highpass(f)
        curve("RL_HPF", "S21 whole curve", f, s21, rf.db(r21), 0.05)
        curve("RL_HPF", "S11 whole curve", f, d["S11"][1], rf.db(r11), 0.05)
        freqcheck("RL_HPF", "-3.0103 dB corner vs HF", crossing(f, s21 - s21[-1], rf.HALF_POWER_DB), 53.05e6, 1.0)
        phase("RL_HPF", f, d["ANG21"][1], r21)


def v_rlc():
    if has("rlc_series"):
        d = load("rlc_series")
        f, s21 = d["S21"]
        _, r11, r21 = rf.rlc_series_pass(f)
        r = rf.rlc_series_pass_ref()
        curve("RLC_SER", "S21 whole curve", f, s21, rf.db(r21), 0.05)
        curve("RLC_SER", "S11 whole curve", f, d["S11"][1], rf.db(r11), 0.05)
        f0, _ = rf.find_extremum(f, 10 ** (s21 / 10), "max")
        freqcheck("RLC_SER", "peak f0", f0, r["f0"], 0.5)
        c = rf.f_at_level(f, s21, s21.max() + rf.HALF_POWER_DB)
        freqcheck("RLC_SER", "-3 dB BW (as 'MHz')", c[1] - c[0], r["bw3db"], 2.0)
        phase("RLC_SER", f, d["ANG21"][1], r21)
    if has("rlc_shunt"):
        d = load("rlc_shunt")
        f, s21 = d["S21"]
        _, r11, r21 = rf.rlc_shunt_notch(f)
        r = rf.rlc_shunt_notch_ref()
        curve("RLC_SHUNT", "S21 whole curve", f, s21, rf.db(r21), 0.05, floor=-45)
        f0, p = rf.find_extremum(f, 10 ** (s21 / 10), "min")
        freqcheck("RLC_SHUNT", "notch f0", f0, r["f0"], 0.5)
        rec("RLC_SHUNT", "notch depth", f"{rf.db(r['s21_f0']):.2f} dB +/-0.3", f"{10 * np.log10(p):.3f} dB", abs(10 * np.log10(p) - rf.db(r["s21_f0"])) <= 0.3)
        phase("RLC_SHUNT", f, d["ANG21"][1], r21)


def near(f, y, f0, kind, span=0.05):
    """(f, y) of the extremum of linear power y within +/-span*f0 of f0, parabola-refined."""
    m = np.abs(f - f0) <= span * f0
    return rf.find_extremum(f[m], y[m], kind)


def v_tl():
    f0 = 2e9
    if has("tl_qwt"):
        d = load("tl_qwt")
        f, s11 = d["S11"]
        s21 = d["S21"][1]
        _, r11, r21 = rf.qwt(f, z_port2=100)
        curve("TL_QWT", "S11 vs qwt(z_port2=100), ref>-40", f, s11, rf.db(r11), 0.1, floor=-40)
        curve("TL_QWT", "S21 vs qwt(z_port2=100), ref>-40", f, s21, rf.db(r21), 0.1, floor=-40)
        for fn in (2e9, 6e9):
            fx, py = near(f, 10 ** (s11 / 10), fn, "min")
            i = np.abs(f - fn).argmin()
            rec("TL_QWT", f"S11 null near {fn / 1e9:g} GHz", f"{fn / 1e9:g} GHz +/-0.5%, < -40 dB",
                f"{fx / 1e9:.5g} GHz, {s11[i]:.1f} dB", abs(fx - fn) / fn <= 0.005 and s11[i] < -40)
        i = np.abs(f - 4e9).argmin()
        rec("TL_QWT", "|S11| at 4 GHz", "-9.54 dB +/-0.1", f"{s11[i]:.3f} dB", abs(s11[i] + 9.54) <= 0.1)
        c = rf.f_at_level(f, s11, -20.0)
        c = c[(c > 0.5 * f0) & (c < 1.5 * f0)]
        fbw = 100 * (c[-1] - c[0]) / f0
        ref = 100 * rf.qwt_ref()["fbw"]
        rec("TL_QWT", "-20 dB fractional BW", f"{ref:.2f} % +/-1% rel", f"{fbw:.3f} %", abs(fbw - ref) / ref <= 0.01)
        phase("TL_QWT", f, d["ANG21"][1], r21)
    if has("tl_open"):
        d = load("tl_open")
        f, s21 = d["S21"]
        _, r11, r21 = rf.stub_lambda4(f, "open")
        curve("TL_OPEN", "S21 vs stub_lambda4(open), ref>-40", f, s21, rf.db(r21), 0.1, floor=-40)
        curve("TL_OPEN", "S11 vs stub_lambda4(open), ref>-40", f, d["S11"][1], rf.db(r11), 0.1, floor=-40)
        for fn in (2e9, 6e9):
            fx, _ = near(f, 10 ** (s21 / 10), fn, "min")
            i = np.abs(f - fn).argmin()
            rec("TL_OPEN", f"S21 notch near {fn / 1e9:g} GHz", f"{fn / 1e9:g} GHz +/-0.5%, < -40 dB",
                f"{fx / 1e9:.5g} GHz, {s21[i]:.1f} dB", abs(fx - fn) / fn <= 0.005 and s21[i] < -40)
        phase("TL_OPEN", f, d["ANG21"][1], r21)
    if has("tl_short"):
        d = load("tl_short")
        f, s21 = d["S21"]
        _, r11, r21 = rf.stub_lambda4(f, "short")
        curve("TL_SHORT", "S21 vs stub_lambda4(short), ref>-40", f, s21, rf.db(r21), 0.1, floor=-40)
        i = np.abs(f - f0).argmin()
        rec("TL_SHORT", "|S21| at 2 GHz", "0 dB +/-0.05", f"{s21[i]:.4f} dB", abs(s21[i]) <= 0.05)
        phase("TL_SHORT", f, d["ANG21"][1], r21)
    if has("tl_half"):
        d = load("tl_half")
        f, s11 = d["S11"]
        s21 = d["S21"][1]
        _, r11, r21 = rf.tline(f, 100, 180, f0, deg=True)
        curve("TL_HALF", "S11 vs tline, ref>-40", f, s11, rf.db(r11), 0.1, floor=-40)
        curve("TL_HALF", "S21 vs tline", f, s21, rf.db(r21), 0.1, floor=-40)
        i = np.abs(f - f0).argmin()
        rec("TL_HALF", "S11 null at 2 GHz", "< -40 dB", f"{s11[i]:.1f} dB", s11[i] < -40)
        fx, py = near(f, 10 ** (s11 / 10), 1e9, "max")
        _, rm = rf.find_extremum(f[np.abs(f - 1e9) <= 5e7], rf.db(r11)[np.abs(f - 1e9) <= 5e7], "max")
        rec("TL_HALF", "|S11| max near 1 GHz", f"1 GHz, {rm:.2f} dB", f"{fx / 1e9:.5g} GHz, {10 * np.log10(py):.3f} dB",
            abs(fx - 1e9) / 1e9 <= 0.005 and abs(10 * np.log10(py) - rm) <= 0.1)
        ph = np.degrees(d["ANG21"][1][i])
        rec("TL_HALF", "ANG(S21) at 2 GHz", "+/-180 deg", f"{ph:.3f} deg", abs(abs(ph) - 180) <= 0.5)
        phase("TL_HALF", f, d["ANG21"][1], r21)


def v_ms():
    f0 = 2e9
    if has("ms_50"):
        d = load("ms_50")
        f, s11 = d["S11"]
        rec("MS_50", "S11 < -30 dB, 0.5-4 GHz", "< -30 dB", f"max {s11.max():.1f} dB @ {f[s11.argmax()] / 1e9:.3g} GHz", s11.max() < -30)
        i = np.abs(f - f0).argmin()
        ang = np.degrees(d["ANG21"][1][i])
        rec("MS_50", "ANG(S21) at 2 GHz", "-90 deg +/-3", f"{ang:.3f} deg", abs(ang + 90) <= 3)
        ee = (rf.C0 * np.radians(-ang) / (2 * np.pi * f0 * 20.53e-3)) ** 2
        w = 3.062e-3
        print(f"INFO  MS_50  eps_eff from phase {ee:.4f}  (static HJ {rf.ms_analysis(w, 1.6e-3, 4.4)[1]:.4f}, KJ@2GHz {rf.ms_eeff_kj(w, 1.6e-3, 4.4, f0):.4f})")
    if has("ms_qwt"):
        d = load("ms_qwt")
        f, s11 = d["S11"]
        fx, py = near(f, 10 ** (s11 / 10), f0, "min", span=0.25)
        err = 100 * (fx - f0) / f0
        rec("MS_QWT", "S11 null vs 2 GHz", "2 GHz +/-3%", f"{fx / 1e9:.5g} GHz ({err:+.2f}%), {10 * np.log10(max(py, 1e-30)):.1f} dB", abs(err) <= 3)


def load_traces(name):
    """All graph_data traces of _out/<name>.txt as {measurement: (x, y)} (IV families come as '<meas>#k')."""
    t = (HERE / "_out" / f"{name}.txt").read_text()
    t = t[t.rindex("--- graph_data"):].split(chr(10), 1)[1]
    dec, i, out = json.JSONDecoder(), 0, {}
    while (i := t.find("{", i)) >= 0:
        d, i = dec.raw_decode(t, i)
        if "measurement" in d:
            out[d["measurement"]] = (np.array(d["x"]), np.array(d["y"]))
    return out


def v_fet():
    if not has("fet_iv"):
        return
    steps = json.loads((HERE / "circuits" / "fet_iv.json").read_text())
    args = {s["args"]["id"]: s["args"] for s in steps if s["tool"] == "add_element" and s["args"].get("id")}
    q, iv = args["Q1"]["params"], args["IV1"]["params"]
    # CURTICE2 (IDSMOD=1) -> rf_theory.curtice_quadratic: VTO->VTO, BETA->BETA, LAMBDA->LAMBDA, ALPHA->ALPHA
    p = dict(VTO=q["VTO"], BETA=q["BETA"], LAMBDA=q["LAMBDA"], ALPHA=q["ALPHA"])
    tr = list(load_traces("fet_iv").values())
    x = tr[0][0]
    ids = np.array([y for _, y in tr])  # (n_vgs, n_vds)
    vgs = iv["VSTEP_start"] + iv["VSTEP_step"] * np.arange(len(ids))
    rec("FET_IV", "traces x points", f"{round((iv['VSTEP_stop'] - iv['VSTEP_start']) / iv['VSTEP_step']) + 1} x {len(x)}", f"{ids.shape[0]} x {ids.shape[1]}",
        ids.shape[0] == round((iv["VSTEP_stop"] - iv["VSTEP_start"]) / iv["VSTEP_step"]) + 1)
    imax = ids.max()
    cut = vgs <= p["VTO"] + 1e-9
    rec("FET_IV", "Ids ~ 0 for Vgs <= VTO", "<= 1% of max", f"max {np.abs(ids[cut]).max() / imax * 100:.2e} % of {imax * 1e3:.2f} mA", np.abs(ids[cut]).max() <= 0.01 * imax)
    j = x > 0
    rec("FET_IV", "Ids rises with Vgs (Vds>0)", "non-decreasing", "ok" if np.all(np.diff(ids[:, j], axis=0) >= -1e-9) else "violated", np.all(np.diff(ids[:, j], axis=0) >= -1e-9))
    top = ids[-1]
    s_lin = (top[2] - top[0]) / (x[2] - x[0])
    s_sat = (top[-1] - top[-21]) / (x[-1] - x[-21])
    rec("FET_IV", "linear region then saturation (Vgs max)", "slope(0-0.2V) > 10 x slope(last 2V)", f"{s_lin:.3e} vs {s_sat:.3e} A/V", s_lin > 10 * s_sat)
    ref = rf.curtice_quadratic(vgs, x, p)
    for vg, vd in ((0.0, 3.0), (-1.0, 1.0), (-0.5, 0.5), (-1.5, 4.0)):
        a, b = np.abs(vgs - vg).argmin(), np.abs(x - vd).argmin()
        e = 100 * abs(ids[a, b] - ref[a, b]) / ref[a, b]
        rec("FET_IV", f"Ids(Vgs={vg:g},Vds={vd:g}) vs curtice_quadratic", f"{ref[a, b] * 1e3:.4f} mA +/-2%", f"{ids[a, b] * 1e3:.4f} mA ({e:.3f}%)", e <= 2)
    m = ref > 0.01 * ref.max()
    e = (np.abs(ids - ref)[m] / ref[m]).max() * 100
    rec("FET_IV", "whole family vs formula (Ids>1% max)", "<= 2 %", f"max {e:.3f} %", e <= 2)


def angelov_series(vg, vd, p, rs, rd):
    """Ids with source/drain resistance: Vgs_int = Vgs - Ids*RS, Vds_int = Vds - Ids*(RS+RD), solved by fixed-point iteration."""
    i = 0.0
    for _ in range(100):
        i = rf.angelov(vg - i * rs, vd - i * (rs + rd), p)[0, 0]
    return i


def v_fet_angelov():
    if not has("fet_iv_angelov"):
        return
    steps = json.loads((HERE / "circuits" / "fet_iv_angelov.json").read_text())
    args = {s["args"]["id"]: s["args"] for s in steps if s["tool"] == "add_element"}
    q, iv = args["Q1"]["params"], args["IV1"]["params"]
    tr = list(load_traces("fet_iv_angelov").values())
    x = tr[0][0]
    ids = np.array([y for _, y in tr])  # (8 Vgs, n Vds)
    vgs = iv["VSTEP_start"] + iv["VSTEP_step"] * np.arange(len(ids))
    rec("FET_ANG", "traces x points", "8 x 51", f"{ids.shape[0]} x {ids.shape[1]}", ids.shape == (8, 51))
    for vd in (5.0, 0.5):  # saturation and knee; RS = RD = 1 Ohm are in the model, RG carries no DC current
        j = np.abs(x - vd).argmin()
        for k, vg in enumerate(vgs):
            ref = angelov_series(vg, vd, q, q["RS"], q["RD"])
            e = 100 * abs(ids[k, j] - ref) / ref
            rec("FET_ANG", f"Ids(Vgs={vg:g},Vds={vd:g})", f"{ref * 1e3:.4f} mA +/-1%", f"{ids[k, j] * 1e3:.4f} mA ({e:.3f}%)", e <= 1)


CHECKS = [v_rc, v_rl, v_rlc, v_tl, v_ms, v_fet, v_fet_angelov]

if __name__ == "__main__":
    for fn in CHECKS:
        fn()
    bad = [r for r in RESULTS if not r[4]]
    print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} checks passed")
    sys.exit(1 if bad else 0)
