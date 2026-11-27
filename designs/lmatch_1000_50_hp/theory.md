# Theory: lmatch_1000_50_hp

## Topology
High-pass L-match: shunt L1 at port 1 (1000 Ohm side) to ground, series C1 from that node to port 2 (50 Ohm). Series C is the DC block; L1 is a DC short on the source side only, so no DC path reaches the load. Rejected: low-pass L (series L, shunt C) has a DC path to the load; pi/T add parts for no gain at a single frequency.

## Hand calculation
Q = sqrt(1000/50 - 1) = sqrt(19) = 4.3589
Shunt X_L = 1000/Q = 229.42 Ohm -> L1 = X/(2*pi*50e6) = 730.3 nH
Series X_C = Q*50 = 217.94 Ohm -> C1 = 1/(2*pi*50e6*217.94) = 14.61 pF
Check: Z of C1+50 = 50 - j217.94; parallel with j229.42 gives 1000 Ohm real.

## Values (SI)
L1 = 7.303e-7 H, C1 = 1.461e-11 F. Ports: P1 = 1000 Ohm, P2 = 50 Ohm (S-params referenced to each port Z; if the build uses 50 Ohm refs everywhere, S11/S21 differ, so tell the Builder to set port Z).

## Predictions (python ABCD, rf-style, ports 1000/50, ideal parts)
f MHz: S11 dB / S21 dB
1: -0.00 / -74.5
10: -0.00 / -34.1
25: -0.11 / -16.2
50: below -80 (numerically ~ -300; rounded parts -61) / 0.00
75: -2.35 / -3.79
100: -1.44 / -5.49
150: -1.07 / -6.60

## DC-block argument
At f->0, C1 is open (S21 -> -inf), L1 shorts port 1 to ground. Port 2 only connects through C1, so there is no DC path from source to load. At 1 MHz S21 = -74.5 dB (spec said about -70; goal needs <= -50).

## AWR models expected
CAP, IND, PORT (P1 Z0=1000, P2 Z0=50), GND. No library block fits.
