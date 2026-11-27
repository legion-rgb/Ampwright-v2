# theory: lmatch_50_250

Topology: low-pass L-match, port 1 (50 Ohm) - series L - node - shunt C to ground - port 2 (250 Ohm). Shunt part on the high-R side (load). Rejected: high-pass (series C, shunt L): no DC need, no harmonic rejection; pi/T networks: more parts, no need for extra Q.

## Calculation
Q = sqrt(Rh/Rl - 1) = sqrt(250/50 - 1) = 2
Xs = Q*Rl = 100 Ohm -> L = Xs/(2 pi f) = 100/(2 pi 50e6) = 318.31 nH
Xp = Rh/Q = 125 Ohm -> C = 1/(2 pi f Xp) = 25.465 pF
Check: Zin = jXs + (250 || -j125) = j100 + (50 - j100) = 50 Ohm.

Values to use (SI): L = 3.1831e-7 H, C = 2.5465e-11 F (rounded 318.3 nH / 25.47 pF gives S11 about -74 dB at 50 MHz, still passes).

## Predictions (ideal parts; S21 = transducer gain, ports 50 and 250 Ohm)
| f MHz | S11 dB | S21 dB |
|---|---|---|
| 5 | -3.57 | -2.51 |
| 25 | -5.08 | -1.61 |
| 50 | < -70 (null) | 0.00 |
| 75 | -2.55 | -3.52 |
| 100 | -0.56 | -9.14 |
| 150 | -0.08 | -17.18 |

At 5 MHz the network is nearly transparent, so S11 tends to the 50/250 mismatch (S11 -3.52 dB, S21 -2.55 dB) as f -> 0.

## Assumption / risk
S21 with unequal port Z: AWR PORT uses its own impedance (set P2 Z = 250) and reports power-wave-like S21 if the sweep is set so; if AWR reports a voltage-normalised S21 the magnitudes differ by sqrt(Z ratio) = 7 dB. Builder: set port 2 Z=250 and compare S21 at 50 MHz to 0 dB; if off, report to lead.
At 50 MHz S11 is a numerical floor, so judge it only against -40.

## AWR models
PORT (P1 Z=50, P2 Z=250), IND (L=3.1831e-7), CAP (C=2.5465e-11, shunt, rotation 270), GND.
