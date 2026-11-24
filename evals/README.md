# Agent evals

Tasks with known answers. Rerun them after any change to agent prompts, models or tools (AGENTIC_PLAN Phase E.3).

**Run one task:** the lead copies `evals/<task>/spec.md` and `spec.json` into `designs/<task>/`, then runs the normal loop in CLAUDE.md. Eval specs are approved once, so the loop doesn't stop at step 2. If `eval.json` has a `seed`, the lead follows it after the first PASS. Run one task at a time in AWR. Use a fresh untitled project and never save it.

**Score all runs:** `python evals/score.py`, or `python evals/score.py <designs dir>`. For each task it prints OK, FAIL with the reason, or "not run", plus the number of fix rounds used.

| Task | What it tests | Max rounds |
|---|---|---|
| rc_lpf | lumped S-parameter build, exact numbers | 1 |
| ne3508_bias | vendor netlist import, DC bias, Vgs search | 2 |
| rc_lpf_fault | a seeded 10x C fault is caught and fixed | 2 |
| tl_qwt | ideal TLIN matching, angle units (radians) | 1 |
| rlc_notch | shunt branch via add_shunt, notch depth | 1 |
| lmatch_opt | L-match; two seeded detunes retuned with the AWR optimizer (`fix_uses: run_optimizer`) | 2 |

**Unattended:** `python evals/run_headless.py [task ...] [--budget 5] [--dry-run]` runs each task with `claude -p`, one at a time, and writes its cost, turns and token use to `designs/<task>/headless.json`. `score.py` shows them. Interactive runs don't record cost.
