# AWRMWO-mcp v2: agentic circuit design

Status (21 Nov 2026):
- **A done:** `test_agents` OK.
- **B done:** `check_spec`, `check_tidy`, `test_checks` OK on fixtures, and live in AWR. The tidy check passed a clean schematic and flagged a real router-made crossing. The spec check measured −6.257 dB against −6.256 dB by hand. The live run found one bug (the hub unwraps one-item lists); it is fixed and has a test.
- **C done:** `hook_guard`, `hook_tidy`, `.claude/settings.json`, `test_hooks` OK, and live: a session in this folder had `add_equation` refused for a non-`v2_*` document and for a missing `document` (project-wide). Progress is tracked in [PROGRESS.md](PROGRESS.md).
- **D done (21 Nov):** rc_lpf and ne3508_bias reached PASS with complete dossiers; a seeded 10x C1 fault was caught and fixed in 1 round. See PROGRESS.md.
- **E in progress (21 Nov):** E.1 tools done and tested live (eval `lmatch_opt` waits for an MCP restart); E.2 library (4 blocks), E.3 evals (5/6 OK, 1 not run), E.4 prompt, E.5 playbook note, E.6 `run_headless.py` built. See PROGRESS.md.
The GUI was built in v1 (`../AWRMWO-mcp`) as Fieldnote, moved into v2 on 25 Nov 2026 and renamed Ampwright on 26 Nov (see PROGRESS.md).

## Goal

You give a circuit task in plain language ("bias the NE3508M04 at 20 mA, 3 V", "2 GHz 5th-order Chebyshev LPF on FR4"). The agents turn it into a spec, predict the result from theory, build it in AWR, simulate it, check it against the spec and the prediction, fix it if it fails, review it, and report. You approve twice: the spec at the start and the save at the end.

## How Claude Code shapes the design

- **A subagent cannot start other subagents.** The Design Lead is therefore the main Claude Code session opened in this folder. Its instructions are in [CLAUDE.md](CLAUDE.md). Every other role is a subagent in [.claude/agents/](.claude/agents/).
- **Agents talk through files, not conversation.** Each design has a dossier folder. An agent reads what it needs, writes its result, and returns a short report (under 200 words). Context stays small, the run is auditable, and a crashed run can be resumed.
- **Permissions are per agent.** Each agent file lists exactly which tools it may use. No agent has `save_project` or `new_project`, and the read-only agents get only the tools marked `readOnlyHint` in [server.py](server.py).
- **One AWR, one writer.** AWR's COM interface is single-threaded. The Lead never runs two AWR-writing agents at once. Read-only agents and agents that don't touch AWR may run in parallel.

## The loop

```
you ─▶ Lead writes spec ─▶ YOU APPROVE SPEC
        │
        ▼
     Theory ─▶ Builder ─▶ Evaluator ─▶ Judge ──pass──▶ Reviewer ─▶ Lead report ─▶ YOU APPROVE SAVE
                  ▲                       │fail
                  └──── Fixer ◀───────────┘   (max 3 fix rounds, then the Lead asks you)
```

Gate rules:
- The **Judge** decides pass or fail. It never built or fixed anything in that design.
- A **fail** goes to the Fixer with the Evaluator's numbers and the Judge's reason. The Fixer makes the smallest change that addresses that reason, and the Evaluator and Judge run again.
- After 3 failed rounds, or if the Judge says the spec itself is unreachable, the Lead stops and asks you.
- The **Reviewer** runs only after a pass. Its findings (tidiness, naming, stray graphs) go back to the Builder once; then the Judge confirms the numbers didn't change.

## Roster

| Agent | File | Model | AWR | Writes |
|---|---|---|---|---|
| Design Lead (master) | [CLAUDE.md](CLAUDE.md) | your session model (Opus) | read-only | `spec.*`, `state.json`, `report.md` |
| Verification Judge (master) | `verification-judge.md` | Opus | read-only | `verdict.md` |
| Theory | `circuit-theory.md` | Sonnet | none | `theory.md`, `predictions.json` |
| AWR Builder | `awr-builder.md` | Sonnet | write (no save, no new project) | `build_log.md` |
| Evaluator | `circuit-evaluator.md` | Sonnet | read-only | `results.json` |
| Fixer (diagnose + fix) | `circuit-fixer.md` | Sonnet | write (no save, no new project) | `fix_log.md` |
| Reviewer | `design-reviewer.md` | Sonnet | read-only | `review.md` |
| Test runner | `test-runner.md` | Haiku | read-only | nothing; reports numbers |

Diagnosis and fixing are one agent: splitting them doubles the handoffs and each handoff loses context. The Lead may rerun the Fixer on Opus (model override) after two failed rounds.

## The dossier: `designs/<slug>/`

| File | Written by | Content |
|---|---|---|
| `spec.md` | Lead | The task in words, assumptions, what you approved |
| `spec.json` | Lead | Machine-readable goals (format below) |
| `theory.md` | Theory | Topology, hand calculations, component values, why |
| `predictions.json` | Theory | Expected value for every spec goal, same metric names |
| `build_log.md` | Builder | Schematic and graph names, every part and wire, deviations from theory |
| `results.json` | Evaluator | Measured value per goal, from scripted checks |
| `verdict.md` | Judge | PASS or FAIL per goal, spec vs prediction vs measured, reason |
| `fix_log.md` | Fixer | Per round: diagnosis, one change, expected effect |
| `review.md` | Reviewer | Tidiness and hygiene findings |
| `state.json` | Lead | Phase, round, AWR document names, open questions |
| `report.md` | Lead | Final summary for you |

