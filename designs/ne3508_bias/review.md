# ne3508_bias review (21 Nov 2026)

Verdict reviewed: PASS (19.964 mA vs 20 +/- 1 mA).

## MUST
None.

## SHOULD
1. state.json is stale: phase "build", round 0. Set phase to "review"/"judged" so a resume is correct.
2. build_log.md Deviations: "rises about 3.5 mA/V..." is truncated and wrong. From 12.2/20.0/29.9 mA at 2/3/4 V the slope is about 8-9 mA/V. verdict.md open point "about 0.9 mA/V at 3 V" is off by 10x for the same reason. Fix both.
3. theory.md still says Id is flat in Vds and Vgs about -0.1 V. Add a one-line "superseded, see build_log/verdict" note (no fix_log exists, and the theory error is only explained in verdict.md).
4. spec.md says "Vgs from theory"; actual Vgs came from a search. Note this in the report.
5. Search used 4 points, not the planned 0.05 V sweep (already logged; fine).

## Checks
- Tidiness: check_tidy.py ok, no issues. Five straight wires, no crossings, none over bodies or pins; coordinates match build_log exactly.
- build_log vs schematic: X1, VG, VD, 3x GND match part for part, same parameters.
- Documents: project_info lists only v2_rc_lpf, v2_ne3508_bias (schematics), v2_ne3508_bias_dev (netlist), v2_rc_lpf_s, v2_ne3508_bias_iv (graphs). No strays. project_info does not list graph measurements; I could not confirm there are no leftover search traces on v2_ne3508_bias_iv (build_log says one trace).
- Values: Vgs -0.314 V (1 mV resolution, in range), sweep 0-4 V / 0.1 V step, UgwNew 0.8, NfgNew 1. Realistic; mismatch with theory explained in build_log and verdict.
- Dossier: spec, theory, predictions, build_log, results, verdict present. report.md is the lead's job.
