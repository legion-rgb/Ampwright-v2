# rc_lpf theory
Topology: port1 -> series R 50 Ohm -> node (port2) with shunt C to ground. Spec fixes it; no alternative needed (L-section or pi would not be first order).
Calc: C sees Rth = 50 + 50 (source+R) in parallel with 50 load = 33.33 Ohm. C = 1/(2*pi*fc*Rth) = 1/(2*pi*1e7*33.333) = 477.5 pF.
DC S21 = 2*50/150 -> -3.522 dB. Corner = DC - 3.01 = -6.53 dB at 10 MHz.
ABCD check (numpy): 100 kHz -3.522, 10 MHz -6.532, 100 MHz -23.566 dB.
Builder values (SI): RES R=50 Ohm; CAP C=477.5e-12 F; PORT P1 Z=50 at R input, PORT P2 Z=50 at node with C; C other pin to GND.
Models: RES, CAP, PORT, GND (no MSUB, no lines; ideal lumped).
Sweep: log points 10 kHz..1 GHz needing exact 100 kHz, 10 MHz, 100 MHz. Use 10 pts/decade from 1e4: 1e4,...,1e9 steps 10^(0.1k) hit every decade exactly (5 decades x10 +1 = 51 pts). Else use a list sweep of explicit freqs incl. those three. Schematic sweep only, document v2_rc_lpf.
Assumptions: ideal parts, no parasitics. Tolerance C: +-0.5 pF shifts fc S21 by <0.005 dB.
All goals reachable.
