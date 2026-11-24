# ne3508_bias report

Spec: NE3508M04 at Id = 20 mA, Vds = 3 V, source grounded (user-approved 21 Nov 2026). Vgs from a search, because theory's estimate was off.
Final: Vgs = -0.314 V (equation `Vgs` in `v2_ne3508_bias`). Device: Renesas `NE3508M04_v124.net`, imported as `v2_ne3508_bias_dev`. Graph `v2_ne3508_bias_iv`: IDC(DCVSS.VD), APLAC DC, Vds 0 to 4 V. Not saved.

| Goal | Spec | Predicted | Measured | Verdict |
|---|---|---|---|---|
| id @ Vds = 3 V | 20 +/- 1 mA | 20 mA after the Vgs trim | 19.964 mA | PASS |

Vgs search at Vds = 3 V: -0.100 V gives 79.7 mA, -0.300 V gives 22.91 mA, -0.320 V gives 18.76 mA, -0.314 V gives 19.96 mA.
Rounds: 0 fixes. The Judge checked the wiring and the curve shape. Id rises with Vds (6.6, 12.2, 20.0, 29.9 mA at 1 to 4 V) because the device is near pinch-off (EEHEMT Gamma and Kapa), and the Judge's own hand estimate follows the same shape. Review: no MUST findings, check_tidy ok.
Open: the bias sits close to pinch-off, so Id is sensitive to Vds (about 8.5 mA/V) and to Vgs (about 200 mA/V). This is fine for the spec, but a real bias network would want a higher Vgs at a lower Vds, or a drain resistor.
Playbook: EEHEMT pinch-off line added.
