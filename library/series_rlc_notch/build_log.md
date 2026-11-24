# build_log rlc_notch
Docs: schematic v2_rlc_notch, graph v2_rlc_notch_s (DB(|S(2,1)|) of v2_rlc_notch).
Sweep (document=v2_rlc_notch only): 1e9 to 2.2e9 Hz, step 1e5 (12001 pts).

Parts (read back with get_parameters):
- L1 IND 100 nH, rot 270 (vertical), pin1 (0,0), pin2 (0,1000)
- C1 CAP 0.1 pF (add_shunt on L1:2)
- R1 RES 1 Ohm (add_shunt on C1:2), GND at its pin 2
- R2 RES 1e-6 Ohm, series, rot 0, pin1 (3000,0), pin2 (4000,0)
- P1 PORT 1, 50 Ohm, on L1:1 (above, (0,-1000))
- P2 PORT 2, 50 Ohm, on R2:2 at (5000,0)

Wires: L1:2-C1:1; C1:2-R1:1; R1:2-GND; L1:1-P1; R2:1-L1:1 (horizontal, straight); R2:2-P2.
Tidy: one vertical shunt column plus one straight horizontal line; no crossings, no wire through bodies.

Result: min S21 = -28.283 dB at 1.5915 GHz (theory -28.30); 1 GHz = -0.0032 dB (theory -0.0031). Status: 0 errors.

Deviation: theory.md has ports joined by a through wire. AWR rejects it ("Ports may not be connected together"), so a series 1e-6 Ohm resistor R2 sits between the node and port 2. Effect on S21 is negligible.
