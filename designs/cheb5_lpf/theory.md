# cheb5_lpf theory

## Topology
Stepped-impedance (Richards/Ridley) low-pass: 5 alternating microstrip sections, low-Z (shunt C), high-Z (series L), low-Z, high-Z, low-Z. Chosen because the spec asks for MLIN-only circuit-level microstrip; symmetric, 5 lines, no stubs.
Rejected: open-stub LPF (needs Kuroda/transformers, wider, stub-junction errors); coupled-line/hairpin (bandpass type); lumped LC (not microstrip). No library block applies (library has only RC, bias, QWT, RLC notch).

## Method
g = 1.1468, 1.3712, 1.9750, 1.3712, 1.1468. Sections: low-Z with beta*l = g*ZL/50 (C), high-Z with beta*l = g*50/ZH (L), at fc = 2 GHz. Zh=110, Zl=20 Ohm picked by sweeping the cascade (script sim.py): ZL < 20 would need W > 6 mm; ZH 110 gives W = 0.215 mm (limit 0.2 mm). Lower ZL or higher ZH adds stopband margin but hits the width limits. Zh=100/Zl=20 gives -26.1 dB at 4 GHz, so 110/20 is better.

Widths (Hammerstad-Jensen Z0 with Hammerstad T=35 um effective-width correction; found by brentq):
- low-Z: W = 5.5 mm, Z = 19.99 Ohm, eeff(0) = 3.75, eeff(2 GHz, KJ) = 3.76 (zero-T Z would be 20.15)
- high-Z: W = 0.215 mm, Z = 109.8 Ohm, eeff(0) = 3.00, eeff(2 GHz) = 3.01 (zero-T Z would be 117.9, so T matters; if AWR ignores T in Z0 the high-Z line is 118 Ohm and S21(4 GHz) improves slightly)

Length formula L = (beta*l) / (2 pi f sqrt(eeff)/c): initial 5.63 / 8.57 / 9.70 / 8.57 / 5.63 mm. Then three symmetric lengths tuned in the cascade (Nelder-Mead, max worst margin of the three goals, in 0.7x-1.4x of initial, so well inside the fixer's 0.5x-2x bound) because real lines are not pure L/C (low-Z lines have series L, high-Z lines have shunt C).

## Final values (MLIN, in order port 1 to port 2)
| Part | W (m) | L (m) | Z (Ohm) |
|---|---|---|---|
| TL1 | 0.0055 | 0.00605 | 20 |
| TL2 | 0.000215 | 0.00865 | 110 |
| TL3 | 0.0055 | 0.0100 | 20 |
| TL4 | 0.000215 | 0.00865 | 110 |
| TL5 | 0.0055 | 0.00605 | 20 |

End/step corrections: MSTEP junction discontinuities between 0.215 mm and 5.5 mm are NOT in the prediction (lengths were not shortened for step C/L). Expect a few % shift in cutoff; if the Builder adds MSTEP, shorten the lines by roughly 0.1 to 0.3 mm each at the high-Z side (shunt step C adds to the wide section) or leave to the fixer. Easiest: no MSTEP, MLIN-to-MLIN directly (the spec marks MSTEP optional). Ports are 50 Ohm terminations at the line ends (PORT, Z=50), no feed lines needed; add no open-end corrections (none present).

## AWR parameters (all SI numbers, plain)
- MSUB: Er=4.4, H=0.0008, T=3.5e-5, TanD=0.02, Rho=1 (copper about 1.05 vs gold reference; loss effect < 0.02 dB), ErNom=4.4, Cond default (set 5.8e7 only if the model exposes it), Name e.g. MSUB.
- MLIN: W and L as in the table (e.g. W=0.0055, L=0.00605), Sub = the MSUB name.
- PORT: Z=50, ports P=1 and P=2 at the two outer line ends.
- Models expected: MSUB, MLIN, PORT (MSTEP optional, not used).

## Loss and model basis
Lossy ABCD (cosh/sinh) with alpha_d (Hammerstad dielectric, tanD=0.02), alpha_c = Rs/(Z W) for copper 5.8e7, KJ dispersion on eeff, no Z0 dispersion. Total loss at 1.8 GHz is about 0.72 dB for a 0.1 dB ripple prototype, mostly dielectric and the 0.215 mm conductor.

## Predictions (also in predictions.json)
Cascade at selected frequencies (S21 dB / S11 dB): 0.1 GHz -0.05 / -28.2; 1.0 -0.27 / -38.8; 1.8 -0.72 / -18.4; 2.0 -2.1 / -6.5; 3.0 -19.1; 4.0 -27.8; 5.0 -29.9; 6.0 -25.3.
- s21_pass: -0.72 dB (worst, at 1.8 GHz). Goal >= -1.0, margin 0.28 dB: MARGINAL. A 40 percent error in line loss would fail it. Also sensitive to the cutoff shift: the band edge at 1.8 GHz is on the skirt; a 3 percent cutoff shift moves it about 0.1 dB.
- s11_pass: -17.6 dB (worst near 1.43 GHz). Goal <= -12, margin 5.6 dB.
- s21_stop: -27.8 dB at 4 GHz. Goal <= -25, margin 2.8 dB. Sensitivity: MSTEP/T-effects and cutoff shift of 5 percent moves it about 1.5 dB. A mild stop-band resonance returns near 6 GHz (-25 dB), outside the goal.

## Risks
- s21_pass is the tightest. If it fails, the fixer should shorten the TL1/TL5 (low-Z) lengths slightly, which lowers loss and moves the cutoff up; lengths are bounded 0.5x-2x.
- No theory goal is unreachable.
- Reproduce: `uv run --with numpy --with scipy python designs/cheb5_lpf/final_check.py` (sim.py has the models).
