# Error catalogue

Errors seen while building designs, how to solve them, and whether they still happen. Every agent reads this, together with `playbook.md`, before working. Only the `lesson-keeper` agent edits it. Other agents put a `Lesson:` line in their log or review, and the keeper records it.

Each entry has these fields:
- **Symptom:** the exact error text, or what went wrong.
- **Cause**
- **Fix:** what to do.
- **Status:** one of
  - `fixed-in-code`: code now prevents it;
  - `workaround`: avoid it as the Fix says;
  - `open`: no good fix yet;
  - `retired`: no longer true; kept for history.
- **Seen:** the version, date, and design.
- **Recheck:** how to confirm, after an upgrade (new v3 code, AWR version, server change), that the entry is still true.

Lookup: search for the error text (for example `Parse Error`, `Ports may not`, `W2/W1`).

## E001 Unit suffix in a part value fails to simulate
- **Symptom:** `CAP.C1: Error evaluating parameter 'C' (Parse Error: syntax 'pF')` at simulate. `set_parameter` itself succeeds and reads back `4775 pF`.
- **Cause:** AWR stores the text with its unit suffix, but the simulator can't parse the suffix.
- **Fix:** pass an SI number (`4.775e-9`) or a display-unit expression (`'4.775*1000'` = 4775 pF). Confirm with `get_parameters`.
- **Status:** workaround
- **Seen:** v2, 21 Nov 2026, rc_lpf_fault seed (2nd try)
- **Recheck:** in a `v2_` sandbox, set a CAP C to `"1000 pF"` and simulate. Expect the parse error.

## E002 Numeric text read in display units (4.775e-9 became 4.775e-9 pF)
- **Symptom:** a value meant as SI reads back as `4.775e-9` with unit pF, which is about zero. The circuit acts as if the part were open or missing.
- **Cause:** the agent's tool call sent the number as text. The old server sent text to AWR unchanged, and AWR reads text in display units.
- **Fix:** the server now treats any plain-number text as SI (`schematic._set_param`).
- **Status:** fixed-in-code (live after the 22 Nov MCP restart)
- **Seen:** v2, 21 Nov 2026, rc_lpf_fault seed (1st and 3rd tries)
- **Recheck:** `python tests/test_params.py`. Live: `set_parameter` C = `"4.775e-9"` reads back `4775` pF.

## E003 Angle sent as text '90' becomes 90 radians
- **Symptom:** TLIN `EL` reads back as about 5157 Deg instead of 90 Deg.
- **Cause:** a consequence of the E002 fix. Plain-number text is now SI, and angles are SI in radians.
- **Fix:** send radians as a number: `1.5707963` = 90 deg. Confirm that EL reads back `90` Deg.
- **Status:** workaround
- **Seen:** v2, 21 Nov 2026, tl_qwt (the builder sent '90'; it worked only on the old server)
- **Recheck:** live: `set_parameter` EL = `"90"` and read it back. Expect about 5157 Deg.

## E004 Long sweep read only partly (2000 points)
- **Symptom:** `check_spec` fails a goal with `f=... outside trace x range`, although the sweep covers that frequency. The trace stops at about point 2000.
- **Cause:** `graph_data` returns at most `max_points` (2000 by default).
- **Fix:** pass `max_points` large enough. `check_spec` now asks for 1e6 points and fails a truncated trace with "truncated".
- **Status:** fixed-in-code
- **Seen:** v2, 21 Nov 2026, rlc_notch (12001 points)
- **Recheck:** `python tests/test_checks.py` (the truncated-trace case).

## E005 Two ports on one node
- **Symptom:** `Ports may not be connected together`
- **Cause:** a shunt-only circuit puts port 1 and port 2 on the same node, which AWR forbids.
- **Fix:** put a tiny series part between the ports (`RES` 1e-6 Ohm). Its effect on S21 is about 1e-7 dB. Plan it in theory.md.
- **Status:** workaround
- **Seen:** v2, 21 Nov 2026, rlc_notch
- **Recheck:** in a `v2_` sandbox, wire two ports to one node and simulate.

## E006 MSTEP width-ratio limit
- **Symptom:** `MSTEP.S1 : W2/W1=0.0390909, must be >= 0.05`
- **Cause:** the closed-form MSTEP model is valid only for width ratios of 0.05 or more.
- **Fix:** none tried yet. Options:
  - widen the narrow line so the ratio is 0.05 or more, and retune the lengths with the optimizer;
  - use MSTEPX (EM-based; uses an EM license, ask the user first);
  - leave steps out and say so in the report.
- **Status:** open
- **Seen:** v2, 22 Nov 2026, cheb5_lpf step check (215 and 5500 um lines)
- **Recheck:** an MSTEP with W1 5.5 mm and W2 0.215 mm should give this error.

## E007 Optimizer method index starts at 1
- **Symptom:** `The value specified by Index is too small.` from `Optimizer.TypeName(0)`.
- **Cause:** the COM optimizer method list is 1-based.
- **Fix:** `optimize._methods` reads indices 1 to TypeCount. Agents pass method names, never indices.
- **Status:** fixed-in-code
- **Seen:** v2, 21 Nov 2026, E.1 probe
- **Recheck:** `opt_state` lists about 33 methods, and the first is "Advanced Genetic Algorithm".

