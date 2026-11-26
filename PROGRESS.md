# v2 plan progress

## Resume here (last updated 25 Nov 2026)
**State:** v2 was held while the Fieldnote GUI was built in v1. On 25 Nov the GUI was moved into v2 (user: "integrate the gui to v2 working condition"):
- v1's `server.py`, `graphs.py`, `hub.py` and `helpers.py` replaced v2's. v1 was a strict superset: the `approve` tool, the fixed Fieldnote pipe, and frequency sweeps in their own unit (`around_hz`).
- `fieldnote/`, `Fieldnote.bat`, `FIELDNOTE_PLAN.md` and the Fieldnote, session and tidy tests came over. v2's `check_tidy.py` was kept (it adds live mode).
- The transmission-line circuit fixtures now take EL in radians (v1's fix). The old `"90"` strings are read as SI radians since the `_set_param` change.
- The old window (`desktop_app.py`, `launch_desktop.bat`, `ui/`, `UI_PLAN.md`) is in `_archive_desktop_v2/`. `fieldnote_client.py` stays: `checks/_awr.py` uses it.
- Checked: 18/18 AWR-free tests, `validate` 71/71, `validate_em` 21/21, and the server starts. Not yet checked live with AWR open: open AWR, run `Fieldnote.bat`, and do the Phase 2 demo (RC low-pass, then delete a graph and Deny).

**Theory training (user, 26 Nov, before item 2):** plan in [THEORY_PLAN.md](THEORY_PLAN.md), rules in [THEORY_GOVERNANCE.md](THEORY_GOVERNANCE.md). Both proposed, nothing built. Phases T0 (baseline drills) to T6; absorbs items 3 and 4. Waiting on the user: approve the governance, textbooks to cite, OK for a `theory-curator` agent, first circuit classes.

**Own repo (user, 26 Nov, lead):** v2 is now a standalone git repo (branch `main`, history kept through `git subtree split`), to be pushed as the **private** GitHub repo `Ampwright-v2`. The parent `workspace` repo no longer tracks it and ignores both folder names. The folder is renamed `Ampwright-v2` to `Ampwright-v2` by the user, with this session closed. The tidy rule was copied into this repo's `CLAUDE.md`, and the agents, `hook_tidy` and the docs point there now (not to `../CLAUDE.md`).

**Renamed Fieldnote to Ampwright (user, 26 Nov, lead):** folders, files, agents, the pipe name and `AMPWRIGHT_PIPE`, the channel sender, deny texts and the UI. `%APPDATA%\Fieldnote` was copied to `%APPDATA%\Ampwright`, and the old folder is kept because v1 still uses it. v1 itself is unchanged and still called Fieldnote. Left as they were: older entries in this file, `designs/`, `_archive_desktop_v2/`, `docs/v2_proposal/` (untracked, not mine). All 18 AWR-free tests pass. `errors.md`/`playbook.md` were passed to lesson-keeper (mode `upgrade`). The AWR MCP server shows the new name in its instructions only after a restart. Older entries below say "Fieldnote" for the same app.

**v3 PA plan (user, 26 Nov):** drafted in "v3: RF power amplifier" at the bottom of this file. Proposed, nothing built. PA tasks only; all other RF design stays on the theory-first v2 loop with THEORY_PLAN (user, 26 Nov). Rewritten 26 Nov around the 10-step PA workflow (step gates, a device model card, a new `pa-diagnostician`, `pa_rules.md` experience base). Waiting on the user: the 6 open decisions there.

**Next (user, 25 Nov):** plan in chat: (1) a Quick/Design mode switch so Fieldnote can run the v2 agent loop, (2) a Theory vs Sim card read from the dossier, (3) the `*_design` inverses in rf_theory, (4) Chebyshev synthesis and an FET bias solver in rf_theory, (5) the open items below. v3 comes after.

**Mode switch (item 1), 25 Nov, lead:** planned in chat. Spec gate is reply-based (user). Design mode = cwd `Ampwright-v2`, tools `Read,Glob,Grep,Write,Agent`, `DESIGN_PROMPT`, same AWR server + `approve`.
- Step 1 probe done: headless session in v2 loads the v2 CLAUDE.md and all v2 agents; Agent works (init lists it as `Task`); subagent steps carry `parent_tool_use_id`, plus `task_started/progress/notification` system events. No AWR server in the probe, so subagent MCP calls and `approve` are not yet seen.
- Step 2 done: `session.lean_args(pipe, mode)`, `Session(mode=...)`, events carry `parent`. `test_session`, `test_fieldnote_chat`, `test_fieldnote_approval` pass.
- Step 3 done: `app.py` has `WORKSPACES` (quick = workspace, design = v2), a `mode` setting (unknown -> quick), `mode` in `state()`, `set_mode()` (refused mid-turn, no-op if already in it, else saves + note + restart), `_make_session()` with a resume id per mode (in memory only). All 5 Fieldnote tests pass via `uv run --script`.
- Step 4 done (tests = step 5, done with it): Quick/Design softkey pair in the header (locked mid-turn, tooltip warns Design uses more of the plan), empty-screen text and placeholder per mode. An Agent call is one row named after the subagent (`agent: True`, Claude icon); its steps carry `parent` and are indented; a subagent's own text is kept out of the chat. Nesting is indent-only in arrival order (`shortcut:` in app.js). All 5 Fieldnote tests pass. Not yet looked at in a real window.
- Review fixes (ponytail-review 1-4), 25 Nov: `hub.approve` now asks for built-in tools except Read/Glob/Grep/Agent/Task and Write/Edit inside the v2 folder (never `.emp`), so Bash or a write elsewhere shows the dialog; `set_mode` refuses while Claude is starting (no double restart), buttons locked then too; Design tools add Edit. All 18 AWR-free tests pass (`test_hub`, `test_client`, `test_channel` need `uv run --no-project --with "mcp>=1.2,<2" --with pywin32 python`).
- Second review fix, 25 Nov: the no-ask write rule is narrowed to `designs/` plus `PROGRESS.md`, `errors.md`, `playbook.md`. `hub.py`, `.claude/` (settings, agents), `checks/`, `CLAUDE.md` and every `.emp` now ask, so Claude can't edit its own safety checks silently. Fieldnote + hub tests pass.
- Full check with AWR, 25 Nov (lead, Untitled Project, nothing saved): 18/18 AWR-free tests; the 13 circuit batches re-run and `validate` 71/71 (open item 3, circuits part; `validate_em` held, it runs EM). Live Fieldnote backend (real Claude + AWR, script `live_fieldnote.py`, temp APPDATA): boot 4 s; Quick built FN_QUICK_RC + FN_QUICK_S21 in 31 s, S21 -6.53 dB at 1 GHz (3.01 dB below the passband), `check_tidy` clean; delete_graph showed the approval, Deny respected, graph kept; Design mode (boot 4 s) wrote `designs/fn_rc_check/` spec.md, spec.json, state.json with no dialog and no AWR writes, then stopped with the spec in 39 s. Usage: Quick build about 164k tokens incl. cache reads, Design spec about 154k.
- Found live: Quick mode set the frequencies project-wide (no `document`), which changes every schematic that uses the project sweep. The v2 guard hook that blocks this doesn't load in Quick mode (cwd is workspace). Not yet seen: subagents (none run before spec approval), so whether their requests reach `approve` is still open.
- Fixed 25 Nov: `hub.approve` now asks before `set_frequencies` / `add_equation` without `document` (project-wide), in both modes; the Quick prompt says to set them on the working schematic. (The v2 guard hook can't be loaded in Quick: it denies every non-`v2_*` document.) Tests pass; not re-run live.
- Step 6 done 26 Nov (lead; the session had only Read/Glob/Grep/Write/Edit/Agent, the Design-mode tool set, so probably the Fieldnote Design session): the user approved `fn_rc_check`, and the full loop ran: theory, build, evaluate, judge PASS round 0, review (no MUST), report, lesson-keeper. S21 was -3.522 / -6.532 / -23.566 dB at 10 MHz / 1 GHz / 10 GHz, within 0.005 dB of theory (`designs/fn_rc_check/report.md`). Not saved. Two findings: (a) `v2_fn_rc_check` and its graph were already in AWR before the build, origin unknown, rebuilt in place; (b) the evaluator's Bash was denied, so `check_spec.py` and `check_tidy.py` didn't run (errors.md E015, open). Likely cause of (b): Design mode has no Bash in its tool list, and subagents inherit that limit. Still open: whether subagent AWR writes went through `approve` (no dialog was needed for any of them). Check the Fieldnote log.
- Checked against the Fieldnote history, 26 Nov (master): (a) is explained. The user first sent "spec approved, run the full loop" while Fieldnote was in **Quick** mode (01:41). The Quick session built `v2_fn_rc_check` + graph itself in 30 s, with no subagents and no dossier files, and replied "The loop ran and the design passes", while also saying it had no subagent or write tool. The user then switched to Design and resent the message (01:42). The project_info at the start of that turn showed neither document. (b) is confirmed. The evaluator's call failed with "No such tool available: Bash. Bash is disabled for this session", so the lean `--tools` list also limits subagents. The old open question is answered: **subagent tool calls do reach `approve`**. The builder's 5 `delete_element` and 1 `delete_measurement` calls each showed the dialog (the user allowed them). Its other AWR writes and all subagent dossier writes went through with no dialog, as designed. Open: Bash for the scripted checks in Design mode; Quick mode claims to run "the loop" when asked; E015 in errors.md needs its cause filled in and sits above E014 (keeper's job).
- Fixed 26 Nov (master): (A2) Design mode's `--tools` adds Bash; `hub._runs_check` lets only `uv run|python checks/check_spec.py designs/<slug>` and `checks/check_tidy.py <schematic>` (optional `cd <v2> && `) run unasked, and every other Bash command shows the dialog. (B) The Quick prompt tells the user to switch to Design mode for the loop, a spec or an approval. (C) lesson-keeper: E015 has the confirmed cause, is fixed-in-code and sits after E014. Tests: test_session, test_fieldnote_chat, _chat_ui, _ui, _approval (8 allowed and 8 refused command forms), test_hub, test_client, test_channel, test_hooks all pass. Not re-run live.
- Side note: the user-level `~/.claude/CLAUDE.md` loads even with `--setting-sources project,local` (extra tokens in Quick mode too).

**Done in v2 (details in the tables below):**
- The agent loop works end to end in live AWR: theory -> build -> evaluate -> judge -> fix -> review -> report.
- 6 designs PASS: rc_lpf, ne3508_bias, rc_lpf_fault (seeded fault fixed in 1 round), tl_qwt, rlc_notch, cheb5_lpf (2 GHz Chebyshev on FR4).
- Evals 5/6 OK (`python evals/score.py`).
- Optimizer and sweep tools (E.1), the verified block library (E.2, 4 blocks), the topology comparison (E.4), the headless runner (E.6).
- The SI-numbers server fix; check_spec now reads full traces.
- The `lesson-keeper` agent with the `errors.md` catalogue (14 entries).

**Open, in order:**
1. Run `lesson-keeper` (mode `run`) on `designs/cheb5_lpf` as its first live test. It only reads AWR, so no AWR project is needed.
2. Run eval `lmatch_opt` (the first time the agents use the optimizer). It needs a fresh untitled AWR project.
3. Re-run the AWR regression suites (`tests/validate.py`, `validate_em.py` via `mcp_call.py --batch`), which haven't run since the `_set_param` change.
4. cheb5_lpf step check. MSTEP can't model the 0.039 width ratio, and the user stopped the MSTEPX (EM) retry because it may use an EM license. Ask the user before any EM or license-heavy run.
5. A first real `evals/run_headless.py` run (only dry-run so far).
6. Version 3: take the user's plans. The PA part is drafted in "v3: RF power amplifier" below. v2's known gaps (from the 22 Nov summary): EM designs through the agent loop, larger and active circuits (amplifiers, stability, noise, harmonic balance), Touchstone import, standard part values and tolerance, open-ended specs.

**Before any AWR step:** check `ListAgents` (another session writing to AWR?) and `project_info`, which can be empty after a manual reset (errors.md E013). Never save without the user's yes.


Master: the main session in this folder (see "Program lead" in CLAUDE.md). One line per step; update after each agent returns.

| # | Step | Status | Result / evidence | Who |
|---|---|---|---|---|
| 1a | Guard: deny `set_frequencies` / `add_equation` without `document` | done 21 Nov | `test_hooks` OK; live refusal seen | lead |
| 1b | `check_spec`: empty trace fails the goal, no crash | done 21 Nov | `test_checks` OK | lead |
| 1c | Copy `tests/_out` from v1 | done 21 Nov | `validate` 71/71, `validate_em` 21/21 | lead |
| 2 | Phase B live: tidy + spec checks on a sandbox schematic | done 21 Nov | tidy flagged a real crossing; spec −6.257 vs −6.256 dB by hand; sandbox deleted | v1 session |
| 3 | Phase C live: hooks fire in a real session | done 21 Nov | `add_equation` refused (non-v2 doc, and no doc) | lead |
| 4 | Phase D: `rc_lpf` to PASS | done 21 Nov | PASS round 0, all 3 goals within 0.001 dB of theory; review clean (`designs/rc_lpf/report.md`) | design team |
| 5 | Phase D: `ne3508_bias` to PASS | done 21 Nov | PASS round 0, Id 19.96 mA at Vgs -0.314 V; theory Vgs guess wrong, Judge checked the physics (`designs/ne3508_bias/report.md`) | design team |
| 6 | Phase D: seeded wrong value in `rc_lpf` fixed in ≤ 2 rounds | done 21 Nov | C1 10x caught by Evaluator + Judge, fixed in 1 round, re-PASS (`designs/rc_lpf/report.md`) | design team |
| 7 | Final report and next-step choice (tidy router vs optimizer) | done 21 Nov | reported to user; choice is theirs | lead |

AWR: fresh untitled project (user, 21 Nov). Never saved.

## Open points (21 Nov)
- String part values: settled in step 8, corrected 21 Nov: a unit suffix ("4775 pF") fails to simulate, and a number can arrive as text. Use display-unit expressions ("4.775*100") or numbers, and confirm with get_parameters. A possible server fix (treat numeric text as SI) needs user approval.
- `results.json` "how" says "interpolation" even at exact sweep points (cosmetic).
- The ne3508 bias sits near pinch-off, which is very sensitive to Vgs and Vds. Fine for the spec; note it for any real bias network.
- Phase E not started. Next step to choose: optimizer/sweep tools (E1), or a tidy-aware router.

## Next steps (started 21 Nov, after "go ahead")
| # | Step | Status | Result / evidence | Who |
|---|---|---|---|---|
| 8 | Settle string part-value units (probe) and fix docs | done 21 Nov | Real strings are display units, numbers are SI; a bare numeric string reaches `set_parameter` as a number (SI). Fixed `server.py` docstrings, playbook, README (`designs/_probes/param_units.md`). v1's copy of server.py is not updated | builder (probe) + lead |
| 9 | Phase E.3 eval suite: `evals/` (5 tasks), `evals/score.py`, `tests/test_evals.py` | built 21 Nov | `test_evals` OK; real dossiers score 2/5 (3 not run yet) | lead |
| 10 | Run the 3 new eval tasks in AWR | done 21 Nov | **5/5 OK** (`python evals/score.py`). rc_lpf_fault: seed caught and fixed in 1 round. tl_qwt and rlc_notch: PASS in round 0. Reports in `designs/<task>/report.md` | design team |
| 11 | Server fix: plain-number text is SI (`schematic._set_param`) | done 21 Nov (user yes) | `tests/test_params.py` OK; docs updated. **Live only after an MCP server restart** | lead |
| 12 | check_spec reads full traces (max_points 1e6; a truncated trace fails) | done 21 Nov | found live on rlc_notch (2000-point cut); `test_checks` OK | lead |


## Phase E (started 21 Nov, user: "go with E.1 optimizer tools and also the future plans. don't merge v1 to v2 now")
| # | Step | Status | Result / evidence | Who |
|---|---|---|---|---|
| 13 | E.1 optimizer + sweep tools (`optimize.py`: opt_state, set_opt_variable, add_opt_goal, delete_opt_goals, run_optimizer, sweep) | done 21 Nov | live via a fresh server (`tests/mcp_call.py`): Simplex 1 nF -> 477.2 pF in 0.8 s; refusals work; sweep restores. `test_optimize`, `test_hooks` OK. Fixer and judge prompts updated | lead |
| 14 | E.1 eval task `lmatch_opt` (seeded 2-value detune, `fix_uses: run_optimizer`) | built, **not run** | needs the MCP restart (session server lacks the new tools) | lead |
| 15 | E.2 block library: `checks/promote.py`, `library/` with 4 blocks | done 21 Nov | `test_promote` OK; theory and builder prompts read `library/` | lead |
| 16 | E.4 design-space: theory compares 2-3 topologies and marks one Recommended | done 21 Nov | prompt change only | lead |
| 17 | E.5 vendor library: playbook note (Glob + import_netlist), no new tool | done 21 Nov | a `search_library` tool was judged not needed; offered to the user | lead |
| 18 | E.6 headless runs: `evals/run_headless.py` (claude -p, budget cap, cost in headless.json, shown by score.py) | built, **not run** | dry run OK | lead |
| 19 | Harder design `cheb5_lpf` (5th-order Chebyshev, 2 GHz, FR4 microstrip) | **PASS 22 Nov, round 0** | -0.683 / -17.55 / -27.85 dB, all within 0.05 dB of theory; passband margin 0.32 dB. The step check was blocked (MSTEP needs a width ratio >= 0.05); the MSTEPX retry was stopped by the user (license). `designs/cheb5_lpf/report.md` | design team |
| 20 | `lesson-keeper` agent + `errors.md` catalogue (14 entries seeded from v2 runs) | done 22 Nov (user: "build it now") | the only writer of errors.md/playbook.md; modes run/upgrade; `test_agents` enforces it and checks the format (8 agents) | lead |
| - | Tidy-aware router | skipped | no crossings in any run so far; revisit if one appears | - |
| - | Merge v1 into v2 | not now | user: don't merge now | - |

Incident 21 Nov: the AWR untitled project was found empty during step 13. The v1 session made no AWR writes; most likely AWR was reset or restarted by hand. All dossiers are on disk and nothing was saved.

**Paused 22 Nov at the user's request.** The user has plans for a version 3. Still open in v2: run `lmatch_opt` (needs an open AWR project), run the AWR regression suites after the `_set_param` change, and the cheb5 step check (EM, or widen to >= 275 um and retune).


## v3: RF power amplifier (plan, rewritten 26 Nov 2026, not started)
Goal: the agents design an RF PA in AWR the way a PA designer does. Theory is used only where it decides something: class and feasibility (step 2) and matching synthesis (step 7). Every other step is decided by running the right AWR tool and reading its plots. AWR is the source of truth, but only inside the device model's valid range and with a correct set-up (converged HB, enough harmonics). Every analysis of an AWR plot is written down, so the next design starts with that experience.

**Where we start (checked 26 Nov):**
- Every PASS so far is passive or a DC bias point. No agent, playbook entry or check knows PA metrics.
- `add_measurement` accepts a `simulator` (`aplac_hb`...), but no HB run has been done through the server.
- Missing: port power and power sweep, load-pull, source-pull, two-tone, HB options, dynamic load line.
- NE3508 is a low-noise device. A PA needs a power device with a nonlinear vendor model.

### Scope: two loops (user, 26 Nov)
**This workflow is for PA design only.** The Lead picks the loop at spec intake and records it in `state.json` as `"loop": "pa"` or `"loop": "rf"`:

| Task | Loop | Driven by |
|---|---|---|
| Power amplifiers (and later other large-signal active stages, if the user says so) | **PA loop** (below) | AWR tools, plot reading, the Diagnostician, `pa_rules.md` |
| Everything else in RF and microwave engineering: transmission lines, microstrip, matching networks, Smith-chart work, filters, couplers, dividers, resonators, stubs, transformers, bias networks | **RF loop**: the existing v2 loop (theory, build, evaluate, judge, fix, review), unchanged | Textbook theory first (Pozar-style microwave engineering), through THEORY_PLAN's cards and `rf_design.py`; the Judge keeps the gap check between prediction and measurement |

- The two loops share the theory base. PA step 7 (matching) uses the same matching cards and functions as the RF loop, so THEORY_PLAN T3 serves both.
- The PA additions (`pa-diagnostician`, the model card, `check_validity`, `pa_rules.md`, the step gates) run only when `loop` is `pa`. The v2 agents keep their current RF behaviour. Each agent's PA rules go in a separate "PA loop" section of its file, so the RF instructions stay as they are.
- An unclear case (for example a mixed PA plus filter module) is a question to the user at spec intake: one loop per block, or the PA loop for the whole design.
- P5 adds a routing test: `test_agents` checks that both loops are described and that no PA-only rule (judging against the spec only, no theory gap) leaks into the RF loop.

### The PA workflow (step gates)
The Lead runs one step at a time. Each step names the AWR tool to run, what to read from its plot, the decision rule, and when the step is done. The Diagnostician reads the plots at **every** step, not only on failure.

| # | Step | Tool / source | Read from the plot | Decision, and when the step is done |
|---|---|---|---|---|
| 1 | **Spec intake** | Lead + **user** | — | Pout, Vdd, efficiency, technology, f0 and bandwidth, gain, linearity. **Ask the user for the device model's valid range** (step 1b). Done when the user approves spec.md |
| 1b | **Device model card** | user, vendor documents | — | `library/devices/<device>.md`: valid Vds and Vgs, Id max, Pdiss max, breakdown, frequency range, temperature, the model's known limits. Anything missing is asked of the user, never guessed. Done when the user confirms the card |
| 2 | **Class and feasibility** | the user's formulas in `rf_design.py` | — | Class, Ropt, Imax, ideal η, expected Pout. Done when Pout and η are reachable with margin; if not, stop with SPEC_UNREACHABLE |
| 3 | **Bias point** | DC I-V, gm and gm3 against Vgs | knee, pinch-off, gm shape, where gain expansion would start | Vgs and Idq inside the model card. Done when the bias is inside the valid range and matches the chosen class |
| 4 | **Stability (first pass)** | K, μ, stability circles over a wide band (about 0.1 to 3 × f0) | where K < 1 or μ < 1, and at which frequency | Add a stabiliser if needed. Done when the stage is unconditionally stable over the wide band |
| 5 | **Architecture** | Lead + experience | — | Narrowband or wideband; single-ended, balanced, Doherty, harmonic-tuned. **Shown to the user** with the step-2 class (proposed checkpoint) |
| 6 | **Load-pull and source-pull** | AWR load-pull and source-pull (f0, band edges, harmonics if needed) | Pout and PAE contours, their optima, the trade-off region | The target ZL and ZS. Done when the target point meets Pout and PAE with margin and stays inside the model card |
| 7 | **Matching networks** | theory synthesis (THEORY_PLAN T3) + AWR | impedance path on the Smith chart across the band | Done when the impedances the device sees stay inside the chosen contours over the band |
| 8 | **Full PA check** | HB power sweep | Pout, gain, P1dB, PAE against Pin, harmonics, dynamic load line against the I-V and the model card | Done when every spec goal passes, and the load line stays inside breakdown, Pdiss and the model range |
| 9 | **Linearity** | AM-AM, AM-PM, two-tone IM3, ACLR | compression shape, phase drift, IM3 slope and sweet spots | Done when the linearity goals pass |
| 10 | **Final stability and robustness** | K and μ again at all drive levels; output mismatch if specified | — | Done when it is stable everywhere; then the Judge gives the final PASS |
| ↺ | **Diagnose and iterate** | Diagnostician | the symptom in the plot | A fault goes back to the step that owns its cause (for example low PAE back to step 6 or 3), not always to the last step |

**Stops for the user:** spec (1), model card (1b), class and architecture (5, proposed), SPEC_UNREACHABLE or 3 failed rounds on a step, any save.

### Agents
| Agent | Change |
|---|---|
| **pa-diagnostician** (new, Opus) | Reads the plots and data after every AWR run: `graph_data`, plus `graph_image` for shape only. Applies the rules in `pa_rules.md` and cites their ids. Writes `diagnosis.md` in the dossier (step, symptom, plot, likely cause, the check that confirms it, the proposed fix, confidence) and one entry in the run journal. A new pattern gets a `Rule-candidate:` line. It may add graphs and measurements only in documents named `v2_<slug>_diag*` and simulate those; it never changes the circuit. A hook enforces this. It counts as an AWR writer (one at a time) |
| circuit-theory | Narrowed to step 2 (the user's class formulas) and step 7 (matching synthesis). It no longer predicts every metric |
| awr-builder | Runs each step's tool set-up, following the PA recipes in the playbook |
| circuit-evaluator | PA metrics through `check_spec`, plus `check_validity.py`: operating point and dynamic load line against the model card, HB convergence |
| verification-judge | Judges against the spec and the model card, not against theory. Stability is a hard gate. HB results are re-checked once with more harmonics. A theory gap alone is never a FAIL |
| circuit-fixer | Applies the Diagnostician's proposed fix, one change per round, at the step that owns the cause. May use the optimizer on load-pull or matching goals |
| design-reviewer | Adds PA hygiene: DC blocks and feeds, no floating DC node, part ratings, values realistic for the technology |
| lesson-keeper | Also the only writer of `pa_rules.md` and `designs/INDEX.md` (see below) |

### Experience: what is kept from every run
- **Run journal:** each `diagnosis.md` holds every plot read and what was concluded, kept in the dossier for good.
- **`pa_rules.md`** (rule base): one rule per pattern. Fields: id, symptom, plot, the check that confirms it, cause, fix, step, technology, source (user or run), seen in, status. Status runs `candidate` → `draft` → `confirmed`. A rule is confirmed by the user, or when its fix was confirmed by the Judge in 2 runs. A rule whose fix fails is demoted and the failure is noted. The user's own rules start as `user` (trusted).
- **`designs/INDEX.md`** (case memory): one line per PA design (technology, device, f0, bandwidth, Pout, class, architecture, result). The Lead and the Diagnostician start from the nearest past design.
- **Rule for keeping a lesson:** after a rule or recipe changes, the PA evals are re-run. A change that lowers the score is reverted.

### Phases
| # | Phase | What | Done when | Who |
|---|---|---|---|---|
| P0 | Tool probe | In a `v2_pa_probe` sandbox with the chosen device: I-V and gm, K and μ with stability circles, HB power sweep (Pout, gain, PAE, harmonics), dynamic load line, load-pull, source-pull, two-tone and AM-PM. Record the working measurement strings, set-up steps and run times in `designs/_probes/pa_tools.md` | Each item returns data through `graph_data`, or its gap is written with the server change it needs | awr-builder (probe), lead checks |
| P1 | Server gaps | Only what P0 proves is missing (likely port power or power sweep, HB options, load-pull and source-pull returning the optimum and contours as data). Each new tool gets a unit test and a hook rule if it writes | Tests pass; the tools run live on the probe | fieldnote-builder, test-runner |
| P2 | Model card and validity | Model card format, `library/devices/`, and `checks/check_validity.py` (bias, load line, Pdiss against the card) | `test_checks` passes on fixtures, including one load line that goes out of range | lead |
| P3 | Spec and step format | PA metrics in `spec.json` (`Pout_dBm`, `Gain_dB`, `P1dB_dBm`, `PAE_pct`, `DE_pct`, `H2_dBc`, `IM3_dBc`, `Idq_A`, `K_min`/`mu_min` over a wide band); `check_spec` computes P1dB and peak PAE; `state.json` tracks the current step | Tests pass on fixture traces with hand-known values | lead |
| P4 | Step-2 and step-7 tools | The user's class and feasibility formulas in `rf_design.py` with cards; matching synthesis from THEORY_PLAN T3 | Self-checks pass; one worked example of the user's each | theory-curator or lead |
| P5 | Diagnostician and experience files | `pa-diagnostician.md`, its hook, `pa_rules.md`, `designs/INDEX.md`, keeper changes, the PA section of the workflow in CLAUDE.md and AGENTIC_PLAN.md | `test_agents` and `test_hooks` pass; the diagnostician is refused any edit to a non-`diag` document | lead |
| P6 | Seed the rules | The user's diagnostic rules ("when I see X in plot Y, I check Z") written as `user` rules | The user checks the list | user + keeper |
| P7 | Design ladder and evals | (1) `pa_bias_stab`: steps 1 to 4; (2) `pa_classA_hb`: up to step 8 with a fixed load; (3) `pa_classAB_lp`: full flow with load-pull and source-pull and PAE; (4) **diagnosis evals:** seeded faults (oscillation, bias too low with gain expansion, load near the knee, detuned output match, bias outside the model card), each scored on whether the Diagnostician names the right cause and step; (5) linearity (step 9); (6) stretch: wideband or harmonic-tuned | Each rung PASSes before the next; the old 6 evals still score at least 5/6 | design team, test-runner |
| P8 | Layout and EM (later) | EM checks of the critical matching parts | Only after the user OKs the licence use | design team |

**Order:** P0 needs AWR; P2, P3 and P5 need none and can run beside it. P4 waits for the user's formulas and THEORY_PLAN T1. P7 rung 1 can start after P0 to P3 and P5.

**Success measures:** diagnosis evals name the right cause at least 80% of the time; fix rounds per PA design go down over the ladder; no operating point outside the model card goes undetected; the number of confirmed rules goes up.

**Risks:**
- Vendor models differ in quality and in which parameters they expose.
- HB may fail to converge at high drive.
- Load-pull or source-pull may not be scriptable through COM; P0 will show this.
- The 15-minute `simulate` limit may be hit.
- A wrong rule can mislead later designs, which is why rules need confirmation and evals gate every change.

**Open decisions for the user:**
1. Device and model: which power transistor, is its vendor kit installed in AWR, and what is its valid range (or where it is documented)?
2. First target: f0, bandwidth, Pout, PAE, Vdd, substrate.
3. Licences: are HB and load-pull/source-pull licensed in this AWR install?
4. Your class and feasibility formulas (step 2), and a first set of diagnostic rules (P6).
5. Should the step-5 class and architecture checkpoint stop for you (proposed: yes)?
6. Order: start P0, P2, P3 and P5 now beside the theory plan, or finish theory T0 to T2 first? And the `theory-curator` decision from THEORY_PLAN.
