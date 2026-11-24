# ne3508_bias build log

## Documents
- `v2_ne3508_bias_dev`: netlist imported (import_netlist) from the text of NE3508M04_v124.net (read only, from the AWR library). Subckt name inside the file is NE3508M04_v124; the document had to be named v2_* (guard hook), so the document name differs.
- `v2_ne3508_bias`: schematic.
- `v2_ne3508_bias_iv`: rectangular graph, one trace.

## Parts (schematic v2_ne3508_bias)
- Equation (document-local): `Vgs=-0.314`
- SUBCKT.X1, NET="v2_ne3508_bias_dev", UgwNew=0.8, NfgNew=1, M=1. Pins verified: 1 gate (left), 2 drain (right), 3 source (bottom).
- DCVS.VG, V=Vgs, hung below X1:1 (pin 1 on gate, pin 2 to GND).
- DCVSS.VD, VStart=0, VStop=4, VStep=0.1 V, hung below X1:2 (pin 1 on drain, pin 2 to GND).
- GND on X1:3 (source).

## Wires
(0,0)-(0,1000) X1:1 to VG:1; (1000,0)-(1000,1000) X1:2 to VD:1; (0,2000)-(0,2500) VG:2 to GND; (1000,2000)-(1000,2500) VD:2 to GND; (500,400)-(500,900) X1:3 to GND. Straight, no crossings, none over parts.

## Graph
`v2_ne3508_bias_iv`: single measurement `v2_ne3508_bias.AP_DC:IDC(DCVSS.VD)` (simulator aplac_dc), x = Vds in V, y = Id in A. No frequency sweep needed (DC).

## Vgs search (Id at Vds = 3.0 V)
| Vgs (V) | Id (mA) |
|---|---|
| -0.100 | 79.7 |
| -0.300 | 22.91 |
| -0.320 | 18.76 |
| -0.314 | 19.96 |

Slope about 0.207 mA/mV; -0.313 would give about 20.17 mA, so -0.314 (19.96 mA, error 0.04 mA) is the 1 mV-rounded choice.

## Deviations
- Netlist document named `v2_ne3508_bias_dev` (hook rule) instead of the vendor name.
- theory.md guessed Vgs near -0.1 V and Id flat in Vds; real Id rises about 3.5 mA/V... (Id 12.2 mA at 2 V, 20.0 at 3 V, 29.9 at 4 V), so Vgs is -0.314 V.
- Search done by single-point reruns around Vds=3 V rather than a 0.05 V Vgs sweep.

> Lead note (21 Nov): the slope figures here are off. From the data, dId/dVds at 3 V is about 8.5 mA/V ((29.9-12.2)/2). Vgs came from the search, not from theory.