## E008 Optimizer goal cost is stale until you simulate
- **Symptom:** `add_opt_goal` returns cost 0, or `run_optimizer` reports start_cost 0, although the design is off.
- **Cause:** goal costs come from the last simulation, not from the current part values.
- **Fix:** simulate the graph before `add_opt_goal` and `run_optimizer`.
- **Status:** workaround
- **Seen:** v2, 21 Nov 2026, E.1 live test
- **Recheck:** change a value, add a goal without simulating, and the cost still matches the old value.

## E009 run_optimizer refuses because of another document
- **Symptom:** `other documents have enabled goals or optimize flags: [...]. Only <schematic> may take part.`
- **Cause:** a run on another design left goals or optimize flags behind. The optimizer is project-wide, so the tool refuses.
- **Fix:** on that design, call `delete_opt_goals` and `set_opt_variable optimize=false`, but only if it is a `v2_` document the agent may change. Otherwise ask the lead.
- **Status:** workaround (by design)
- **Seen:** v2, 21 Nov 2026, E.1 live test
- **Recheck:** `python tests/test_optimize.py`.

## E010 One-item list comes back as a bare item
- **Symptom:** a checks script crashes iterating `graph_data` output when the graph has one measurement.
- **Cause:** the hub unwraps a one-item list into the bare item.
- **Fix:** `checks/_awr.call_list` wraps it back.
- **Status:** fixed-in-code
- **Seen:** v2, 21 Nov 2026, Phase B live
- **Recheck:** `python tests/test_checks.py`.

## E011 MSUB has no ID parameter
- **Symptom:** `set_parameter` / `add_element` with `id=` does not name the MSUB.
- **Cause:** MSUB is named by its `Name` parameter, which the MLINs refer to.
- **Fix:** set `Name` to `v2_MSUB` (or `v2_<slug>_sub`).
- **Status:** workaround
- **Seen:** v2, 22 Nov 2026, cheb5_lpf
- **Recheck:** `get_parameters` on an MSUB lists `Name` and no `ID`.

## E012 Project-wide change denied by the guard hook
- **Symptom:** `set_frequencies without document changes the whole project. Pass document='v2_<slug>...'.` (also for `add_equation`)
- **Cause:** the guard hook blocks changes to the project sweep and Global Definitions.
- **Fix:** always pass `document='v2_<slug>'`.
- **Status:** workaround (by design)
- **Seen:** v2, 21 Nov 2026, Phase C
- **Recheck:** `python tests/test_hooks.py`.

## E013 "A project is not open", or the project suddenly empty
- **Symptom:** COM error `A project is not open.`, or `project_info` shows no v2_* documents that should exist.
- **Cause:** the user closed or replaced the AWR project, or AWR restarted. On 21-22 Nov the v1 session confirmed it made no writes.
- **Fix:** don't recreate anything yourself. Report to the lead, who asks the user for a fresh untitled project. The dossier files are the record; AWR state is disposable.
- **Status:** open (an outside event)
- **Seen:** v2, 21 Nov 2026 (empty project during E.1) and 22 Nov 2026 (no project after the MSTEPX stop)
- **Recheck:** none. The lead runs `project_info` before each AWR step.

## E014 An agent wrote a wrong lesson
- **Symptom:** a playbook line that contradicts the code. Examples: "send EL as '90' degrees" after the E002 fix, and calling a seeded fault a "stale value".
- **Cause:** any agent could edit playbook.md, and nothing checked what it wrote against the code or the seed records.
- **Fix:** only the lesson-keeper writes playbook.md and errors.md. `tests/test_agents.py` enforces this.
- **Status:** fixed-in-code
- **Seen:** v2, 21 Nov 2026, rc_lpf_fault and tl_qwt
- **Recheck:** `python tests/test_agents.py`.

## E015 Evaluator's Bash denied, so check_spec.py and check_tidy.py don't run
- **Symptom:** the evaluator's call failed with `No such tool available: Bash. Bash is disabled for this session`; the scripted checks in `checks/` couldn't run.
- **Cause:** Fieldnote's Design mode started Claude Code with a lean `--tools` list (Read,Glob,Grep,Write,Edit,Agent). Subagents inherit that list, whatever their agent file says (`circuit-evaluator.md` lists Bash).
- **Fix:** `fieldnote/session.py` now adds Bash to the Design-mode tool list. `hub.approve` (`_runs_check` in `hub.py`) lets only `uv run|python checks/check_spec.py designs/<slug>` and `checks/check_tidy.py <schematic>` (optional `cd <v2 folder> && ` prefix) run without a dialog; any other Bash command shows the approval dialog. Workaround for older runs: read values with `graph_data` and judge tidiness from `list_wires`, and say the scripts did not run.
- **Status:** fixed-in-code
- **Seen:** v2, 26 Nov 2026, fn_rc_check (PASS by the manual route)
- **Recheck:** `uv run --script tests/test_fieldnote_approval.py` and `python tests/test_session.py`. Live recheck: the next Design-mode run shows check_spec.py running in the evaluator.
