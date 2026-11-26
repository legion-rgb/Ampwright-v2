# fn_rc_check theory

## Topology
Series R (port 1 to node N), shunt C (N to ground), port 2 on N. Ideal lumped parts. Alternatives rejected: shunt-R/series-C forms and L-sections (spec fixes a first-order RC with series R).

## Calculation
Source and load are 50 Ohm, R = 50 Ohm. Let Zp = 50 || C. Then V2/Vs = Zp/(100 + Zp), and S21 = 2*V2/Vs. This simplifies to:

S21 = (2/3) / (1 + j*w*tau), with tau = (50+50)||50 * C = 33.33 Ohm * C.

- DC: 20log(2/3) = -3.522 dB.
- -3 dB point relative to DC at w*tau = 1, so C = 1/(2*pi*1e9*33.333) = 4.775 pF. Use 4.775e-12 F (SI).
- |S21| = (2/3)/sqrt(1+x^2), with x = f/1 GHz.
  - 10 MHz: x = 0.01, -3.522 dB (loss from the pole is 0.0004 dB).
  - 1 GHz: -3.522 - 3.010 = -6.532 dB.
  - 10 GHz: -3.522 - 10*log10(101) = -3.522 - 20.043 = -23.57 dB.

## Values
R1 = 50 (SI Ohm), C1 = 4.775e-12 (SI F). Confirm with get_parameters (reads back 4.775 pF).

## Models expected
RES, CAP, PORT (x2), GND. Sweep 10 MHz to 10 GHz, step 10 MHz. Schematic v2_fn_rc_check, graph v2_fn_rc_check_s.

## Assumptions
Ideal parts, no parasitics. "-3 dB cutoff" is relative to the DC level (see spec.md). All three goals are reachable.
