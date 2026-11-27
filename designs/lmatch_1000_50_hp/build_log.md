# Build log: lmatch_1000_50_hp

## Documents
- Schematic `v2_lmatch_1000_50_hp` (sweep on the schematic only: 1 to 150 MHz, 1 MHz step, 150 points)
- Graph `v2_lmatch_1000_50_hp_s`: DB(|S(1,1)|), DB(|S(2,1)|)

## Parts
- CAP.C1: C = 1.461e-11 F (14.61 pF)
- IND.L1: L = 7.303e-7 H (730.3 nH), shunt via add_shunt from C1:1, ground below
- PORT.P1: Z = 1000 Ohm, on C1:1
- PORT.P2: Z = 50 Ohm, on C1:2
- GND under L1:2

## Wires (schematic units)
- (-1000,0)-(0,0) P1 to node; (0,0)-(0,1000) node to L1:1
- (1000,0)-(2000,0) C1:2 to P2
- (0,2000)-(0,2500) L1:2 to GND
- C1:1 sits at (0,0), the node itself. Straight lines, no crossings, nothing over bodies.

## Result
No simulation errors. S11 / S21 (dB): 1 MHz -1.5e-7 / -74.50; 50 MHz -61.25 / -3.3e-6; 150 MHz -1.07 / -6.60. Matches theory predictions.

## Deviations
None. Skipped tidy_graph, set_graph_axis, arrange_windows as instructed.
