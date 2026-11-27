# lmatch_50_250: L-match, 50 Ohm source to 250 Ohm load, 50 MHz

Task (user, 26 Nov 2026): design a matching network for a source resistance of 50 Ohm and a load resistance of 250 Ohm at 50 MHz.

Assumptions (the task states no DC requirement, so I chose):
- **Low-pass L-match**: series L from the source, shunt C across the load (the shunt part goes on the higher-resistance side, here the load). It passes DC and also suppresses harmonics. A high-pass version would need a stated reason (DC block), and there is none.
- Ideal lumped parts, no losses, no parasitics.
- Port 1 = source side, 50 Ohm. Port 2 = load side, 250 Ohm.

Expected by hand: Q = sqrt(250/50 - 1) = 2. Series X = Q * 50 = 100 Ohm, so L = 318.3 nH. Shunt X = 250 / Q = 125 Ohm, so C = 25.47 pF.
At 50 MHz: S11 is a deep null (numerically below -80 dB), S21 = 0 dB (all available power reaches the load). At 150 MHz S21 is about -17 dB (low-pass).

Sweep: 5 to 150 MHz, 1 MHz step, so 50 MHz is an exact point (schematic sweep only, `document=v2_lmatch_50_250`).
Documents: schematic `v2_lmatch_50_250`, graph `v2_lmatch_50_250_s` with `DB(|S(1,1)|)` and `DB(|S(2,1)|)`.

Graphs: the axes must reach the deepest dip (rule "Graph scaling" in CLAUDE.md), with a marker on the S11 null at 50 MHz.

Approved by the user: 26 Nov 2026, as written.
