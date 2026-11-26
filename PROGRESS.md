# v2 plan progress

## Resume here (last updated 25 Nov 2026)
**State:** v2 was held while the Fieldnote GUI was built in v1. On 25 Nov the GUI was moved into v2 (user: "integrate the gui to v2 working condition"):
- v1's `server.py`, `graphs.py`, `hub.py` and `helpers.py` replaced v2's. v1 was a strict superset: the `approve` tool, the fixed Fieldnote pipe, and frequency sweeps in their own unit (`around_hz`).
- `fieldnote/`, `Fieldnote.bat`, `FIELDNOTE_PLAN.md` and the Fieldnote, session and tidy tests came over. v2's `check_tidy.py` was kept (it adds live mode).
- The transmission-line circuit fixtures now take EL in radians (v1's fix). The old `"90"` strings are read as SI radians since the `_set_param` change.
- The old window (`desktop_app.py`, `launch_desktop.bat`, `ui/`, `UI_PLAN.md`) is in `_archive_desktop_v2/`. `fieldnote_client.py` stays: `checks/_awr.py` uses it.
- Checked: 18/18 AWR-free tests, `validate` 71/71, `validate_em` 21/21, and the server starts. Not yet checked live with AWR open: open AWR, run `Fieldnote.bat`, and do the Phase 2 demo (RC low-pass, then delete a graph and Deny).

**Next (user, 25 Nov):** plan in chat: (1) a Quick/Design mode switch so Fieldnote can run the v2 agent loop, (2) a Theory vs Sim card read from the dossier, (3) the `*_design` inverses in rf_theory, (4) Chebyshev synthesis and an FET bias solver in rf_theory, (5) the open items below. v3 comes after.

**Mode switch (item 1), 25 Nov, lead:** planned in chat. Spec gate is reply-based (user). Design mode = cwd `AWRMWO-mcp-v2`, tools `Read,Glob,Grep,Write,Agent`, `DESIGN_PROMPT`, same AWR server + `approve`.
- Step 1 probe done: headless session in v2 loads the v2 CLAUDE.md and all v2 agents; Agent works (init lists it as `Task`); subagent steps carry `parent_tool_use_id`, plus `task_started/progress/notification` system events. No AWR server in the probe, so subagent MCP calls and `approve` are not yet seen.
- Step 2 done: `session.lean_args(pipe, mode)`, `Session(mode=...)`, events carry `parent`. `test_session`, `test_fieldnote_chat`, `test_fieldnote_approval` pass.
- Step 3 done: `app.py` has `WORKSPACES` (quick = workspace, design = v2), a `mode` setting (unknown -> quick), `mode` in `state()`, `set_mode()` (refused mid-turn, no-op if already in it, else saves + note + restart), `_make_session()` with a resume id per mode (in memory only). All 5 Fieldnote tests pass via `uv run --script`.
- Step 4 done (tests = step 5, done with it): Quick/Design softkey pair in the header (locked mid-turn, tooltip warns Design uses more of the plan), empty-screen text and placeholder per mode. An Agent call is one row named after the subagent (`agent: True`, Claude icon); its steps carry `parent` and are indented; a subagent's own text is kept out of the chat. Nesting is indent-only in arrival order (`shortcut:` in app.js). All 5 Fieldnote tests pass. Not yet looked at in a real window.
- Review fixes (ponytail-review 1-4), 25 Nov: `hub.approve` now asks for built-in tools except Read/Glob/Grep/Agent/Task and Write/Edit inside the v2 folder (never `.emp`), so Bash or a write elsewhere shows the dialog; `set_mode` refuses while Claude is starting (no double restart), buttons locked then too; Design tools add Edit. All 18 AWR-free tests pass (`test_hub`, `test_client`, `test_channel` need `uv run --no-project --with "mcp>=1.2,<2" --with pywin32 python`).
- Second review fix, 25 Nov: the no-ask write rule is narrowed to `designs/` plus `PROGRESS.md`, `errors.md`, `playbook.md`. `hub.py`, `.claude/` (settings, agents), `checks/`, `CLAUDE.md` and every `.emp` now ask, so Claude can't edit its own safety checks silently. Fieldnote + hub tests pass.
- Next: step 6 (live `rc_lpf` to the spec stop).
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
6. Version 3: take the user's plans. v2's known gaps (from the 22 Nov summary): EM designs through the agent loop, larger and active circuits (amplifiers, stability, noise, harmonic balance), Touchstone import, standard part values and tolerance, open-ended specs.

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
