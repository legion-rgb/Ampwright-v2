# rc_lpf_fault: first-order RC low-pass, 10 MHz

Task: a series-R, shunt-C low-pass between two 50 Ohm ports, with its corner (3 dB below the DC level) at 10 MHz.

Fixed by the spec: R = 50 Ohm in series from port 1; C from the output node (port 2) to ground; 50 Ohm ports. Theory picks C.

Expected by hand: DC S21 = 20log(2*50/150) = -3.52 dB. The C sees (50+50)||50 = 33.3 Ohm, so C is about 477 pF.
At 10 MHz S21 = -6.53 dB; at 100 MHz about -23.6 dB.

Sweep: 10 kHz to 1 GHz, log, with 100 kHz, 10 MHz and 100 MHz as exact points (schematic sweep only, `document=v2_rc_lpf_fault`).
Documents: schematic `v2_rc_lpf_fault`, graph `v2_rc_lpf_fault_s` with `DB(|S(2,1)|)`.

Approved by the user: 21 Nov 2026 (eval task).