`spec.json`:
```json
{
  "name": "ne3508_bias",
  "class": "bias",
  "schematic": "v2_ne3508_bias",
  "goals": [
    {"id": "id",  "metric": "Id_A", "graph": "v2_ne3508_bias_iv", "at": {"Vds": 3.0}, "op": "within", "value": 0.020, "tol": 0.001},
    {"id": "s11", "metric": "S11_dB", "graph": "v2_x_s", "over_hz": [1.5e9, 2.5e9], "op": "<=", "value": -10}
  ]
}
```
Values are in the trace's base units (A, V, Hz; dB stays dB). Optional `measurement` picks one trace by substring when a graph has several. Supported `op`: `<=`, `>=`, `within` (needs `tol`). A goal reads a measurement from a graph, either at a point (`at`) or as the worst case over a band (`over_hz`).

## Naming and AWR hygiene

- Every document an agent creates is named `v2_<slug>` or `v2_<slug>_<what>`, so it is easy to find and clean up, and never collides with your documents.
- Agents never touch documents they did not create in this design, and never `Schematic 1`.
- No save, no new project: the Lead asks you, and you do it or approve it.
- One graph per measurement set, reused across fix rounds, not a new graph per run.

## The playbook

[playbook.md](playbook.md) holds general lessons (model choices, good defaults). [errors.md](errors.md) is the error catalogue. Each entry gives the exact error text, its cause and fix, a status (fixed-in-code, workaround, open or retired), the version it was seen in, and a recheck. Every agent reads both before working. Only the `lesson-keeper` agent edits them: after every run (mode `run`), and after a version change (mode `upgrade`, which reruns the rechecks and retires stale entries). Other agents leave `Lesson:` lines in their logs. `tests/test_agents.py` enforces this and checks the catalogue format.

## Phases

Each phase has a test that says when it is done.

### Phase A: plan and agents (this document)
- AGENTIC_PLAN.md, CLAUDE.md for the Lead, 7 agent files, playbook.md, `.mcp.json`.
- **Done when:** `tests/test_agents.py` passes. It checks that every agent file has a name, description and model, that every MCP tool it lists exists in server.py, that read-only agents list only read-only tools, and that no agent has save or new-project.

### Phase B: deterministic checks
- `checks/check_spec.py designs/<slug>`: reads spec.json, pulls graph data through the hub pipe (no second COM owner), and writes results.json. The Evaluator runs it; it does not eyeball plots.
- `checks/check_tidy.py <schematic>`: wire crossings, wires over part bodies, overlaps, from `list_wires`/`list_elements`. Enforces the tidiness rule.
- **Done when:** both run without AWR on recorded fixtures (a passing and a failing case each), and live on one sandbox schematic.

### Phase C: guard hooks
- A `PreToolUse` hook blocks `save_project`, `new_project` and deleting a document that isn't `v2_*`.
- A `PostToolUse` hook on `connect` runs check_tidy and returns the crossings to the agent.
- **Done when:** a test call to each blocked tool is refused by the hook, and a crossing wire is reported.

### Phase D: first end-to-end runs
- Run the loop on two known tasks: the NE3508M04 bias point (validated by hand on 20 Nov) and an RC low-pass with a known −3 dB point.
- **Done when:** both reach PASS with a complete dossier, and a deliberately wrong part value is caught and fixed in at most 2 rounds.

### Phase E: scale-up
1. **AWR optimizer and tuner tools:** `add_opt_goal`, `set_opt_variable`, `run_optimizer`, `sweep`. The Fixer sets goals and lets AWR search, instead of changing values one at a time.
2. **Verified block library:** a passing design can be promoted to `library/<block>/`, holding the netlist, spec, results and verdict. Theory and the Builder reuse blocks.
3. **Agent eval suite:** `evals/` with 5–8 tasks that have known answers. `test-runner` runs them after any change to prompts, models or tools, and reports pass rate, rounds and token use per task.
4. **Design-space exploration:** Theory proposes 2–3 topologies in parallel; the Lead picks which to build, one at a time.
5. **Vendor library search** (`search_library`, already approved for v1).
6. **Headless runs** via `claude -p` (the Ampwright app-session mode) for unattended evals.

## Cost rules

- Opus only for the Lead and the Judge. Sonnet does the work. Haiku runs tests.
- Graph data in summary mode; full traces only to check_spec.
- Reports under 200 words; details go to dossier files.
- Max 3 fix rounds per design, then a person decides.

## Risks

- **Subagents can't nest.** If the Lead runs in a subagent (for example from Ampwright), it can't dispatch. The Lead must be the main session.
- **AWR modal dialogs** block COM and stall every agent. The Lead checks `status_messages` and asks you.
- **The Judge reads the same numbers the Evaluator wrote.** Its independence comes from checking the spec, the prediction and the measurement together, and from re-reading the key graph itself.
- **Theory can be wrong.** A large prediction gap is reported, not hidden; the Judge decides whether the theory or the build is at fault.
