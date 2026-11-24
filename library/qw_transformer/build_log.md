# tl_qwt build log

Documents: schematic `v2_tl_qwt`, graph `v2_tl_qwt_s` (only `v2_tl_qwt:DB(|S(1,1)|)`).

Parts (read back with get_parameters):
- TLIN.TL1: Z0 = 70.7106781 Ohm, EL = 90 Deg, F0 = 2 GHz
- PORT.P1: P=1, Z=50 Ohm, on TL1:1
- PORT.P2: P=2, Z=100 Ohm, on TL1:2

Wires: (0,0)-(-1000,0) TL1:1 to P1; (1000,0)-(2000,0) TL1:2 to P2. Straight, no crossings, none over bodies.

Sweep: schematic-only (document=v2_tl_qwt), 0.5 to 7 GHz, step 0.25 GHz, 27 points (2 and 4 GHz exact).

Results: S11 at 2 GHz -191.6 dB; 1.75/2.25 GHz -23.25 dB; 4 GHz -9.542 dB. Sim: 0 errors, status window empty.

Deviations: EL sent as string '90' (display deg) instead of radians 1.5707963; reads back exactly 90 Deg. Otherwise none.
