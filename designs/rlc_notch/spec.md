# rlc_notch: shunt series-RLC notch between 50 Ohm ports

Task: a series L-C-R branch from the through line to ground, between two 50 Ohm ports. The spec fixes L = 100 nH, C = 0.1 pF and R = 1 Ohm.

Known answer: f0 = 1/(2*pi*sqrt(LC)) = 1591.55 MHz. S21 at f0 is 20log(2R/(2R+50)) = -28.30 dB, and S21 at 1 GHz is -0.003 dB.

Sweep: 1 to 2.2 GHz, fine enough that 1591.55 MHz is within 0.1 MHz of a sweep point. Set it on the schematic only, with `document=v2_rlc_notch`.

Documents: schematic `v2_rlc_notch`, and graph `v2_rlc_notch_s` holding `DB(|S(2,1)|)` only.

Approved by the user: 21 Nov 2026 (eval task).
