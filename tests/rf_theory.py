# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Analytic RF reference for checking AWR Microwave Office results. Touches no AWR/COM.

Conventions
- f in Hz, complex S-parameters as numpy arrays over f. ABCD arrays have shape (N, 2, 2).
- Ports are real 50 Ohm unless a function takes other port impedances.
- Every element is ideal and lossless (no conductor/dielectric loss, no parasitics).
- Microstrip is zero-thickness (T = 0), lossless, no enclosure.
Run: uv run --script tests/rf_theory.py   (runs the self-check and prints the reference table)
"""
from functools import reduce

import numpy as np

C0 = 299_792_458.0  # speed of light, m/s
ETA0 = 376.73       # free-space wave impedance as used by Hammerstad-Jensen, Ohm
Z0 = 50.0           # default port impedance, Ohm

# ---------------------------------------------------------------- two-port math

def _abcd(a, b, c, d):
    a, b, c, d = np.broadcast_arrays(*(np.asarray(x, complex) for x in (a, b, c, d)))
    return np.stack([np.stack([a, b], -1), np.stack([c, d], -1)], -2)


def abcd_series(z):  # Pozar 4th ed. Table 4.1: series impedance
    return _abcd(1, z, 0, 1)


def abcd_shunt(y):  # Pozar 4th ed. Table 4.1: shunt admittance
    return _abcd(1, 0, y, 1)


def theta_at(f, theta0, f0, deg=False):  # TEM line: electrical length scales linearly with f
    return np.asarray(f, float) / f0 * (np.deg2rad(theta0) if deg else theta0)


def abcd_tline(f, zline, theta0, f0, deg=False):  # Pozar 4th ed. Table 4.1: lossless line
    t = theta_at(f, theta0, f0, deg)
    return _abcd(np.cos(t), 1j * zline * np.sin(t), 1j * np.sin(t) / zline, np.cos(t))


def cascade(*abcds):  # Pozar 4th ed. Sec. 4.4: ABCD of a cascade is the matrix product
    return reduce(np.matmul, abcds)


def abcd_to_s(abcd, z1=Z0, z2=None):
    """(S11, S21, S12, S22) for real port impedances z1, z2 (z2 defaults to z1).
    Pozar 4th ed. Table 4.2 for z1 = z2; Frickey, IEEE T-MTT 42(2) 1994 for z1 != z2 (power waves)."""
    z2 = z1 if z2 is None else z2
    a, b, c, d = abcd[..., 0, 0], abcd[..., 0, 1], abcd[..., 1, 0], abcd[..., 1, 1]
    den = a * z2 + b + c * z1 * z2 + d * z1
    k = 2 * np.sqrt(z1 * z2)
    return ((a * z2 + b - c * z1 * z2 - d * z1) / den, k / den,
            k * (a * d - b * c) / den, (-a * z2 + b - c * z1 * z2 + d * z1) / den)


def zin_line(zline, theta, zl):  # Pozar 4th ed. eq. 2.44 (finite zl)
    t = np.tan(theta)
    return zline * (zl + 1j * zline * t) / (zline + 1j * zl * t)


def gamma(z, z0=Z0):  # reflection coefficient of impedance z in a z0 system
    return (z - z0) / (z + z0)


def db(x):  # 20 log10 |x|, floored at -300 dB so exact nulls stay finite
    return 20 * np.log10(np.maximum(np.abs(x), 1e-15))


def vswr(s):
    m = np.abs(s)
    return (1 + m) / (1 - m)


def return_loss_db(s):  # positive number, RL = -20 log10 |S11|
    return -db(s)


def find_extremum(f, y, kind="min"):
    """(f_ext, y_ext) of a sampled curve, refined by a 3-point parabola.
    For a null pass |S|**2 (parabolic near a simple zero), not dB (V-shaped)."""
    y = np.asarray(y, float)
    i = int(np.argmin(y) if kind == "min" else np.argmax(y))
    if i in (0, len(y) - 1):
        return f[i], y[i]
    x = f[i - 1:i + 2] - f[i]
    a, b, c = np.polyfit(x, y[i - 1:i + 2], 2)
    return f[i] - b / (2 * a), c - b * b / (4 * a)


def f_at_level(f, y, level):
    """All frequencies where the sampled curve y crosses `level` (linear interpolation)."""
    s = np.asarray(y, float) - level
    i = np.nonzero(np.sign(s[:-1]) != np.sign(s[1:]))[0]
    return f[i] - s[i] * (f[i + 1] - f[i]) / (s[i + 1] - s[i])


HALF_POWER_DB = 20 * np.log10(1 / np.sqrt(2))  # -3.0103 dB, the "-3 dB" used everywhere below

# ---------------------------------------------------------------- reference circuits
# Each circuit: name(f, ...) -> (f, S11, S21), and name_ref(...) -> dict of closed-form numbers.

def _s(f, abcd, z1=Z0, z2=None):
    s11, s21, _, _ = abcd_to_s(abcd, z1, z2)
    return f, s11, s21


def rc_lowpass(f, R=1e3, C=1e-9, z0=Z0):  # series R, shunt C
    return _s(f, cascade(abcd_series(R), abcd_shunt(2j * np.pi * f * C)), z0)


def rc_lowpass_ref(R=1e3, C=1e-9, z0=Z0):
    # S21 = 2 / ((2 + R/z0) + j w C (R + z0)) -> single pole, C sees Rth = (R + z0) || z0
    rth = (R + z0) * z0 / (R + 2 * z0)
    return dict(s21_dc=2 * z0 / (R + 2 * z0), v2_over_vs_dc=z0 / (R + 2 * z0),
                f3db=1 / (2 * np.pi * rth * C), f_unloaded=1 / (2 * np.pi * R * C), rth=rth)


def rl_lowpass(f, L=100e-9, R=50.0, z0=Z0):  # series L, shunt R
    return _s(f, cascade(abcd_series(2j * np.pi * f * L), abcd_shunt(1 / R)), z0)


def rl_lowpass_ref(L=100e-9, R=50.0, z0=Z0):
    # S21 = 2 / ((2 + z0/R) + j w L (1/R + 1/z0)) -> L sees Rth = z0 + (R || z0)
    rth = z0 + R * z0 / (R + z0)
    return dict(s21_dc=2 * R / (2 * R + z0), f3db=rth / (2 * np.pi * L), rth=rth)


def rl_highpass(f, R=50.0, L=100e-9, z0=Z0):  # series R, shunt L (f > 0)
    return _s(f, cascade(abcd_series(R), abcd_shunt(1 / (2j * np.pi * f * L))), z0)


def rl_highpass_ref(R=50.0, L=100e-9, z0=Z0):
    # S21 = 2 / ((2 + R/z0) + (R + z0)/(j w L)) -> L sees Rth = (R + z0) || z0; -3 dB is vs f -> inf
    rth = (R + z0) * z0 / (R + 2 * z0)
    return dict(s21_hf=2 * z0 / (R + 2 * z0), f3db=rth / (2 * np.pi * L), rth=rth)


def _z_rlc(f, R, L, C):  # series R-L-C impedance (f > 0)
    w = 2 * np.pi * f
    return R + 1j * w * L + 1 / (1j * w * C)


def rlc_series_pass(f, R=1.0, L=100e-9, C=0.1e-12, z0=Z0):  # series RLC in the through path
    return _s(f, abcd_series(_z_rlc(f, R, L, C)), z0)


def rlc_series_pass_ref(R=1.0, L=100e-9, C=0.1e-12, z0=Z0):
    # S21 = 2 z0 / (2 z0 + Z); |S21| -3 dB from peak where X = +-(R + 2 z0)  =>  BW = (R + 2 z0) / (2 pi L), exact
    w0 = 1 / np.sqrt(L * C)
    rt = R + 2 * z0
    return dict(f0=w0 / (2 * np.pi), q0=w0 * L / R, ql=w0 * L / rt,
                s21_f0=2 * z0 / rt, bw3db=rt / (2 * np.pi * L))


def rlc_shunt_notch(f, R=1.0, L=100e-9, C=0.1e-12, z0=Z0):  # series RLC from the line to ground
    return _s(f, abcd_shunt(1 / _z_rlc(f, R, L, C)), z0)


def rlc_shunt_notch_ref(R=1.0, L=100e-9, C=0.1e-12, z0=Z0):
    # S21 = Z / (Z + z0/2); |S21| = 1/sqrt2 where X = +-sqrt((R + z0/2)^2 - 2 R^2)  =>  BW below, exact
    # S11 = S21 - 1 peaks at f0 with -3 dB-from-peak width (R + z0/2)/(2 pi L) = f0/QL
    w0 = 1 / np.sqrt(L * C)
    rt = R + z0 / 2
    return dict(f0=w0 / (2 * np.pi), q0=w0 * L / R, ql=w0 * L / rt, s21_f0=R / rt,
                bw3db_s21=np.sqrt(rt**2 - 2 * R**2) / (2 * np.pi * L), bw3db_s11=rt / (2 * np.pi * L))


def qwt(f, zl=100.0, f0=2e9, z0=Z0, z_port2=None):
    """Quarter-wave transformer, ideal line Zt = sqrt(z0 zl), 90 deg at f0.
    Port 1 = z0. Port 2 reference = z_port2, default zl (same S11 as port 2 terminated in zl).
    z_port2 = z0 gives the bare transformer between two 50 Ohm ports."""
    return _s(f, abcd_tline(f, np.sqrt(z0 * zl), np.pi / 2, f0), z0, zl if z_port2 is None else z_port2)


def qwt_ref(zl=100.0, f0=2e9, z0=Z0, s11_max_db=-20.0):
    zt = np.sqrt(z0 * zl)
    gm = 10 ** (s11_max_db / 20)
    # Pozar 4th ed. Sec. 5.4 (TEM): df/f0 = 2 - (4/pi) acos[ Gm/sqrt(1-Gm^2) * 2 sqrt(z0 zl)/|zl - z0| ]
    fbw = 2 - 4 / np.pi * np.arccos(gm / np.sqrt(1 - gm**2) * 2 * np.sqrt(z0 * zl) / abs(zl - z0))
    return dict(zt=zt, f0=f0, f_null2=3 * f0, fbw=fbw, s11_max_db=s11_max_db,
                s11_f0_bare_50_50=gamma(zt**2 / z0, z0))


def stub_lambda4(f, kind="open", zs=Z0, f0=2e9, z0=Z0):
    """Shunt stub, 90 deg at f0. Open: Yin = j tan(t)/Zs; short: Yin = -j/(Zs tan t)  (Pozar 4th ed. Sec. 2.3).
    Open -> S21 = 0 at f0 (and 3 f0); short -> S21 = 1 at f0. f > 0."""
    t = theta_at(f, np.pi / 2, f0)
    y = 1j * np.tan(t) / zs if kind == "open" else -1j / (zs * np.tan(t))
    return _s(f, abcd_shunt(y), z0)


def tline(f, zline, theta0, f0, deg=False, z0=Z0):  # ideal TLIN (Z0, EL at F0) between z0 ports
    return _s(f, abcd_tline(f, zline, theta0, f0, deg), z0)
# lambda/2 of any zline is transparent at f0: tline(f, zline, 180, f0, deg=True) -> S11 = 0, S21 = -1.


def thru_line(f, length, eps_eff=1.0, zline=Z0, z0=Z0):  # physical length (m); |S21| = 1, phase -beta*L
    return tline(f, zline, 2 * np.pi * np.sqrt(eps_eff) * length / C0, 1.0, z0=z0)  # theta = beta*L, theta0 per Hz


def beta(f, eps_eff=1.0):  # rad/m
    return 2 * np.pi * np.asarray(f, float) * np.sqrt(eps_eff) / C0

# ---------------------------------------------------------------- microstrip (zero thickness, lossless)

def ms_analysis(w, h, er):
    """(Z0, static eps_eff) of a zero-thickness microstrip. Hammerstad & Jensen, IEEE MTT-S Digest 1980."""
    u = w / h
    fu = 6 + (2 * np.pi - 6) * np.exp(-(30.666 / u) ** 0.7528)
    z01 = ETA0 / (2 * np.pi) * np.log(fu / u + np.sqrt(1 + (2 / u) ** 2))  # air-filled line
    a = 1 + np.log((u**4 + (u / 52) ** 2) / (u**4 + 0.432)) / 49 + np.log(1 + (u / 18.1) ** 3) / 18.7
    b = 0.564 * ((er - 0.9) / (er + 3)) ** 0.053
    ee = (er + 1) / 2 + (er - 1) / 2 * (1 + 10 / u) ** (-a * b)
    return z01 / np.sqrt(ee), ee


def ms_wh_wheeler(z0, er):
    """W/H for a target Z0, closed form (Wheeler/Hammerstad as in Pozar 4th ed. Sec. 3.8). About 1 % accurate."""
    A = z0 / 60 * np.sqrt((er + 1) / 2) + (er - 1) / (er + 1) * (0.23 + 0.11 / er)
    wh = 8 * np.exp(A) / (np.exp(2 * A) - 2)
    if wh <= 2:
        return wh
    B = 377 * np.pi / (2 * z0 * np.sqrt(er))
    return 2 / np.pi * (B - 1 - np.log(2 * B - 1) + (er - 1) / (2 * er) * (np.log(B - 1) + 0.39 - 0.61 / er))


def ms_synthesis(z0, h, er):
    """W (same unit as h) whose Hammerstad-Jensen Z0 equals z0: bisection in log(W/H), Z0 falls with W."""
    lo, hi = np.log(1e-3), np.log(1e3)
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ms_analysis(np.exp(mid) * h, h, er)[0] > z0 else (lo, mid)
    return np.exp((lo + hi) / 2) * h


def ms_eeff_kj(w, h, er, f):
    """Dispersive eps_eff(f), Kirschning & Jansen, Electron. Lett. 18(6) 1982. h in m, f in Hz."""
    u = w / h
    ee0 = ms_analysis(w, h, er)[1]
    fn = np.asarray(f, float) / 1e9 * h * 1e3  # GHz * mm
    p1 = 0.27488 + (0.6315 + 0.525 / (1 + 0.0157 * fn) ** 20) * u - 0.065683 * np.exp(-8.7513 * u)
    p2 = 0.33622 * (1 - np.exp(-0.03442 * er))
    p3 = 0.0363 * np.exp(-4.6 * u) * (1 - np.exp(-((fn / 38.7) ** 4.97)))
    p4 = 1 + 2.751 * (1 - np.exp(-((er / 15.916) ** 8)))
    p = p1 * p2 * ((0.1844 + p3 * p4) * fn) ** 1.5763
    return er - (er - ee0) / (1 + p)


def guided_wavelength(f, eps_eff):  # lambda_g = c / (f sqrt(eps_eff))
    return C0 / (np.asarray(f, float) * np.sqrt(eps_eff))

# ---------------------------------------------------------------- EM-level references (open end, stub, patch, phase)
# Tolerance guidance for comparing AXIEM (2.5D MoM) / Analyst (3D FEM) against these closed forms.
# Realistic agreement, with the reason:
#   Z0, static eps_eff     1-2 %  HJ is fitted to ~0.2-1 % of exact T=0 solutions; the rest is mesh/cell size in the EM solver.
#   eps_eff(f), phase      1-2 %  KJ is a fit (~0.6 % in its range); EM adds port de-embedding and mesh error.
#   open-end dL            10-20 % of dL itself (a few % of a lambda/4 stub): dL is a quasi-static fit and the EM
#                          fringing field depends on mesh, box height and the port reference plane.
#   open-stub notch f      about 2 %: line eeff (1 %) plus dL (small share) plus the T-junction, which the model ignores.
#   patch resonance f      2-4 %: the cavity model assumes a magnetic wall, a constant eeff and the dL of a wide line,
#                          and ignores the feed and ground-plane size; trust the EM answer, use the cavity for order and trend.
#   patch R_edge           factor of ~1.5, not %: it is very sensitive to the resonance offset; compare input R at the EM peak only.
# Assumptions the validator must match: T = 0 (zero-thickness strip), lossless, infinite ground plane and no enclosure
# (or a lid/walls far away: > 10 h side, > 20 h above), PEC, a feed that does not perturb the patch (edge-fed by a
# 50 Ohm line with the port de-embedded to the patch edge, or an inset feed with the notch gap ~ line width).

def ms_open_end_dl(w, h, er, model="hb"):
    """Open-end length extension dL (m) of a microstrip, static eps_eff.
    hb: Hammerstad & Bekkadal 1975, dL/h = 0.412 (ee+0.3)(u+0.264) / ((ee-0.258)(u+0.8)).
    kjk: Kirschning, Jansen & Koster, Archiv Elektrotech. 1981 (as tabulated in Kirschning-Jansen-Koster / Garg et al.)."""
    u, ee = w / h, ms_analysis(w, h, er)[1]
    if model == "hb":
        return h * 0.412 * (ee + 0.3) * (u + 0.264) / ((ee - 0.258) * (u + 0.8))
    x1 = 0.434907 * (ee**0.81 + 0.26) / (ee**0.81 - 0.189) * (u**0.8544 + 0.236) / (u**0.8544 + 0.87)
    x2 = 1 + u**0.371 / (2.358 * er + 1)
    x3 = 1 + 0.5274 * np.arctan(0.084 * u ** (1.9413 / x2)) / ee**0.9236
    x4 = 1 + 0.0377 * np.arctan(0.067 * u**1.456) * (6 - 5 * np.exp(0.036 * (1 - er)))
    x5 = 1 - 0.218 * np.exp(-7.5 * u)
    return h * x1 * x3 * x5 / x4


def stub_open_length(f0, w, h, er, end_effect=True, dispersion=True):
    """Physical length (m) of an open microstrip stub (width w) that is lambda/4 at f0: L = lambda_g/4 - dL.
    end_effect=False, dispersion=False is the 'naive' length lambda_g(static eeff)/4."""
    ee = ms_eeff_kj(w, h, er, f0) if dispersion else ms_analysis(w, h, er)[1]
    return C0 / (4 * f0 * np.sqrt(ee)) - (ms_open_end_dl(w, h, er) if end_effect else 0.0)


def stub_open_notch_f(length, w, h, er):
    """Notch frequency (Hz) of an open stub of physical length `length`: solves 4 f (L + dL) sqrt(eeff_KJ(f)) = c by bisection."""
    le = length + ms_open_end_dl(w, h, er)
    lo, hi = 1e6, C0 / (4 * le * np.sqrt(ms_analysis(w, h, er)[1])) * 3
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if 4 * mid * le * np.sqrt(ms_eeff_kj(w, h, er, mid)) < C0 else (lo, mid)
    return (lo + hi) / 2


def _j0(x):  # Bessel J0 by power series, fine for x < ~10 (patch L k0 < 3)
    x = np.asarray(x, float)
    t, s = np.ones_like(x), np.ones_like(x)
    for k in range(1, 40):
        t = t * -((x / 2) ** 2) / k**2
        s = s + t
    return s


def patch_edge_resistance(w, l, h, er, f0, model="balanis"):
    """Radiating-edge input resistance (Ohm) of a rectangular patch.
    balanis: Rin = 1/(2 (G1 + G12)), Balanis 4th ed. eqs. 14-12, 14-18a, 14-17 (G1 for h << lambda0, G12 integrated numerically).
    simple: 90 er^2/(er-1) (L/W)^2 (rule of thumb)."""
    if model == "simple":
        return 90 * er**2 / (er - 1) * (l / w) ** 2
    k0 = 2 * np.pi * f0 / C0
    g1 = w / (120 * (C0 / f0)) * (1 - (k0 * h) ** 2 / 24)
    th = np.linspace(0, np.pi, 20001)
    a = k0 * w / 2
    integrand = (a * np.sinc(a * np.cos(th) / np.pi)) ** 2 * _j0(k0 * l * np.sin(th)) * np.sin(th) ** 3
    g12 = np.trapezoid(integrand, th) / (120 * np.pi**2)
    return 1 / (2 * (g1 + g12))


def patch_design(f0, h, er):
    """Rectangular patch, cavity model, Balanis 4th ed. ch. 14 (eqs. 14-6 .. 14-8). Returns dict (SI):
    w, l, eeff (Balanis W/h>1 form), dl (Hammerstad, Balanis 14-2), r_edge (G1/G12), r_edge_simple, y0 (inset for 50 Ohm)."""
    w = C0 / (2 * f0) * np.sqrt(2 / (er + 1))
    ee = (er + 1) / 2 + (er - 1) / 2 * (1 + 12 * h / w) ** -0.5
    dl = patch_dl(w, h, ee)
    l = C0 / (2 * f0 * np.sqrt(ee)) - 2 * dl
    r = patch_edge_resistance(w, l, h, er, f0)
    return dict(w=w, l=l, eeff=ee, dl=dl, r_edge=r, r_edge_simple=patch_edge_resistance(w, l, h, er, f0, "simple"),
                y0=patch_inset(r, l))


def patch_dl(w, h, ee):  # Hammerstad, as Balanis eq. 14-2 (ee = Balanis eeff for the patch width)
    return h * 0.412 * (ee + 0.3) * (w / h + 0.264) / ((ee - 0.258) * (w / h + 0.8))


def patch_inset(r_edge, l, rin=Z0):  # R(y0) = R_edge cos^2(pi y0 / L)  ->  y0 for the wanted input resistance
    return l / np.pi * np.arccos(np.sqrt(rin / r_edge))


def patch_f_res(l, w, h, er):
    """Resonant frequency (Hz) of the TM010 mode for patch length l, width w: f = c / (2 (L + 2 dL) sqrt(eeff))."""
    ee = (er + 1) / 2 + (er - 1) / 2 * (1 + 12 * h / w) ** -0.5
    return C0 / (2 * (l + 2 * patch_dl(w, h, ee)) * np.sqrt(ee))


def ms_s21_phase_deg(w, h, er, length, f):
    """Wrapped (-180, 180] S21 phase in deg of a matched (50 Ohm, Z0 = line Z0) microstrip line: -beta L, KJ eps_eff(f)."""
    ph = -2 * np.pi * np.asarray(f, float) * np.sqrt(ms_eeff_kj(w, h, er, f)) * length / C0
    return (np.degrees(ph) + 180) % 360 - 180


def ms_eeff_from_phase(phase_deg, length, f, eeff_guess):
    """eps_eff from a measured S21 phase (deg, any wrap): picks the 360 deg turn count nearest the guess, then
    eeff = (c * phi_unwrapped / (2 pi f L))^2 with phi = -phase."""
    guess = 2 * np.pi * f * np.sqrt(eeff_guess) * length / C0  # rad, unwrapped
    phi = np.deg2rad(-phase_deg)
    phi = phi + 2 * np.pi * np.round((guess - phi) / (2 * np.pi))
    return (C0 * phi / (2 * np.pi * f * length)) ** 2

# ---------------------------------------------------------------- FET DC I-V
# Each model: ids(vgs, vds, p) -> Ids (A) on the grid shape (len(vgs), len(vds)). Keys of p are the names
# used in each model's original paper / SPICE documentation; AWR names may differ (map them later).

def _grid(vgs, vds):
    return np.meshgrid(np.atleast_1d(np.asarray(vgs, float)), np.atleast_1d(np.asarray(vds, float)), indexing="ij")


def curtice_quadratic(vgs, vds, p):
    """Curtice, IEEE T-MTT 28(5) 1980; SPICE GaAsFET level 1. Keys: VTO, BETA, LAMBDA, ALPHA."""
    g, d = _grid(vgs, vds)
    vt = np.maximum(g - p["VTO"], 0.0)
    return p["BETA"] * vt**2 * (1 + p["LAMBDA"] * d) * np.tanh(p["ALPHA"] * d)


def curtice_cubic(vgs, vds, p):
    """Curtice & Ettenberg, IEEE T-MTT 33(12) 1985. Keys: A0, A1, A2, A3, BETA, GAMMA, VDS0.
    Ids = (A0 + A1 V1 + A2 V1^2 + A3 V1^3) tanh(GAMMA Vds), V1 = Vgs (1 + BETA (VDS0 - Vds)).
    shortcut: cutoff clamped as Ids >= 0; vendors differ (some use a VT0 pinch-off key), check AWR's rule."""
    g, d = _grid(vgs, vds)
    v1 = g * (1 + p["BETA"] * (p["VDS0"] - d))
    poly = p["A0"] + p["A1"] * v1 + p["A2"] * v1**2 + p["A3"] * v1**3
    return np.maximum(poly, 0.0) * np.tanh(p["GAMMA"] * d)


