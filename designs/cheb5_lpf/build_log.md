# cheb5_lpf build log

## Documents
- Schematic `v2_cheb5_lpf` (own sweep 0.1 to 6 GHz, 10 MHz step, 591 points, set with document=).
- Graph `v2_cheb5_lpf_s` (rectangular): `v2_cheb5_lpf:DB(|S(2,1)|)` and `v2_cheb5_lpf:DB(|S(1,1)|)`.
- No netlists, no EM structures.

## Parts (all values passed as SI numbers, read back with get_parameters)
| Part | Model | Parameters (read back) |
|---|---|---|
| v2_MSUB | MSUB | Er 4.4, H 800 um, T 35 um, Rho 1, Tand 0.02, ErNom 4.4, Name v2_MSUB |
| TL1 | MLIN | W 5500 um, L 6050 um, MSUB v2_MSUB |
| TL2 | MLIN | W 215 um, L 8650 um, MSUB v2_MSUB |
| TL3 | MLIN | W 5500 um, L 10000 um, MSUB v2_MSUB |
| TL4 | MLIN | W 215 um, L 8650 um, MSUB v2_MSUB |
| TL5 | MLIN | W 5500 um, L 6050 um, MSUB v2_MSUB |
| P1 | PORT | P 1, Z 50 Ohm |
| P2 | PORT | P 2, Z 50 Ohm |

## Wires (x, y in schematic units; all on y = 0, one straight row)
- P1 pin (2000,0) to TL1:1 (3000,0)
- TL1:2 (4000,0) to TL2:1 (6000,0)
- TL2:2 (7000,0) to TL3:1 (9000,0)
- TL3:2 (10000,0) to TL4:1 (12000,0)
- TL4:2 (13000,0) to TL5:1 (15000,0)
- TL5:2 (16000,0) to P2 pin (17000,0)
Tidy: single straight line, no crossings, no wire over a body or pin. MSUB sits off the signal row.

## Simulation
Ran with simulate(graph=v2_cheb5_lpf_s): 0 errors, status window empty.

## Goal values (from graph data)
- s21_pass: min DB(S21) over 0.1 to 1.8 GHz = -0.683 dB at 1.8 GHz (goal >= -1.0): pass.
- s11_pass: worst DB(S11) over 0.1 to 1.8 GHz about -17.55 dB near 1.43 GHz (goal <= -12): pass.
- s21_stop: DB(S21) at 4 GHz = -27.85 dB (goal <= -25): pass.
(Theory predicted -0.72 / -17.6 / -27.8.)

## Deviations from theory.md
- MSUB takes no ID; its name is the `Name` parameter, set to `v2_MSUB` (default was SUB1). MLIN `MSUB` parameter points to it.
- Sweep 0.1 to 6 GHz at 10 MHz per spec.md (theory.md gave none).
- No MSTEP, as theory.md recommends. Cond/Rho left at Rho = 1 as in theory.
