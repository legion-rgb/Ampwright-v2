# cheb5_lpf review

MUST: none.

SHOULD / NICE
- NICE: remove `__pycache__/` from the dossier (clutter).
- NICE: no fix_log.md, correct (round 0 PASS). Build log values match theory.md table exactly (W/L of TL1-5, MSUB, ports).
- NICE: s21_pass margin is 0.32 dB (-0.683 vs -1.0); report it as marginal. Low-Z width 5.5 mm is near the 6 mm limit and high-Z 0.215 mm near 0.2 mm; both are inside spec.
- NICE: MSTEP discontinuities are not modelled (theory says so); the lead's v2_cheb5_lpf_mstep check covers it.

Checks
- Tidy: check_tidy.py ok, 0 issues. Six wires on y=0, one straight row, no crossings, no wire over a body or pin. build_log wire list matches the pin coordinates.
- Build log matches list_elements part for part (MSUB, TL1-5, P1, P2).
- Naming/clutter: project_info shows only schematic v2_cheb5_lpf and graph v2_cheb5_lpf_s; no netlists or EM structures. MSUB is v2_MSUB.
- Dossier: spec, theory, predictions, build_log, results, verdict present. report.md is the lead's job.
- Lesson: none new.
