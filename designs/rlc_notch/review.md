# review rlc_notch
MUST: none.
Tidy: check_tidy.py ok, 0 issues. Vertical shunt column L1-C1-R1-GND, one straight horizontal wire to R2, port wires straight; no crossings, none over bodies or pins.
Naming: only v2_rlc_notch and v2_rlc_notch_s from this design; other v2_* documents belong to other designs. No clutter.
build_log matches schematic part for part (L1 100 nH, C1 0.1 pF, R1 1 Ohm, GND, R2 1e-6 Ohm, P1/P2 50 Ohm). Values standard.
Dossier complete: spec, theory, predictions, build_log, results, verdict.
SHOULD:
- theory.md still says ports joined by a through wire; build uses R2 = 1e-6 Ohm. Add a one-line pointer to build_log deviation (no fix_log exists).
- theory.md has an unfinished note on grid offset ("yields value within ~0.1 dB at nearest point?"); tidy it.
- R2 1e-6 Ohm is non-standard; acceptable as a documented AWR workaround.
Lesson for lead: theory should not specify a through wire between two ports; AWR rejects directly connected ports, so plan a tiny series R from the start.
