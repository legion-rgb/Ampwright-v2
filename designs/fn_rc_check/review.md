# Review: fn_rc_check

MUST: none.

NICE
1. Origin of pre-existing v2_fn_rc_check and v2_fn_rc_check_s is not in the dossier (state.json note says so). Add one line saying who created them.
2. checks/check_spec.py was not run (Bash denied). Rerun it when Bash is allowed, so the verdict does not rest on hand reads only.
3. report.md is not written yet (lead step 7). It is the only dossier piece missing.
4. No `checks/check_tidy.py` run; tidiness was judged from coordinates (see below).

Checks
1. Tidiness: 4 straight wires, no crossings. R1 body (0..1000, y=0), C1 body (x=1000, y 1000..2000), GND at y=2500. The R1:2 junction is a T joint (R1:2, C1:1, P2). No wire runs over a body or pin. OK.
2. build_log.md matches list_elements part for part (R1 50, C1 4.775 pF, GND, P1, P2) and the 4 wires. OK.
3. Naming: only v2_fn_rc_check and v2_fn_rc_check_s belong to this design. No stray v2_ graphs or schematics. Other documents were not checked, as instructed.
4. Values: R 50 Ohm and C 4.775 pF match theory.md (C = 1/(2*pi*1e9*33.33)). C is not a standard E-series value, but it is a theory-derived ideal lumped part. Acceptable. No line widths apply.
5. Dossier: spec, theory, predictions, build_log, results and verdict are present. Report is pending.

Lesson: none.
