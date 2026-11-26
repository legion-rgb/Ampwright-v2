# fn_rc_check: first-order RC low-pass, 1 GHz

Task (user, 25 Nov 2026): an RC low-pass filter, -3 dB cutoff 1 GHz, 50 Ohm source and load, lumped R and C.

Assumptions (for the user to confirm):
- Topology: series R from port 1, shunt C from the output node (port 2) to ground. Ideal lumped RES and CAP.
- R = 50 Ohm (as in rc_lpf). Theory picks C.
- "-3 dB cutoff" means 3 dB below the passband (DC) level. With a 50 Ohm series R the passband is already -3.52 dB, so absolute S21 = -3 dB at 1 GHz is not possible with this topology.

Expected by hand: DC S21 = 20log(2*50/150) = -3.52 dB. The C sees (50+50)||50 = 33.3 Ohm, so C = 1/(2*pi*1e9*33.3) = 4.775 pF.
At 1 GHz S21 = -6.53 dB; at 10 GHz about -23.6 dB.

Sweep (proposed, schematic only, `document=v2_fn_rc_check`): 10 MHz to 10 GHz, linear, step 10 MHz (1000 points), so 10 MHz, 1 GHz and 10 GHz are exact points.
Documents: schematic `v2_fn_rc_check`, graph `v2_fn_rc_check_s` with `DB(|S(2,1)|)`.

Goals:
| id | at | goal |
|---|---|---|
| s21_dc | 10 MHz | S21 = -3.52 dB +/- 0.05 |
| s21_fc | 1 GHz | S21 = -6.53 dB +/- 0.25 (3 dB below DC) |
| s21_stop | 10 GHz | S21 <= -22 dB |

Approved by the user: yes, 26 Nov 2026 ("run the full loop, don't save").
