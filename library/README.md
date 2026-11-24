# Verified block library

Passing designs, promoted with `checks/promote.py`. Theory reuses them; the Builder rebuilds from `build_log.md`.

| block | from design | what it does |
|---|---|---|
| [rc_lowpass_1st](rc_lowpass_1st/) | rc_lpf | First-order RC low-pass between 50 Ohm ports, corner 10 MHz (R 50 Ohm series, C 477.5 pF shunt) |
| [qw_transformer](qw_transformer/) | tl_qwt | Ideal quarter-wave TLIN, 50 to 100 Ohm at 2 GHz (Z0 70.71 Ohm, 90 deg) |
| [series_rlc_notch](series_rlc_notch/) | rlc_notch | Shunt series-RLC notch at 1591.55 MHz, -28.3 dB (100 nH, 0.1 pF, 1 Ohm), with the 1e-6 Ohm port spacer |
| [ne3508_bias_point](ne3508_bias_point/) | ne3508_bias | Renesas NE3508M04 DC bias: Vds 3 V, Id 20 mA at Vgs -0.314 V (vendor netlist) |
