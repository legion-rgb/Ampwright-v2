VERDICT: PASS

| goal | spec | predicted | measured | result |
|---|---|---|---|---|
| s11_f0 (2 GHz) | <= -40 dB | <= -100 dB (null) | -191.57 dB | PASS |
| s11_band (1.75-2.25 GHz worst) | <= -20 dB | -23.2 dB | -23.25 dB (at both edges) | PASS |
| s11_2f0 (4 GHz) | -9.54 +/- 0.1 dB | -9.54 dB | -9.542 dB | PASS |

Most important reason: all three goals meet spec with margin, and measured matches theory to within 0.05 dB (no prediction gap). Re-checked independently with graph_data on `v2_tl_qwt_s` (27 points, one measurement `DB(|S(1,1)|)`); trace is symmetric about 2 and 6 GHz as expected for an ideal quarter-wave line.

Band sampling (only 3 points, 1.75/2.0/2.25 GHz): enough evidence. For a single ideal TLIN between resistive ports, |S11| rises monotonically from the 2 GHz null to each side within the 1.75-2.25 GHz band (|Gamma| grows with |cos(theta)|, theta 78.75-101.25 deg), so the in-band worst case sits exactly at the band edges, and both edges are sampled points. A denser sweep could not show a higher in-band value.

Schematic check: list_elements shows exactly TL1 (TLIN, Z0 70.7106781 Ohm, EL 90 Deg, F0 2 GHz), P1 (50 Ohm, net 1 = TL1:1), P2 (100 Ohm, net 2 = TL1:2). Matches build_log.md; no undocumented parts. EL entered as '90' in display degrees is documented as a deviation and reads back as 90 Deg; results confirm it is correct.

Status window: only info messages for LIN:v2_tl_qwt (Begin Simulate, 27 points, End Simulate). No errors or warnings.

Fixer: nothing to fix.
