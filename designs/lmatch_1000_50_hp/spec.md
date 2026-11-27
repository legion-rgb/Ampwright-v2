# lmatch_1000_50_hp: AC-coupled L-match, 1000 Ohm source to 50 Ohm load, 50 MHz

Task (user, 26 Nov 2026): design a matching network for a source resistance of 1000 Ohm and a load resistance of 50 Ohm at 50 MHz. Assume only AC voltage can be transferred to the load.

Reading of "only AC": the load must not see DC, so the path to the load needs a **series capacitor** (a DC block). That makes the match **high-pass**: shunt L across the source side (the higher-resistance side), series C into the load. The shunt L is a DC short on the source side, so no DC reaches the load.

Assumptions:
- Ideal lumped parts, no losses, no parasitics.
- Port 1 = source side, 1000 Ohm. Port 2 = load side, 50 Ohm.
- S-parameters cannot test DC directly. DC blocking is checked by structure (series C, no DC path) and by S21 at 1 MHz, far below the band.

Expected by hand: Q = sqrt(1000/50 - 1) = 4.359. Shunt X = 1000 / Q = 229.4 Ohm, so L = 730.3 nH. Series X = Q * 50 = 217.9 Ohm, so C = 14.61 pF.
At 50 MHz: S11 is a deep null (numerically below -80 dB), S21 = 0 dB. At 1 MHz S21 is about -70 dB (high-pass).

Sweep: 1 to 150 MHz, 1 MHz step, so 1 MHz and 50 MHz are exact points (schematic sweep only, `document=v2_lmatch_1000_50_hp`).
Documents: schematic `v2_lmatch_1000_50_hp`, graph `v2_lmatch_1000_50_hp_s` with `DB(|S(1,1)|)` and `DB(|S(2,1)|)`.

Graphs: the axes must reach the deepest dip (rule "Graph scaling" in CLAUDE.md), with a marker on the S11 null at 50 MHz.

Approved by the user: 26 Nov 2026, as written.
