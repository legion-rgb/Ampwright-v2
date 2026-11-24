# cheb5_lpf: 5th-order Chebyshev low-pass, 2 GHz, microstrip on FR4

Task: a 5th-order Chebyshev low-pass filter (0.1 dB ripple prototype) between two 50 Ohm ports, with the ripple-band edge at 2 GHz, built as a stepped-impedance microstrip filter on FR4. This is a circuit-level design (MSUB, MLIN, and MSTEP if Theory wants it), not an EM design.

Board: FR4, Er 4.4, tan d 0.02, H 0.8 mm, copper T 35 um. Lines no narrower than 0.2 mm and no wider than 6 mm.

Expected by hand: the 0.1 dB, n = 5 prototype gives g = 1.1468, 1.3712, 1.9750, 1.3712, 1.1468. The ideal attenuation at 4 GHz is about 35 dB. Stepped-impedance sections and FR4 loss reduce that margin, so the goals below leave room for it.

Goals:
- Passband |S21| >= -1.0 dB from 0.1 to 1.8 GHz (FR4 loss included).
- Passband |S11| <= -12 dB from 0.1 to 1.8 GHz.
- Stopband |S21| <= -25 dB at 4 GHz.

Sweep: 0.1 to 6 GHz in 10 MHz steps, set on the schematic only with `document=v2_cheb5_lpf`.
Documents: schematic `v2_cheb5_lpf`, and graph `v2_cheb5_lpf_s` holding `DB(|S(2,1)|)` and `DB(|S(1,1)|)`.
Fixer: may use the optimizer on the line lengths, bounded to 0.5x to 2x of theory.

Approved by the user: 22 Nov 2026 ("approve the cheb5 spec, run it here").
