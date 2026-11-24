# rc_lpf fix log

## Round 1
Diagnosis: get_parameters showed C1 C = 4775 pF; build_log and theory say 477.5 pF. Build error (x10 slip), theory is right. Measured -6.532 dB at 1 MHz instead of 10 MHz confirmed it.
Change: C1 C 4775 pF -> 477.5 pF (one change).
Result: resimulated v2_rc_lpf_s, 0 errors. 100 kHz -3.522 dB, 10 MHz -6.532 dB, 100 MHz -23.566 dB, equal to theory.
Note: set_parameter with string '477.5' stored 4.775e14 pF (string treated as SI F, not display pF). Reset using numeric 4.775e-10.