def statz(vgs, vds, p):
    """Statz et al. (Raytheon), IEEE T-ED 34(2) 1987; SPICE GaAsFET level 2. Keys: VTO, BETA, B, ALPHA, LAMBDA.
    Ids = BETA (Vgs-VTO)^2 / (1 + B (Vgs-VTO)) * K(Vds) * (1 + LAMBDA Vds),
    K = 1 - (1 - ALPHA Vds/3)^3 for 0 <= Vds < 3/ALPHA, else 1."""
    g, d = _grid(vgs, vds)
    vt = np.maximum(g - p["VTO"], 0.0)
    k = np.where(d < 3 / p["ALPHA"], 1 - (1 - p["ALPHA"] * d / 3) ** 3, 1.0)
    return p["BETA"] * vt**2 / (1 + p["B"] * vt) * k * (1 + p["LAMBDA"] * d)


def mosfet_level1(vgs, vds, p):
    """Shichman-Hodges, IEEE JSSC 3(3) 1968; SPICE MOSFET level 1 (NMOS, Vds >= 0, no body effect).
    Keys: VTO, KP, W, L, LAMBDA. beta = KP W/L.
    Linear (Vds < Vgs-VTO): beta (Vgs-VTO - Vds/2) Vds (1 + LAMBDA Vds); saturation: beta/2 (Vgs-VTO)^2 (1 + LAMBDA Vds)."""
    g, d = _grid(vgs, vds)
    b = p["KP"] * p["W"] / p["L"]
    vov = np.maximum(g - p["VTO"], 0.0)
    return np.where(d < vov, b * (vov - d / 2) * d, b / 2 * vov**2) * (1 + p["LAMBDA"] * d)


