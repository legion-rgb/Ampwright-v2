VERDICT: PASS

| goal | spec | predicted | measured | result |
| --- | --- | --- | --- | --- |
| s11_f0 (S11 at 50 MHz) | <= -40 dB | -100 dB (exact parts); -61 dB (rounded parts, theory.md) | -61.25 dB | PASS (21 dB margin) |
| s21_f0 (S21 at 50 MHz) | >= -0.05 dB | 0.00 dB | -3.3e-6 dB | PASS |
| s21_dcblock (S21 at 1 MHz) | <= -50 dB | -74.5 dB | -74.50 dB | PASS |

Most important reason: all three goals are met, and the measured values match theory. The live graph (graph_data, 150 points, 1 to 150 MHz) shows the S11 minimum at exactly 50 MHz (-61.25 dB) and S21 at 1 MHz = -74.50 dB.

## Prediction gap on s11_f0 (-100 vs -61.25 dB): explained rounding, not a real discrepancy
- The headline number in predictions.json (-100 dB) is for exact L and C. The same file's basis field and theory.md (line 20) both give -61 dB for the rounded values. The build used the rounded values (730.3 nH, 14.61 pF), as theory.md said to.
- Independent check: exact C = 14.605 pF, so 14.61 pF is +3.4e-4 high. Exact L = 730.26 nH, so 730.3 nH is +4e-5 high. The C error moves the series reactance by about 0.074 Ohm. Seen from the 1000 Ohm node, that is a susceptance error of about 1.5e-6 S against G = 1e-3 S, so |Gamma| is about 7.5e-4, or about -62 dB. That is within about 1 dB of the -61.25 dB measured.
- So theory is right for the parts that were built, and the build is right. The -100 dB figure is a numerical idealisation that no 4-digit part value can reach. It is not a build fault. A depth of -61 dB is far below the -40 dB spec.
- The other goals are within 0.01 dB of theory. Theory gives 75 MHz -2.35 / -3.79 dB and 150 MHz -1.07 / -6.60 dB; the live data shows -2.349 / -3.791 and -1.074 / -6.595.

## Schematic vs build_log.md
- The parts match exactly: CAP.C1 14.61 pF; IND.L1 730.3 nH (shunt, node to GND); PORT.P1 Z = 1000 Ohm on the C1:1 node; PORT.P2 Z = 50 Ohm on C1:2; one GND. No undocumented parts.
- The 4 wires match the log's coordinates. They are straight, with no crossings and nothing running over a part body.
- The topology fits the spec: a series C is the only path to the load, so DC is blocked.

## Status messages
The last simulation of LIN:v2_lmatch_1000_50_hp ran with no errors or warnings: Begin, Freq 150 points, End.

## For the Fixer
Nothing to fix. Optional: if the lead wants the prediction file to agree with the build, set the s11_f0 predicted value to -61 dB (rounded parts) instead of -100 dB.
