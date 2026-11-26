# AWRMWO-mcp

An MCP server that lets Claude Code (or another MCP client) drive Cadence AWR Microwave Office. You describe a circuit, a layout or an analysis in plain language. Claude builds it in the AWR window you have open, simulates it and reads the results back.

As far as we know, no MCP server for AWR Microwave Office existed before this one.

- **AWR version:** AWR Design Environment v17 (22.1). Other versions are untested.
- **Platform:** Windows only. It talks to AWR through COM.
- **Status:** schematic and EM layout tools are built and checked against RF theory. Optimisation and tuning (Phase 5) are not started.

## How it works

```
Claude Code ──MCP (stdio)──> AWRMWO-mcp (Python, run by uv) ──COM──> MWOffice.exe (your open AWR window)
```

The server attaches to the AWR window that is already running, so you watch every change happen and can take over at any point. It never starts AWR on its own. If AWR isn't open, it says so.

## Setup

1. Install AWR DE v17 with a license, and install [uv](https://docs.astral.sh/uv/).
2. Open AWR with your project. Keep only one AWR window open.
3. Open Claude Code in the folder that holds `.mcp.json`. It already registers the server:
   ```json
   {"mcpServers": {"AWRMWO-mcp": {"command": "uv", "args": ["run", "--script", "AWRMWO-mcp/server.py"]}}}
   ```
4. Approve the `AWRMWO-mcp` server when Claude Code asks. Check it with `/mcp`.

There is no separate install step for packages. `server.py` declares its own dependencies (`mcp<2`, `pywin32`, `matplotlib`), and uv installs them on first run.

To check the server without Claude, run this from the folder above `AWRMWO-mcp`:

```
uv run --script AWRMWO-mcp/tests/mcp_call.py project_info '{}'
```

### Ampwright desktop app

Ampwright (called Fieldnote in v1) is a desktop window for AWR work, brought over from v1 on 25 Nov 2026. Open AWR with your project, then double-click `Ampwright.bat` in this folder (needs uv and Microsoft Edge WebView2). It starts Claude Code hidden, on your own subscription login with no API key, and shows the open AWR project. You chat with it, watch each step in the activity feed, stop a turn, and allow or deny save, new project and delete in a dialog. The plan is in [AMPWRIGHT_PLAN.md](AMPWRIGHT_PLAN.md). The older v2 window is archived in `_archive_desktop_v2/`.

Ampwright's hidden session starts in the workspace folder, so it uses the lean setup (AWR server only) and not this folder's agent loop or `v2_*` guard hooks. The agent loop still runs from a Claude Code session opened in this folder.

### GitHub Copilot (VS Code)

The server should also work with Copilot in Agent mode, but this is untested. Add `.vscode/mcp.json`:

```json
{"servers": {"AWRMWO-mcp": {"type": "stdio", "command": "uv",
  "args": ["run", "--script", "${workspaceFolder}/AWRMWO-mcp/server.py"]}}}
```

It only works from VS Code on the PC where AWR runs, not from Copilot's cloud agent.

## What it can do

40 tools, grouped by job.

### Project

| Tool | What it does |
|---|---|
| `project_info` | Name, file, saved state, schematics, EM structures, netlists, graphs |
| `save_project` | Saves, but only with `user_confirmed=True`. Claude must ask you first |
| `new_project` | Closes the project without saving and opens a new one, only with `user_confirmed=True` |

### Schematics

| Tool | What it does |
|---|---|
| `search_models` | Searches AWR's element list (about 1,700 models) by name, description or category |
| `create_schematic`, `delete_schematic` | Make or remove a schematic |
| `add_element` | Places a part on a free grid spot and sets its parameters. Numbers are SI units; any plain number is SI, even sent as text; other strings are expressions or variable names, read in display units (`"2*500"` = 1000 pF). A unit suffix such as `"1000 pF"` fails to simulate. `model: "SUBCKT"` with `NET` places a netlist or schematic as a subcircuit |
| `connect` | Wires two pins by name, such as `R1:2` to `C1:1`, then confirms they share a net |
| `add_port`, `add_ground` | Adds a port or ground wired to a pin |
| `add_shunt` | Hangs a 2-pin part straight down from a pin, with ground on its other end |
| `delete_element` | Removes a part and the wires attached to it |
| `list_elements`, `list_wires` | Shows parts, pins, nets and wires |
| `get_parameters`, `set_parameter` | Reads or changes part values |
| `add_equation` | Adds a variable, such as `Cval=1e-12` |
| `import_netlist` | Adds an AWR-format netlist, for example a vendor device model |

You and Claude work in part IDs and pin names. Coordinates stay inside the server. The wiring code refuses any route that would touch another pin or land mid-way on another wire, because AWR would silently join them.

### Simulation and results

| Tool | What it does |
|---|---|
| `set_frequencies` | Sets the sweep for the project, one schematic or one EM structure |
| `create_graph`, `delete_graph` | Rectangular, polar, Smith, tabular and other graph types |
| `add_measurement`, `delete_measurement` | For example `DB(\|S(2,1)\|)`, `IVCurve(IV1)` or `IDC(DCVS.VD,1)`. `simulator` picks the engine, such as `aplac_dc` for APLAC models |
| `simulate` | Whole project (returns at once), or one graph only (waits for it), so a broken schematic elsewhere doesn't stop you |
| `wait_for_simulation`, `simulation_state` | Waits for a run, or reports its state and errors |
| `graph_data` | Results in SI units, with trace labels and units. `summary=True` gives min, max and where they occur |
| `graph_image` | Plots a graph as a PNG that Claude can look at. Curves are labelled by swept value, and axes carry units |
| `status_messages`, `clear_status_messages` | Reads or clears AWR's Status Window |
| `opt_state` | Optimizer goals with their cost, flagged parameters with bounds, and the optimizer methods |
| `set_opt_variable`, `add_opt_goal`, `delete_opt_goals` | Flag a parameter (SI bounds) and add or remove goals such as `DB(\|S(1,1)\|) < -20` over a band |
| `run_optimizer` | Runs the AWR optimizer (Simplex by default) for one schematic. Refuses if another document has goals or flags |
| `sweep` | Tries a list of values for one parameter and returns the measurement at one frequency, then restores the old value |

### EM layout (AXIEM and Analyst)

| Tool | What it does |
|---|---|
| `create_em_structure`, `delete_em_structure` | AXIEM (planar) or Analyst (3D FEM). Analyst structures get a real simulation boundary |
| `set_em_stackup` | Dielectric layers, conductors, enclosure, and top, bottom and side boundaries. Every change is checked against the solver's own input file |
| `add_em_shape` | Rectangle, polygon, path, ellipse or via, in mm |
| `add_em_port` | Edge, lumped down, lumped differential (±), wave and custom-size wave ports |
| `em_info`, `em_ports` | Stackup, layers, boundary, shapes and ports |
| `check_em_setup` | Checks the setup before you simulate (see below) |
| `set_em_option` | Sets one EM option, such as Analyst's mesh-refinement tolerance |
| `em_simulation_log` | End of the solver log: mesh, convergence, errors |

`check_em_setup` catches the mistakes we hit by hand on a real antenna project:
- port numbers that skip a number;
- a wave port that isn't on the boundary edge;
- a custom wave port box outside the boundary;
- a differential port with no − terminal;
- a lumped-down port with no ground under it;
- a port that touches no shape;
- too little air (less than λ/4) around a radiating structure;
- a boundary that isn't a plain rectangle, or no boundary at all.

## How it was checked

Every circuit was built through the MCP tools and compared with an independent analytic reference, `tests/rf_theory.py`. That module uses ABCD matrices, transmission-line theory, Hammerstad-Jensen and Kirschning-Jansen microstrip formulas, Hammerstad-Bekkadal open-end correction, the Balanis cavity model, and Curtice, Statz and Angelov FET equations. It has 103 self-checks of its own.

### Schematics: 71 of 71 checks pass (`tests/validate.py`)

| Circuit | Result |
|---|---|
| RC, RL low-pass and RL high-pass | Curves match theory to under 0.01 dB; corners at 3.33 MHz, 119.4 MHz and 52.9 MHz |
| Series RLC, pass and notch | f₀ = 1591.5 MHz, bandwidth 160.75 MHz, notch −28.29 dB (theory −28.30) |
| λ/4 transformer, 50 Ω to 100 Ω | S11 nulls at 2 and 6 GHz, −20 dB bandwidth 36.70% |
| λ/4 open and shorted stubs, λ/2 line | Notches and phases exact |
| Microstrip on FR4 | ε_eff matches Kirschning-Jansen |
| FET I-V, CURTICE2 | Within 0.016% of the Curtice equation |
| FET I-V, ANGELOV | Within 0.002% of the Angelov equation, including RS and RD |

### EM: 21 of 21 checks pass (`tests/validate_em.py`)

| Structure | Result |
|---|---|
| AXIEM 50 Ω line on FR4, two-line ε_eff | Within 0.4% of Kirschning-Jansen at 1, 2 and 3 GHz |
| AXIEM air line (ε_eff must be 1) | 0.999 to 1.003 |
| AXIEM open stub, end effect | Ratio of two stub notches within 0.06% of theory |
| AXIEM microstrip λ/4 transformer | Null within 0.6% of 2 GHz |
| AXIEM 2.4 GHz FR4 patch | Resonance at 2.349 GHz, 2.1% from the cavity model |
| Analyst 50 Ω line with wave ports | S11 −23.9 dB, ε_eff within 1.5% |

### Device demo: NE3508M04

The Renesas NE3508M04 HJ-FET was loaded from AWR's Renesas library as a netlist and placed as a subcircuit. Its I-V family was plotted, and it was biased in the linear region at Vgs = 0 V, Vds = 0.1 V. The DC simulation gives Ids = 20.36 mA, the same value as the I-V curve.

### Running the tests

From the folder above `AWRMWO-mcp`:

```
python AWRMWO-mcp/tests/test_pins.py                    # wiring logic, no AWR needed
python AWRMWO-mcp/tests/test_em.py                      # EM lint logic, no AWR needed
uv run --script AWRMWO-mcp/tests/rf_theory.py           # the theory module's own self-checks
uv run --with numpy AWRMWO-mcp/tests/validate.py        # schematic results against theory
uv run --with numpy AWRMWO-mcp/tests/validate_em.py     # EM results against theory
```

The `validate` scripts compare saved results in `tests/_out/`. To refresh them, re-run the circuit batches in `tests/circuits/` with `tests/mcp_call.py --batch`, in a fresh untitled project.

## Problems found and fixed along the way

These are worth knowing about if you script AWR yourself.

- **`MaterialLayers.Remove` doesn't really remove a layer.** The API reported 2 layers while the solver still saw a third: 0.1 mm of εr 12.9 under the substrate.
- **`DielectricConstant` only sets the vertical (z) permittivity.** x and y kept AWR's defaults, so every "FR4" was anisotropic. The fix edits the EM input file and imports it back.
- **Analyst needs a real boundary object** (`DrawingObjects.AddBoundary`). A polygon drawn on the EMBoundary layer doesn't count.
- **The measurement simulator is chosen in the source name**, as `<schematic>.<simulator>`, for example `AP_IV.AP_DC`.
- **Subcircuits need `Elements.AddSubcircuit`.** `Elements.Add("SUBCKT")` fails.
- **`add_shunt` turned a DC source sideways and shorted two nets.** It now tries rotations until the part really hangs straight down.
- **Swept complex data needs `TraceValues(k)`.** `YValues(k)` returns data dimension k, not trace k.

## Safety

- Nothing is saved without your say-so. `save_project` and `new_project` refuse unless `user_confirmed=True`.
- Reusing a conductor name with different values is refused, because conductors are shared across the whole project.
- Every tool call has a hard timeout, so no call can block forever.
- There is no tool that runs arbitrary scripts inside AWR.

## Known limits

- **Schematic layout:** routing is straight or one L-shape, with no detours. Wires can still cross or run past part bodies, so check each schematic by eye. The project rule is no crossings at all (see `../CLAUDE.md`), and the router doesn't enforce it yet.
- **Pin order differs between models,** for example EEFET3_AP is drain, gate, source and ANGELOV is gate, drain, source. `search_models` doesn't return pin names.
- **Vendor libraries:** `search_models` only searches AWR's element list. Parts in the Libraries tree, such as Renesas devices, have to be found on disk and imported with `import_netlist`. A `search_library` tool was started but not finished.
- **EM through the API:** at most 3 dielectric layers. The stackup must be set before drawing. Shapes can't be deleted. PML boundaries can't be set. AXIEM S-parameters stay referenced to 50 Ω whatever the port impedance.
- **Not tested:** an open (Approx Open) Analyst box, GitHub Copilot, and AWR versions other than v17.
- **Results:** `graph_data` returns only the real part of complex traces.
- **Multiple AWR windows:** the server attaches to whichever one AWR hands out.

## Files

| Path | Contents |
|---|---|
| `server.py` | Entry point and the MCP tools |
| `connection.py` | Attaching to AWR; the single COM thread with timeouts |
| `schematic.py` | Parts, wiring, ports, parameters, netlists |
| `graphs.py` | Frequencies, simulation, graphs, data, plots |
| `optimize.py` | Optimizer goals, variables, runs, and parameter sweeps |
| `em.py` | EM structures, stackup, shapes, ports, boundary |
| `helpers.py` | Pure logic with no AWR: routing, placement, EM lint |
| `PLAN.md` | Development plan, phase status and decisions |
| `tests/` | Theory module, test harness, circuit batches, validation scripts |

## Roadmap

- **Phase 5:** optimiser goals, tuning and parameter sweeps.
- **Library search:** find and load vendor parts by name.
- **Tidy layout:** routing that avoids crossings and part bodies.
- **Phase 6:** move to the `mcp` 2.x SDK (currently pinned to v1), packaging, and more AWR versions.