def angelov(vgs, vds, p):
    """Angelov, Zirath & Rorsman, IEEE T-MTT 40(12) 1992, basic form. Keys: IPK, VPK, P1, P2, P3, ALPHA, LAMBDA.
    Ids = IPK (1 + tanh psi)(1 + LAMBDA Vds) tanh(ALPHA Vds), psi = P1 x + P2 x^2 + P3 x^3, x = Vgs - VPK."""
    g, d = _grid(vgs, vds)
    x = g - p["VPK"]
    psi = p["P1"] * x + p["P2"] * x**2 + p["P3"] * x**3
    return p["IPK"] * (1 + np.tanh(psi)) * (1 + p["LAMBDA"] * d) * np.tanh(p["ALPHA"] * d)


# Example parameter sets (illustrative GaAs MESFET / NMOS values, used only by the self-check)
CURTICE_Q_P = dict(VTO=-2.0, BETA=0.05, LAMBDA=0.02, ALPHA=2.0)
CURTICE_C_P = dict(A0=0.1, A1=0.1, A2=0.025, A3=-0.002, BETA=0.02, GAMMA=2.0, VDS0=3.0)
STATZ_P = dict(VTO=-2.0, BETA=0.05, B=0.3, ALPHA=2.0, LAMBDA=0.02)
MOS1_P = dict(VTO=1.0, KP=2e-5, W=100e-6, L=1e-6, LAMBDA=0.02)
ANGELOV_P = dict(IPK=0.05, VPK=-0.5, P1=1.5, P2=0.0, P3=0.1, ALPHA=2.0, LAMBDA=0.02)

