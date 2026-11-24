VERDICT: FAIL

| goal | spec | predicted | measured | result |
| --- | --- | --- | --- | --- |
| s21_dc (S21 @ 100 kHz) | -3.52 +/- 0.05 dB | -3.52 dB | -3.565 dB | PASS (margin 0.005 dB) |
| s21_fc (S21 @ 10 MHz) | -6.53 +/- 0.25 dB | -6.53 dB | -23.566 dB | FAIL (17.0 dB off; prediction gap) |
| s21_stop (S21 @ 100 MHz) | <= -22 dB | -23.55 dB | -43.523 dB | PASS (but 20 dB prediction gap) |

Most important reason: C1 in the schematic is `4.775*1000` pF = 4775 pF, ten times the 477 pF that theory.md and build_log.md give. The corner moved from 10 MHz to 1 MHz: graph_data(summary=true) on `v2_rc_lpf_fault_s` gives -6.532 dB at 1 MHz, -23.566 dB at 10 MHz and -43.523 dB at 100 MHz, which is the predicted curve shifted down one decade. The build is wrong, not the theory: the theory numbers matched AWR exactly in round 0 with 477 pF.

Checks:
- Prediction gap: s21_fc is 17.0 dB off and s21_stop is 20.0 dB off (both over 3 dB). s21_dc is 0.045 dB lower than predicted, also from the larger C (wC*33.3 Ohm = 0.3 at 100 kHz instead of 0.03). It is still inside the tolerance.
- Schematic vs build_log.md: the parts and nets match (R1 50 Ohm, C1 shunt with pin 2 to GND, P1/P2 50 Ohm, nets 3/1/2). The C1 value does not: build_log says 4.77e-10 (477 pF read back), but the schematic holds `4.775*1000` pF. The log is stale or the value was changed without being logged. No undocumented parts.
- Status window: info messages only for LIN:v2_rc_lpf_fault (81 points), no errors or warnings.

For the Fixer: set C1.C to about 477 pF with an expression in display units, e.g. `'4.775*100'` (= 477.5 pF), per the playbook. Do not use `'4.775*1000'` (4775 pF), and do not send a bare `'477.5'`, which the playbook warns can arrive as a number (477.5 F). Confirm with get_parameters (expect 477.5 pF), re-simulate, and update build_log.md with the value actually stored.
