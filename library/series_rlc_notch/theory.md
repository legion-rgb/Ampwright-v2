# rlc_notch theory
Topology: 2 ports (50 Ohm) joined by a through wire; a series L-C-R branch from that node to ground (shunt notch). Rejected: parallel LC in series (bandpass, wrong function); a lossless L-C without R (S21 goes to -inf, spec fixes R=1).
Values (SI, pass as plain numbers): L=1e-7 H, C=1e-13 F, R=1 Ohm. No tuning needed; spec fixes them.
Formulas: Z=R+j(wL-1/(wC)); S21=2Z/(2Z+Z0).
- f0=1/(2*pi*sqrt(LC))=1.591549e9 Hz; Z=R -> S21=2/52 -> -28.30 dB.
- 1 GHz: X=628.32-1591.55=-963.2 Ohm; |S21|=|2Z|/|2Z+50|=0.99964 -> -0.0031 dB.
Sweep (schematic document only, document=v2_rlc_notch): 1e9 to 2.2e9, step 1e5 (1.2e3+1 points); 1591.55 MHz is within 0.05 MHz of a point, and 1 GHz is a point.
Note: notch is very narrow (Q=X0/R = 1000/1 -> 1 MHz-scale); 0.1 MHz grid yields value within ~0.1 dB at nearest point? Offset 0.05 MHz: X=2*Q-ish... dX=2*L*dw=2*1e-7*2pi*5e4=0.0628 Ohm, negligible vs 2R=2. Fine.
AWR models: PORT (x2), RES, IND, CAP, GND (shunt wiring; the Builder checks names with search_models). Graph v2_rlc_notch_s: DB(|S(2,1)|).
Assumptions: ideal lumped parts, no parasitics, no substrate.

*Lead note (21 Nov): the build adds a 1e-6 Ohm series R2 before port 2, because AWR rejects ports wired directly together. See the build_log.md deviation; the Judge found its effect on S21 is about 1e-7 dB.*
