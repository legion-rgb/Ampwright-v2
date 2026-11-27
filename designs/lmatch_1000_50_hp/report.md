# Report: lmatch_1000_50_hp (1000 Ohm source to 50 Ohm load, 50 MHz, AC only)

**Verdict: PASS, round 0** (no fix needed). Not saved in AWR.

## Spec (approved 26 Nov 2026)
Match a 1000 Ohm source to a 50 Ohm load at 50 MHz, with only AC voltage reaching the load. A series capacitor blocks DC, so the match is high-pass: shunt L across the source side, series C into the load.

## Final design
- Shunt L1 = 730.3 nH to ground at port 1 (1000 Ohm), series C1 = 14.61 pF to port 2 (50 Ohm).
- Q = sqrt(1000/50 - 1) = 4.359; shunt X = 229.4 Ohm, series X = 217.9 Ohm.
- Sweep 1 to 150 MHz, 1 MHz step (schematic only). Documents: `v2_lmatch_1000_50_hp`, graph `v2_lmatch_1000_50_hp_s`.
- DC block: C1 is the only path to the load, so no DC reaches it. S-parameters cannot test DC, so the check is S21 at 1 MHz.

## Verdict table
| Goal | Spec | Predicted | Measured | Result |
|---|---|---|---|---|
| S11 at 50 MHz | <= -40 dB | -100 dB (exact parts), -61 dB (rounded) | -61.25 dB | PASS |
| S21 at 50 MHz | >= -0.05 dB | 0 dB | -3e-6 dB | PASS |
| S21 at 1 MHz (DC block) | <= -50 dB | -74.5 dB | -74.50 dB | PASS |

The S11 gap to -100 dB is rounding, not a defect: the build used 730.3 nH and 14.61 pF, and 14.61 pF is 3.4e-4 above the exact 14.605 pF. That alone gives about -62 dB, in line with the measured -61.25 dB. Exact values (730.25 nH, 14.605 pF) would give a much deeper null.

## Rounds
Theory, build, evaluate (check_spec and check_tidy ran), judge PASS, review. No fix round.

## Graph
Axes: x 0 to 160 MHz, step 20; y -80 to 0 dB, step 10 (reaches the -74.5 dB S21 at 1 MHz). Marker on the S11 null at 50 MHz: -61.3 dB. Colour-blind-safe trace colours; schematic and graph side by side, each zoomed to fit.

## Open points
- The null is -61 dB with the rounded parts. Say if you want the exact values for a deeper demo null.
- Parts are not E-series values.
