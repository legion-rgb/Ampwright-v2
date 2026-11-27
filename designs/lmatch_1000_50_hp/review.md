# Review: lmatch_1000_50_hp (read only, graph formatting excluded)

## MUST
- None.

## SHOULD / NICE
1. state.json is stale: `phase` is `theory_done` and `docs` is `[]`, but the build, evaluation and verdict are done. Fix: set phase to the real one and list `v2_lmatch_1000_50_hp` and `v2_lmatch_1000_50_hp_s` under `docs`.
2. predictions.json: s11_f0 predicts -100 dB, but the build with rounded parts gives -61.25 dB. verdict.md already explains it. Fix: set the value to -61 and keep -100 as a note in `basis`.
3. report.md does not exist yet. The lead writes it (step 7).
4. build_log.md says nothing about arrange_windows or tidy_graph being skipped on purpose. It does say "as instructed". Fine.

## Checked and OK
- check_tidy: ok, no issues. Four straight wires and no crossings. The wires on the C1:1 node, (-1000,0)-(0,0) and (0,0)-(0,1000), meet at a tee on a pin. Nothing runs over a body.
- build_log.md matches list_elements part for part: C1 14.61 pF, L1 730.3 nH, P1 1000 Ohm, P2 50 Ohm, one GND. Wire coordinates match.
- Naming: `v2_lmatch_1000_50_hp` and `v2_lmatch_1000_50_hp_s` follow the rule.
- Values match theory.md (730.3 nH, 14.61 pF). The 4-digit rounding is explained in verdict.md.
- Clutter: project_info also shows `Match_50_250`, `Match_50_250 Sparams`, `v2_lmatch_50_250` and `v2_lmatch_50_250_s`. None belong to this design, so there are no stray documents from it. The first two are not v2-named. Leave them for the lead or the user to decide.

Lesson: none.