# ---------------------------------------------------------------- comparison helpers for the validator

def compare(name, f, sim_db, ref_db, tol_db, floor_db=-60.0):
    """Max and RMS |sim - ref| in dB, both floored at floor_db so deep nulls do not dominate. -> (ok, max, rms)."""
    e = np.abs(np.maximum(sim_db, floor_db) - np.maximum(ref_db, floor_db))
    mx, rms = float(e.max()), float(np.sqrt(np.mean(e**2)))
    ok = mx <= tol_db
    print(f"{name:<34} max {mx:9.4f} dB  rms {rms:9.4f} dB  (worst at {f[e.argmax()] / 1e9:.6g} GHz)"
          f"  tol {tol_db} dB  {'PASS' if ok else 'FAIL'}")
    return ok, mx, rms


def compare_freq(name, sim_f0, ref_f0, tol_pct):
    """Relative frequency error in %. -> (ok, err_pct)."""
    err = 100 * abs(sim_f0 - ref_f0) / abs(ref_f0)
    ok = err <= tol_pct
    print(f"{name:<34} sim {sim_f0 / 1e9:.6g} GHz  ref {ref_f0 / 1e9:.6g} GHz  err {err:.4f} %"
          f"  tol {tol_pct} %  {'PASS' if ok else 'FAIL'}")
    return ok, err

