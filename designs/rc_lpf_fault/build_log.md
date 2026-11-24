# build_log: rc_lpf_fault

Documents: schematic `v2_rc_lpf_fault`, graph `v2_rc_lpf_fault_s`.

Parts (values passed as SI numbers):
- R1 RES, R=50 Ohm (read back 50 Ohm)
- C1 CAP, C=`4.775*100` pF = 477.5 pF (fix round 1; round 0 had been left at `4.775*1000`; read back confirmed), shunt via add_shunt from R1:2, GND at its pin 2
- P1 PORT number 1, 50 Ohm, on R1:1
- P2 PORT number 2, 50 Ohm, on R1:2

Wires: P1-R1:1 (-1000,0 to 0,0); R1:2-P2 (1000,0 to 2000,0); R1:2-C1:1 (1000,0 to 1000,1000); C1:2-GND (1000,2000 to 1000,2500). No crossings, no wires over bodies.

Sweep (schematic only, document=): 100 kHz to 1 GHz, 81 log points (20/decade; 100 kHz, 10 MHz, 100 MHz are exact points).

Graph v2_rc_lpf_fault_s: DB(|S(2,1)|) of v2_rc_lpf_fault.

Results (after fix round 1): 100 kHz -3.522 dB; 10 MHz -6.532 dB; 100 MHz -23.566 dB. Matches theory.md.
Simulation: 0 errors, status window clean.

Deviations from theory.md: none. From spec.md: the sweep starts at 100 kHz, not 10 kHz (lead note after the round-0 Judge: no goal is below 100 kHz, so no effect).
