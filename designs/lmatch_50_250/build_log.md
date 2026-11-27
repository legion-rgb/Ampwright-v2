# build_log: lmatch_50_250

## Documents
- Schematic `v2_lmatch_50_250` (new). Graph `v2_lmatch_50_250_s` (new).
- Other project document `Match_50_250` and its graph pre-exist (not mine, untouched).

## Parts (SI)
- IND.L1: L = 3.1831e-7 H (reads 318.31 nH)
- CAP.C1: C = 2.5465e-11 F (reads 25.465 pF), shunt, vertical (add_shunt, pin 1 up)
- GND below C1
- PORT.P1: P=1, Z=50
- PORT.P2: P=2, Z=250

## Wires (grid units)
- P1:1 (-1000,0) to L1:1 (0,0)
- L1:2 (1000,0) to P2:1 (2000,0)
- L1:2 (1000,0) down to C1:1 (1000,1000) (T junction at L1:2)
- C1:2 (1000,2000) to GND (1000,2500)
No crossings, no wire over a body or foreign pin.

## Sweep
`set_frequencies(document='v2_lmatch_50_250')`: 5 to 150 MHz, 1 MHz step, 146 points. Project sweep untouched.

## Graph
`v2_lmatch_50_250_s`: DB(|S(1,1)|), DB(|S(2,1)|) from v2_lmatch_50_250. Not formatted (tidy tools not loaded; lead formats).

## Results (simulate OK, 0 errors)
| f MHz | S11 dB | S21 dB |
|---|---|---|
| 5 | -3.57 | -2.51 |
| 25 | -5.08 | -1.61 |
| 50 | -101.5 | -3e-10 |
| 75 | -2.55 | -3.52 |
| 100 | -0.56 | -9.14 |
| 150 | -0.084 | -17.18 |
All match theory predictions. No S21 normalisation problem: S21 at 50 MHz is 0 dB with P2 Z=250.

## Deviations
None. add_shunt used for C1 (rotation 270 equivalent, vertical, pin 1 on top). Arrange_windows/tidy not run (not available).
