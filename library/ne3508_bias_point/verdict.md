VERDICT: PASS

| goal | spec | predicted | measured | result |
|---|---|---|---|---|
| id (Id at Vds=3 V, Vgs=-0.314 V) | 20.0 mA +/- 1 mA | 20.0 mA (searched) | 19.964 mA (graph_data, own read) | PASS |

Most important reason: the measured 19.96 mA is within 20 +/- 1 mA, and the circuit is the one the spec describes. The APLAC netlist (mwo_aplac_netlist.i) shows `Volt VG 1 0 DC=-0.314` on the node that reaches the EEHEMT gate through Lg1/Lg, `Volt VD 2 0` swept on the node that reaches the drain through Ld2/Ld, and the source going to ground through Ls. There are no extra series resistors: only the intrinsic Rd/Rs/Rg. IDC(DCVSS.VD) is the drain current (positive, 0 at Vds=0).

Lead's concern (no saturation): this is how the model behaves, not a build fault. Vgs=-0.314 V is only 0.19 V above Vto=-0.508 V, so the device sits in the EEHEMT sine-shaped near-pinch-off region (between Vto and Vgo). There, Gamma=0.0198 shifts the effective Vgs by Gamma*(Vds-Vdso), up to 0.08 V over the 0..4 V sweep. That is a large share of the 0.19 V overdrive, and on top of it comes Kapa=0.123/V. My hand estimate with Ids0 = Gmmax/2*[(V-Vto) - (Vgo-Vto)/pi*sin(pi(V-Vto)/(Vgo-Vto))], V = Vgs + Gamma*(Vds-Vdso), times (1+Kapa*Vds): 9.8, 14.8, 21.3 and 29.5 mA at 1, 2, 3 and 4 V. The measured values are 6.6, 12.2, 20.0 and 29.9 mA. The upward-curving slope matches; my estimate leaves out Peff self-heating and Vch. The knee is near 0.3-0.4 V. The 20 Nov demo (20.36 mA at Vgs=0, Vds=0.1 V) is a linear-region point at a much higher gate drive, so it is consistent: Ron is about 5 Ohm, and Id at Vgs=-0.1 V, Vds=3 V is 79.7 mA.

Prediction gap: theory.md guessed Vgs near -0.1 V and a flat Id; the build found -0.314 V. The theory is wrong: it ignored Gamma and Kapa near pinch-off. The build is fine. The Id goal itself has no gap, because it was found by search.

Schematic vs build_log: X1 (SUBCKT, v2_ne3508_bias_dev, UgwNew=0.8, NfgNew=1), VG (DCVS, V=Vgs), VD (DCVSS 0..4 V, 0.1 V step) and three GND. The parts and the five wires match the log exactly, with no undocumented parts. The wires are straight with no crossings.

Status: the last AP_DC run is info only (Begin/End Simulate, 41 points), with no errors or warnings.

Open point (not a fail): the bias point is close to pinch-off, so Id is sensitive to Vgs (about 0.2 mA/mV) and to Vds (about 0.9 mA/V at 3 V).

> Lead note (21 Nov): the "0.9 mA/V" figure is 10x low; the data give about 8.5 mA/V. The verdict is unaffected.
