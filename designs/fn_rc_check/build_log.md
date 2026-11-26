# fn_rc_check build log

Documents: schematic `v2_fn_rc_check` (pre-existing, emptied and rebuilt), graph `v2_fn_rc_check_s` (pre-existing, measurement deleted and re-added). No new documents.

## Parts
- R1 RES: R = 50 Ohm
- C1 CAP: C = 4.775e-12 F (reads back 4.775 pF), hung below R1:2 via add_shunt
- GND: on C1:2
- P1 PORT: P=1, Z=50, on R1:1
- P2 PORT: P=2, Z=50, on R1:2

## Wires
- P1:1 to R1:1 (0,0)-(-1000,0)
- R1:2 to P2:1 (1000,0)-(2000,0)
- R1:2 to C1:1 (1000,0)-(1000,1000)
- C1:2 to GND (1000,2000)-(1000,2500)
All straight, no crossings, none over bodies.

## Sweep
Set on schematic only (document=v2_fn_rc_check): 10 MHz to 10 GHz, step 10 MHz (1000 points).

## Graph
v2_fn_rc_check_s: v2_fn_rc_check:DB(|S(2,1)|).

## Result
Simulated, 0 errors. 10 MHz -3.522 dB, 10 GHz -23.566 dB (matches theory).

## Deviations
None.
