# Ampwright

Design RF circuits in Cadence AWR Microwave Office by describing them in plain language. Claude builds the schematic in your open AWR window, simulates it, checks the result against theory and fixes what fails.

```
Claude Code ──MCP──> Ampwright (Python) ──COM──> your open AWR window
```

- **Needs:** Windows, AWR Design Environment v17 (22.1) with a license, [uv](https://docs.astral.sh/uv/), Claude Code. Other AWR versions are untested.
- **Safe by design:** nothing is saved without your yes, no tool runs arbitrary scripts in AWR, and every call has a timeout.

## Quick start

1. Open AWR with your project (one AWR window only).
2. Open Claude Code in this folder. `.mcp.json` registers the server; approve it and check with `/mcp`.
3. Ask: *"Design a matching network for a 50 Ω source and a 250 Ω load at 50 MHz."*

Desktop app: double-click `Ampwright.bat` (needs Microsoft Edge WebView2). It runs Claude Code hidden and uses the Claude Code login on that PC, no API key. Sign in once by running `claude` and `/login`.

## What it does

**Design loop.** Claude Code acts as Design Lead and runs subagents that talk through files in `designs/<slug>/`:

```
spec (you approve) -> theory -> build -> evaluate -> judge --pass--> review -> report
                                  ^                     | fail
                                  +------- fix <--------+   (3 failed rounds, then it asks you)
```

Agents are in [.claude/agents/](.claude/agents/); the rules are in [CLAUDE.md](CLAUDE.md) and [AGENTIC_PLAN.md](AGENTIC_PLAN.md). Scripted checks in `checks/` enforce tidy schematics and `v2_*` document names.

**Clean output.** Schematics are wired without crossings or shorts. Graphs get round axes that reach the deepest null, readable colours and markers, and the schematic and graphs are stacked in view-all windows.

**Tools (53).** Schematics (parts, wiring, ports, parameters, netlists), simulation and graphs (sweeps, measurements, axes, traces, markers, data, images), the optimizer, and EM layout (AXIEM and Analyst: stackup, shapes, ports, setup checks). Full list in `server.py`.

## Checked against theory

Circuits built through the tools match independent analytic references in `tests/rf_theory.py`: RC/RL/RLC filters (under 0.01 dB), λ/4 transformers and stubs, microstrip ε_eff, FET I-V models, and AXIEM/Analyst structures (within 0.4% to 2%). Designed so far through the loop: RC and Chebyshev filters, a notch, a λ/4 transformer, a FET bias, and two L-match networks.

```
uv run --script tests/mcp_call.py project_info '{}'   # check the server without Claude
python tests/test_hooks.py                           # unit tests need no AWR
uv run --with numpy tests/validate.py                # schematic results against theory
```

## Known limits

- The router does not yet avoid wires crossing or running past part bodies, so check each schematic by eye.
- Pin order differs between models, and vendor library parts must be imported with `import_netlist`.
- EM through the API: at most 3 dielectric layers, no shape deletion, no PML boundaries.
- `graph_data` returns only the real part of complex traces. Log-scale axes are not set by `tidy_graph`.
- Not tested: GitHub Copilot, other AWR versions.

## Files

| Path | Contents |
|---|---|
| `server.py`, `connection.py` | MCP tools; attaching to AWR on one COM thread |
| `schematic.py`, `graphs.py`, `optimize.py`, `em.py`, `helpers.py` | Parts and wiring; simulation and graphs; optimizer; EM; pure logic |
| `ampwright/`, `Ampwright.bat` | Desktop app |
| `.claude/`, `checks/` | Agents, settings, guard hooks, spec and tidiness checks |
| `designs/` | One dossier per design (spec, theory, results, verdict, report) |
| `errors.md`, `playbook.md` | Known errors and lessons |
| `tests/` | Theory module, harness, validation scripts |
| [PROGRESS.md](PROGRESS.md) | Current state and next steps |

## Roadmap

Layout routing without crossings, theory training (`rf_design.py`), power-amplifier workflow (HB, load-pull), vendor library search, more AWR versions.
