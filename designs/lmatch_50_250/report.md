# Report: lmatch_50_250 (50 Ohm source to 250 Ohm load, 50 MHz)

**Verdict: PASS, round 0** (no fix needed). Not saved in AWR.

## Spec (approved 26 Nov 2026)
Match a 50 Ohm source to a 250 Ohm load at 50 MHz. No DC requirement stated, so a low-pass L-match was chosen (passes DC, rejects harmonics).

## Final design
- Series L1 = 318.31 nH from port 1 (50 Ohm), shunt C1 = 25.465 pF to ground at the load node, port 2 = 250 Ohm.
- Q = sqrt(250/50 - 1) = 2; series X = 100 Ohm, shunt X = 125 Ohm.
- Sweep 5 to 150 MHz, 1 MHz step (schematic only). Documents: `v2_lmatch_50_250`, graph `v2_lmatch_50_250_s`.

## Verdict table
| Goal | Spec | Predicted | Measured | Result |
|---|---|---|---|---|
| S11 at 50 MHz | <= -40 dB | -100 dB | -101.48 dB | PASS |
| S21 at 50 MHz | >= -0.05 dB | 0 dB | -3e-10 dB | PASS |
| S21 at 150 MHz | <= -10 dB | -17.18 dB | -17.18 dB | PASS |

The whole curve matches theory within 0.01 dB at the checked points (5 to 150 MHz). The flagged normalisation risk (S21 with unequal port impedances) did not occur: S21 is 0 dB at the match.

## Rounds
Theory, build, evaluate (check_spec and check_tidy ran), judge PASS, review (no MUST). No fix round.

## Graph
Axes: x 0 to 160 MHz, step 20; y -120 to 0 dB, step 20 (reaches the null). Marker on the S11 null at 50 MHz: -101.5 dB. Colour-blind-safe trace colours; the schematic and graph are shown side by side, each zoomed to fit.

## Open points
- -101 dB is a numerical null of an ideal lumped match; real parts (tolerance, parasitics) will not reach it.
- Parts are exact calculated values, not E-series.
