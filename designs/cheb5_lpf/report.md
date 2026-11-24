# Report: cheb5_lpf (22 Nov 2026)

Spec: a 5th-order Chebyshev low-pass (0.1 dB ripple prototype), ripple-band edge 2 GHz, stepped-impedance microstrip on FR4 (Er 4.4, tan d 0.02, H 0.8 mm, 35 um Cu). User-approved 22 Nov.

Final values (MSUB `v2_MSUB`; MLINs from port 1 to port 2, W x L):
| line | Z | W | L |
|---|---|---|---|
| TL1 | 20 Ohm | 5.5 mm | 6.05 mm |
| TL2 | 110 Ohm | 0.215 mm | 8.65 mm |
| TL3 | 20 Ohm | 5.5 mm | 10.0 mm |
| TL4 | 110 Ohm | 0.215 mm | 8.65 mm |
| TL5 | 20 Ohm | 5.5 mm | 6.05 mm |

| goal | spec | theory | measured | result |
|---|---|---|---|---|
| s21_pass, worst 0.1-1.8 GHz | >= -1.0 dB | -0.72 | -0.683 | PASS (**marginal**, 0.32 dB) |
| s11_pass, worst 0.1-1.8 GHz | <= -12 dB | -17.6 | -17.55 | PASS |
| s21_stop, 4 GHz | <= -25 dB | -27.8 | -27.85 | PASS |

Rounds: PASS in round 0, with no fix. Measured values are within 0.05 dB of theory. Review: no MUST findings, and the tidy check is ok.

Open points:
- **Step discontinuities are not modelled.** The Judge suggested a step check. Plain MSTEP rejects the 0.039 width ratio (it needs >= 0.05), and the MSTEPX (EM) retry was stopped by the user before it ran (`mstep_check.md`). Real 25:1 steps usually pull the cutoff down, so the 0.32 dB passband margin is the risk. Before trusting this beyond circuit level, either run an EM check or widen the narrow line to >= 275 um (ratio >= 0.05) and retune with the optimizer.
- The check copy `v2_cheb5_lpf_mstep` (with `v2_MSUB2`) was left in AWR. AWR later showed no open project.