# ---------------------------------------------------------------- self-check and reference table

def _close(a, b, rel):
    return abs(a - b) <= rel * abs(b)


def _self_check():
    checks = []

    def check(name, cond):
        assert cond, name
        checks.append(name)

    f0 = 2e9
    f = np.linspace(0.05e9, 7e9, 140001)

    # lossless + reciprocity on raw ABCD -> S
    lossless = {
        "TLIN 70.71 Ohm 90 deg (50/100 ports)": (abcd_tline(f, np.sqrt(5000), 90, f0, deg=True), 50, 100),
        "TLIN 100 Ohm 180 deg": (abcd_tline(f, 100, 180, f0, deg=True), 50, 50),
        "open lambda/4 stub": (abcd_shunt(1j * np.tan(theta_at(f, np.pi / 2, f0)) / 50), 50, 50),
        "short lambda/4 stub": (abcd_shunt(-1j / (50 * np.tan(theta_at(f, np.pi / 2, f0)))), 50, 50),
        "series L + shunt C + line": (cascade(abcd_series(2j * np.pi * f * 5e-9),
                                              abcd_shunt(2j * np.pi * f * 2e-12), abcd_tline(f, 35, 60, f0, True)), 50, 50),
    }
    for name, (m, z1, z2) in lossless.items():
        s11, s21, s12, s22 = abcd_to_s(m, z1, z2)
        check(f"lossless |S11|^2+|S21|^2=1: {name}", np.allclose(abs(s11) ** 2 + abs(s21) ** 2, 1, atol=1e-9))
        check(f"lossless |S22|^2+|S12|^2=1: {name}", np.allclose(abs(s22) ** 2 + abs(s12) ** 2, 1, atol=1e-9))
        check(f"reciprocal S12=S21: {name}", np.allclose(s12, s21, atol=1e-12))
    s = abcd_to_s(cascade(abcd_series(1e3), abcd_shunt(2j * np.pi * f * 1e-9)))
    check("reciprocal S12=S21: RC low-pass (lossy)", np.allclose(s[2], s[1], atol=1e-12))

    # quarter-wave transformer
    _, s11q, _ = qwt(np.array([f0, 3 * f0]))
    check("QWT |S11| < 1e-9 at f0 and 3 f0", np.all(abs(s11q) < 1e-9))
    _, s11b, _ = qwt(np.array([f0]), z_port2=50)
    check("QWT: S11 with 100 Ohm port-2 ref = Gamma of zin_line(Zt, theta, 100 Ohm load)",
          np.allclose(gamma(zin_line(np.sqrt(5000), theta_at(f, np.pi / 2, f0), 100)), qwt(f)[1], atol=1e-12))
    check("QWT bare between 50/50 ports: S11(f0) = 1/3", np.isclose(s11b[0], 1 / 3))
    r = qwt_ref()
    _, s11, _ = qwt(f)
    fc = f_at_level(f, db(s11), -20.0)
    fc = fc[(fc > 0.5 * f0) & (fc < 1.5 * f0)]
    check("QWT -20 dB fractional bandwidth: sweep = closed form (1e-4)", _close((fc[1] - fc[0]) / f0, r["fbw"], 1e-4))
    fq = np.linspace(1.9e9, 2.1e9, 1000)  # grid does not contain f0
    fmin, _ = find_extremum(fq, abs(qwt(fq)[1]) ** 2)
    check("QWT null located by find_extremum within 1e-6", _close(fmin, f0, 1e-6))

    # stubs, half-wave line, thru
    _, _, s21o = stub_lambda4(np.array([f0]), "open")
    _, _, s21s = stub_lambda4(np.array([f0]), "short")
    check("open lambda/4 shunt stub |S21| < 1e-9 at f0", abs(s21o[0]) < 1e-9)
    check("short lambda/4 shunt stub |S21| = 1 at f0", abs(abs(s21s[0]) - 1) < 1e-9)
    _, s11h, s21h = tline(np.array([f0]), 100, 180, f0, deg=True)
    check("lambda/2 100 Ohm line: |S11| < 1e-9, S21 = -1 at f0", abs(s11h[0]) < 1e-9 and abs(s21h[0] + 1) < 1e-9)
    L, ee = 25e-3, 2.5
    _, s11t, s21t = thru_line(f, L, ee)
    check("50 Ohm thru: |S21| = 1, S11 = 0", np.allclose(abs(s21t), 1) and np.all(abs(s11t) < 1e-12))
    check("50 Ohm thru: angle(S21) = -beta L (wrapped)", np.allclose(np.exp(1j * np.angle(s21t)), np.exp(-1j * beta(f, ee) * L)))

    # RC low-pass
    rr = rc_lowpass_ref()
    _, _, s21dc = rc_lowpass(np.array([0.0]))
    check("RC LPF DC: S21 = 2*50/(1000+100) = 0.0909..., i.e. V2/Vs = 50/1100", np.isclose(s21dc[0], 100 / 1100, rtol=1e-12))
    fl = np.logspace(3, 9, 200001)
    _, _, s21 = rc_lowpass(fl)
    check("RC LPF -3 dB (vs DC): sweep = closed form (1e-4)", _close(f_at_level(fl, db(s21) - db(rr["s21_dc"]), HALF_POWER_DB)[0], rr["f3db"], 1e-4))

    # RL filters
    for fn, ref, base in ((rl_lowpass, rl_lowpass_ref(), "s21_dc"), (rl_highpass, rl_highpass_ref(), "s21_hf")):
        fl = np.logspace(5, 11, 200001)
        _, _, s21 = fn(fl)
        check(f"{fn.__name__} -3 dB: sweep = closed form (1e-4)",
              _close(f_at_level(fl, db(s21) - db(ref[base]), HALF_POWER_DB)[0], ref["f3db"], 1e-4))
    check("rl_lowpass DC S21 = 2/3", np.isclose(abs(rl_lowpass(np.array([1.0]))[2][0]), 2 / 3, rtol=1e-6))

    # RLC
    fr = np.linspace(0.2e9, 4e9, 400001)
    rp = rlc_series_pass_ref()
    _, _, s21 = rlc_series_pass(fr)
    fpk, _ = find_extremum(fr, abs(s21) ** 2, "max")
    check("series RLC pass: peak f = f0 (1e-6)", _close(fpk, rp["f0"], 1e-6))
    check("series RLC pass: S21(f0) = 2 z0/(R+2 z0)", np.isclose(abs(rlc_series_pass(np.array([rp["f0"]]))[2][0]), rp["s21_f0"]))
    fc = f_at_level(fr, db(s21) - db(rp["s21_f0"]), HALF_POWER_DB)
    check("series RLC pass: -3 dB BW sweep = (R+2 z0)/(2 pi L) (1e-4)", _close(fc[1] - fc[0], rp["bw3db"], 1e-4))
    rn = rlc_shunt_notch_ref()
    _, s11, s21 = rlc_shunt_notch(fr)
    fn0, _ = find_extremum(fr, abs(s21) ** 2, "min")
    check("shunt RLC notch: min f = f0 (1e-6)", _close(fn0, rn["f0"], 1e-6))
    fc = f_at_level(fr, db(s21), HALF_POWER_DB)
    check("shunt RLC notch: |S21| = -3 dB width sweep = closed form (1e-4)", _close(fc[1] - fc[0], rn["bw3db_s21"], 1e-4))
    fc = f_at_level(fr, db(s11) - db(1 - rn["s21_f0"]), HALF_POWER_DB)
    check("shunt RLC notch: |S11| -3 dB-from-peak width = f0/QL (1e-4)", _close(fc[1] - fc[0], rn["bw3db_s11"], 1e-4))

    # microstrip
    w_fr4 = ms_synthesis(50, 1.6e-3, 4.4)
    check("FR4 1.6 mm 50 Ohm W within 3.0 +/- 0.15 mm", abs(w_fr4 * 1e3 - 3.0) <= 0.15)
    for name, h, er in (("FR4", 1.6e-3, 4.4), ("RO4003C", 0.508e-3, 3.55)):
        for z in (25, 50, 75, 100):
            check(f"{name} {z} Ohm: synthesis -> analysis round trip (1e-9)", _close(ms_analysis(ms_synthesis(z, h, er), h, er)[0], z, 1e-9))
            check(f"{name} {z} Ohm: Wheeler closed form within 2 % of HJ-exact W",
                  _close(ms_wh_wheeler(z, er) * h, ms_synthesis(z, h, er), 0.02))
        w = ms_synthesis(50, h, er)
        check(f"{name}: KJ eps_eff(f->0) = static HJ eps_eff", np.isclose(ms_eeff_kj(w, h, er, 1.0), ms_analysis(w, h, er)[1], rtol=1e-6))

    # EM-level references
    for name, h, er in (("FR4", 1.6e-3, 4.4), ("RO4003C", 0.508e-3, 3.55)):
        for u in (1, 2, 5, 10, 20):
            check(f"{name} W/h={u}: dL/h (hb) in 0.3-0.5", 0.3 <= ms_open_end_dl(u * h, h, er) / h <= 0.5)
            # KJK runs up to ~15 % above HB for wide lines (W/h >= 5), so only the 50 Ohm range is bounded
            check(f"{name} W/h={u}: dL/h (kjk) in 0.3-0.58", 0.3 <= ms_open_end_dl(u * h, h, er, "kjk") / h <= 0.58)
        w = ms_synthesis(50, h, er)
        check(f"{name}: dL HB and KJK agree within 8 %", _close(ms_open_end_dl(w, h, er, "kjk"), ms_open_end_dl(w, h, er), 0.08))
        check(f"{name}: stub with dL + dispersion shorter than naive", stub_open_length(2e9, w, h, er) < stub_open_length(2e9, w, h, er, False, False))
        check(f"{name}: stub notch inverse returns f0 (1e-6)", _close(stub_open_notch_f(stub_open_length(2e9, w, h, er), w, h, er), 2e9, 1e-6))
        pd = patch_design(2.4e9, h, er)
        check(f"{name} patch: inverse(L) = f0 (1e-6)", _close(patch_f_res(pd["l"], pd["w"], h, er), 2.4e9, 1e-6))
        check(f"{name} patch: R(y0) = 50 Ohm", np.isclose(pd["r_edge"] * np.cos(np.pi * pd["y0"] / pd["l"]) ** 2, 50))
        check(f"{name} patch: R_edge G1/G12 in 100-250 Ohm, rule of thumb within x2.2 of it",
              100 < pd["r_edge"] < 250 and 1 < pd["r_edge_simple"] / pd["r_edge"] < 2.2)
        fq = np.array([0.5e9, 2e9, 5e9])
        ph = ms_s21_phase_deg(w, h, er, 30e-3, fq)
        check(f"{name}: phase -> eeff round trip (1e-9)",
              np.allclose(ms_eeff_from_phase(ph, 30e-3, fq, ms_eeff_kj(w, h, er, fq) * 1.05), ms_eeff_kj(w, h, er, fq), rtol=1e-9))
    pd = patch_design(2.4e9, 1.6e-3, 4.4)
    check("FR4 2.4 GHz patch: W = 38.0 +/- 0.5 mm, L = 29.4 +/- 0.6 mm", abs(pd["w"] * 1e3 - 38.0) < 0.5 and abs(pd["l"] * 1e3 - 29.4) < 0.6)
    check("J0 series: J0(0)=1, J0(2.404826)=0", np.isclose(_j0(0.0), 1) and abs(_j0(2.404826)) < 1e-5)
    # Balanis ex. 14.1: er 2.2, h 0.1588 cm, 10 GHz -> W 11.86 mm, L 9.06 mm
    pb = patch_design(10e9, 1.588e-3, 2.2)
    check("Balanis ex. 14.1 (er 2.2, 10 GHz): W = 11.86 mm, L = 9.06 mm within 0.1 mm",
          abs(pb["w"] * 1e3 - 11.86) < 0.1 and abs(pb["l"] * 1e3 - 9.06) < 0.1)

    # FETs
    vgs, vds = np.linspace(-3, 1, 41), np.linspace(0, 6, 601)
    idq = curtice_quadratic(vgs, vds, CURTICE_Q_P)
    check("Curtice quadratic: Ids = 0 for Vgs <= VTO", np.all(idq[vgs <= CURTICE_Q_P["VTO"]] == 0))
    check("Curtice quadratic: Ids increases monotonically with Vds (Vgs > VTO)", np.all(np.diff(idq[vgs > CURTICE_Q_P["VTO"]], axis=1) > 0))
    knee = 3 / STATZ_P["ALPHA"]
    a, b = statz(0.0, [knee - 1e-9, knee + 1e-9], STATZ_P)[0]
    check("Statz: continuous at Vds = 3/ALPHA", np.isclose(a, b, rtol=1e-6))
    check("Statz: Ids = 0 for Vgs <= VTO", np.all(statz(vgs, vds, STATZ_P)[vgs <= STATZ_P["VTO"]] == 0))
    vdsat = 2.0 - MOS1_P["VTO"]
    a, b = mosfet_level1(2.0, [vdsat - 1e-9, vdsat + 1e-9], MOS1_P)[0]
    check("MOSFET level 1: continuous at Vds = Vgs - VTO", np.isclose(a, b, rtol=1e-6))
    check("MOSFET level 1: Ids = 0 for Vgs <= VTO", np.all(mosfet_level1([0.0, 1.0], vds, MOS1_P) == 0))
    check("Angelov: Ids >= 0 and Ids(Vds=0) = 0", np.all(angelov(vgs, vds, ANGELOV_P) >= 0) and np.all(angelov(vgs, 0.0, ANGELOV_P) == 0))
    check("Curtice cubic: Ids >= 0, Ids(Vds=0) = 0", np.all(curtice_cubic(vgs, vds, CURTICE_C_P) >= 0) and np.all(curtice_cubic(vgs, 0.0, CURTICE_C_P) == 0))

    # comparison helpers on known inputs
    ok, mx, _ = compare("helper test: identical curves", f, db(s21), db(s21), 0.01)
    check("compare(): identical -> PASS, max 0", ok and mx == 0)
    check("compare_freq(): 0.1 % off with 0.5 % tol -> PASS", compare_freq("helper test: 0.1 % off", 1.001 * f0, f0, 0.5)[0])
    return checks


