# rc_lpf build log
Documents: schematic `v2_rc_lpf`, graph `v2_rc_lpf_s`.

## Parts
- RES R1: R = 50 Ohm
- CAP C1: C = 477.5 pF (4.775e-10 F), shunt, pin 2 to GND
- PORT P1: Z = 50 Ohm, on R1:1
- PORT P2: Z = 50 Ohm, on R1:2 (same node as C1:1)
- GND on C1:2

## Wires
(-1000,0)-(0,0) P1 to R1:1; (1000,0)-(2000,0) R1:2 to P2; (1000,0)-(1000,1000) R1:2 to C1:1; (1000,2000)-(1000,2500) C1:2 to GND. No crossings, no wires over bodies.

## Sweep
Schematic-only, 10 kHz to 1 GHz, 51 log points (10 per decade, so 100 kHz, 10 MHz and 100 MHz are exact points).

## Graph
`v2_rc_lpf_s`: `v2_rc_lpf:DB(|S(2,1)|)`. The spec says measurement "S(2,1)" and I plotted it as dB.

## Simulation
0 errors. S21 is -3.522 dB at 100 kHz, -6.532 dB at 10 MHz and -23.566 dB at 100 MHz. These match theory.

## Deviations
None.
