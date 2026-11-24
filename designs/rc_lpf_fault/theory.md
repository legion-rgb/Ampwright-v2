# theory: rc_lpf_fault
Topology: series R=50 Ohm (port 1 to node OUT), shunt C OUT to ground, port 2 at OUT. Fixed by spec; alternatives (L-section, 2nd order) not needed for a first-order response.
Derivation: ABCD = [1+RY, R; Y, 1], Y=jwC. S21 = 2/(A+B/Z0+C*Z0+D) = 2/(3 + j*w*C*100).
DC: 2/3 -> -3.52 dB. Corner: C sees 50+50 || 50 = 33.33 Ohm, so C = 1/(2*pi*10e6*33.33) = 477.5 pF. Use 477 pF (470 pF E12 gives about -6.4 dB at 10 MHz, still within tol).
Values: R=50 Ohm, C=477 pF.
Predictions: 100 kHz -3.52 dB; 10 MHz -6.53 dB; 100 MHz -23.55 dB.
Models: MSUB not needed. RES (series), CAP (shunt), PORT x2 (50 Ohm), GND. Ideal lumped, no parasitics.
All goals reachable.