def _table():
    def row(circuit, quantity, value, unit=""):
        print(f"{circuit:<30} {quantity:<44} {value:>14.6g} {unit}")

    print(f"{'circuit':<30} {'quantity':<44} {'value':>14} unit")
    print("-" * 96)
    r = rc_lowpass_ref()
    c = "RC LPF R=1k series, C=1n sh"
    row(c, "|S21| at DC", db(r["s21_dc"]), "dB")
    row(c, "|S21| at DC (linear, = 2*50/1100)", r["s21_dc"])
    row(c, "Thevenin R seen by C = 1050||50", r["rth"], "Ohm")
    row(c, "f(-3 dB vs DC), loaded, exact", r["f3db"] / 1e6, "MHz")
    row(c, "1/(2 pi R C) unloaded (NOT the answer)", r["f_unloaded"] / 1e6, "MHz")
    r = rl_lowpass_ref()
    c = "RL LPF L=100n ser, R=50 sh"
    row(c, "|S21| at DC", db(r["s21_dc"]), "dB")
    row(c, "f(-3 dB vs DC) = 75/(2 pi L)", r["f3db"] / 1e6, "MHz")
    r = rl_highpass_ref()
    c = "RL HPF R=50 ser, L=100n sh"
    row(c, "|S21| as f -> inf", db(r["s21_hf"]), "dB")
    row(c, "f(-3 dB vs HF) = 33.33/(2 pi L)", r["f3db"] / 1e6, "MHz")
    r = rlc_series_pass_ref()
    c = "RLC series, in path (pass)"
    row(c, "f0 = 1/(2 pi sqrt(LC)), R=1 L=100n C=0.1p", r["f0"] / 1e9, "GHz")
    row(c, "Q0 = w0 L / R", r["q0"])
    row(c, "QL = w0 L / (R + 2 z0)", r["ql"])
    row(c, "|S21| at f0", db(r["s21_f0"]), "dB")
    row(c, "BW -3 dB from peak = (R+100)/(2 pi L)", r["bw3db"] / 1e6, "MHz")
    r = rlc_shunt_notch_ref()
    c = "RLC series, shunt (notch)"
    row(c, "f0", r["f0"] / 1e9, "GHz")
    row(c, "QL = w0 L / (R + z0/2)", r["ql"])
    row(c, "|S21| at f0 = R/(R+25)", db(r["s21_f0"]), "dB")
    row(c, "BW where |S21| < -3.01 dB (absolute)", r["bw3db_s21"] / 1e6, "MHz")
    row(c, "BW of |S11| -3 dB from peak = f0/QL", r["bw3db_s11"] / 1e6, "MHz")
    r = qwt_ref()
    c = "QWT 50->100, f0=2G"
    _, s11, _ = qwt(np.array([2e9, 3e9, 4e9, 6e9]))
    row(c, "Zt = sqrt(50*100)", r["zt"], "Ohm")
    row(c, "S11 null frequencies", r["f0"] / 1e9, "GHz")
    row(c, "  and", r["f_null2"] / 1e9, "GHz")
    row(c, "|S11| at f0 (port 2 = 100 Ohm)", db(s11[0]), "dB")
    row(c, "|S11| at 1.5 f0 = 3 GHz", db(s11[1]), "dB")
    row(c, "|S11| at 2 f0 = 4 GHz (= |50-100|/150)", db(s11[2]), "dB")
    row(c, "fractional BW, |S11| < -20 dB", r["fbw"] * 100, "%")
    row(c, "  i.e. absolute BW", r["fbw"] * r["f0"] / 1e6, "MHz")
    row(c, "bare 50/50 ports: |S11(f0)| (=1/3)", db(r["s11_f0_bare_50_50"]), "dB")
    _, _, so = stub_lambda4(np.array([2e9]), "open")
    _, _, ss = stub_lambda4(np.array([2e9]), "short")
    row("lambda/4 open stub sh, 50 Ohm", "|S21| at f0 = 2 GHz", db(so[0]), "dB")
    row("lambda/4 short stub sh, 50 Ohm", "|S21| at f0 = 2 GHz", db(ss[0]), "dB")
    _, s11, s21 = tline(np.array([2e9]), 100, 180, 2e9, deg=True)
    row("lambda/2 TLIN 100 Ohm", "|S11| at f0 = 2 GHz", db(s11[0]), "dB")
    row("lambda/2 TLIN 100 Ohm", "angle S21 at f0", np.degrees(np.angle(s21[0])), "deg")
    _, _, s21 = thru_line(np.array([2e9]), 25e-3, 1.0)
    row("thru 50 Ohm, 25 mm, eeff=1", "angle S21 at 2 GHz (-beta L, wrapped)", np.degrees(np.angle(s21[0])), "deg")
    row("thru 50 Ohm, 25 mm, eeff=1", "-beta L unwrapped", -np.degrees(beta(2e9) * 25e-3), "deg")
    for name, h, er in (("FR4 er=4.4 H=1.6mm", 1.6e-3, 4.4), ("RO4003C er=3.55 H=0.508mm", 0.508e-3, 3.55)):
        w = ms_synthesis(50, h, er)
        z, ee = ms_analysis(w, h, er)
        eek = ms_eeff_kj(w, h, er, 2e9)
        lg, lgk = guided_wavelength(2e9, ee), guided_wavelength(2e9, eek)
        row(name, "50 Ohm W, Hammerstad-Jensen exact (T=0)", w * 1e3, "mm")
        row(name, "50 Ohm W, Wheeler closed form", ms_wh_wheeler(50, er) * h * 1e3, "mm")
        row(name, "Z0 of that W (HJ, round trip)", z, "Ohm")
        row(name, "eps_eff static (HJ)", ee)
        row(name, "eps_eff at 2 GHz (Kirschning-Jansen)", eek)
        row(name, "lambda_g at 2 GHz, static", lg * 1e3, "mm")
        row(name, "lambda/4 at 2 GHz, static", lg / 4 * 1e3, "mm")
        row(name, "lambda/4 at 2 GHz, KJ dispersive", lgk / 4 * 1e3, "mm")
    for name, h, er in (("FR4 er=4.4 H=1.6mm", 1.6e-3, 4.4), ("RO4003C er=3.55 H=0.508mm", 0.508e-3, 3.55)):
        w = ms_synthesis(50, h, er)
        c = name.split()[0] + " 50 Ohm open stub"
        l0 = stub_open_length(2e9, w, h, er)
        ln = stub_open_length(2e9, w, h, er, False, False)
        row(c, "dL Hammerstad-Bekkadal (USED for refs)", ms_open_end_dl(w, h, er) * 1e3, "mm")
        row(c, "dL Kirschning-Jansen-Koster", ms_open_end_dl(w, h, er, "kjk") * 1e3, "mm")
        row(c, "dL/h (HB)", ms_open_end_dl(w, h, er) / h)
        row(c, "stub L for notch at 2 GHz (dL + KJ eeff)", l0 * 1e3, "mm")
        row(c, "stub L naive (static eeff, no dL)", ln * 1e3, "mm")
        row(c, "naive length error vs corrected", 100 * (ln - l0) / l0, "%")
        row(c, "notch f of naive-length stub", stub_open_notch_f(ln, w, h, er) / 1e9, "GHz")
        row(c, "notch f of corrected stub (inverse)", stub_open_notch_f(l0, w, h, er) / 1e9, "GHz")
        pd = patch_design(2.4e9, h, er)
        c = name.split()[0] + " patch 2.4 GHz"
        row(c, "W", pd["w"] * 1e3, "mm")
        row(c, "L (cavity model)", pd["l"] * 1e3, "mm")
        row(c, "eeff (Balanis W/h>1)", pd["eeff"])
        row(c, "dL (Hammerstad, eeff above)", pd["dl"] * 1e3, "mm")
        row(c, "R_edge, Balanis G1/G12 (USED)", pd["r_edge"], "Ohm")
        row(c, "R_edge, 90 er^2/(er-1) (L/W)^2", pd["r_edge_simple"], "Ohm")
        row(c, "inset y0 for 50 Ohm (G1/G12 R_edge)", pd["y0"] * 1e3, "mm")
        row(c, "inset y0 for 50 Ohm (simple R_edge)", patch_inset(pd["r_edge_simple"], pd["l"]) * 1e3, "mm")
        row(c, "f_res(L) inverse", patch_f_res(pd["l"], pd["w"], h, er) / 1e9, "GHz")
        c = name.split()[0] + " 50 Ohm line 30 mm"
        for fq in (1e9, 2e9, 5e9):
            row(c, f"eeff KJ at {fq / 1e9:g} GHz", ms_eeff_kj(w, h, er, fq))
            row(c, f"S21 phase at {fq / 1e9:g} GHz (wrapped)", ms_s21_phase_deg(w, h, er, 30e-3, fq), "deg")
    for name, fn, p, vg in (("Curtice quadratic", curtice_quadratic, CURTICE_Q_P, 0.0),
                            ("Curtice cubic", curtice_cubic, CURTICE_C_P, 0.0),
                            ("Statz", statz, STATZ_P, 0.0),
                            ("MOSFET level 1", mosfet_level1, MOS1_P, 2.0),
                            ("Angelov", angelov, ANGELOV_P, 0.0)):
        row(name + " (example p)", f"Ids at Vgs={vg:g} V, Vds=3 V", fn(vg, 3.0, p)[0, 0] * 1e3, "mA")


if __name__ == "__main__":
    for i, name in enumerate(_self_check(), 1):
        print(f"PASS {i:2d}  {name}")
    print()
    _table()
