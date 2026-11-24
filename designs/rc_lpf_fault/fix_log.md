# fix_log: rc_lpf_fault

## Round 1
Diagnosis: C1.C read back `4.775*1000` pF (4775 pF), 10x theory (477.5 pF). Corner moved to 1 MHz; S21 was -23.57 dB at 10 MHz and -43.5 dB at 100 MHz. Build error, theory correct (round 0 matched with 477 pF). Other parts and wiring unchanged.
Change: C1.C `4.775*1000` -> `4.775*100` (display units pF, expression so it cannot arrive as a number or text).
Read back: get_parameters C = `4.775*100` pF.
Result: re-simulated, 0 errors. 100 kHz -3.522 dB, 10 MHz -6.532 dB, 100 MHz -23.566 dB (theory -3.52 / -6.53 / -23.55).
