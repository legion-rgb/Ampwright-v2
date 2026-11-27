# Ampwright development plan

Goal: drive Cadence AWR Microwave Office (MWO) from Claude Code through MCP. A user describes a circuit, layout or analysis in plain language, and Claude builds it, simulates it, plots it and reports back, without the user touching the GUI.

Status: Phase 0 done. One file, [server.py](server.py), with 9 tools (read status, ports, graphs, simulate, get/set parameters). Tested against AWR DE v17 (22.1) on an empty project only.

## How it works

```
Claude Code ──MCP (stdio)──> Ampwright (Python, uv) ──COM──> MWOffice.exe (the open GUI)
```

- Uses AWR's own COM API (`AWR.MWOffice`), the same one used by AWR's VBA scripts and pyawr.
- Attaches to the running GUI, so the user sees every change as it happens and can step in.
- All COM calls run on one worker thread (COM objects are bound to their thread).

### API coverage (checked against the v17 type library)

| Need | API |
|---|---|
| New schematic / EM structure / graph | `Schematics.Add`, `EMStructures.Add`, `Graphs.Add` |
| Place parts | `Elements.Add(name, x, y, rot, flip)`, `Elements.AddSubcircuit` |
| Wire parts | `Wires.Add(x1, y1, x2, y2)` plus element `Nodes` coordinates |
| EM geometry and ports | `Shapes.AddRectangle / AddPolygon / AddPath / AddVia / AddPort / AddFace`, `EMPorts.Add` |
| Measurements and plots | `Measurements.Add(doc, meas)`, `XValues/YValues`, `ExportTraceData` |
| Frequencies, equations | `Frequencies.AddMultiple`, `Equations.Add` |
| Optimise, tune, sweep | `OptGoals.Add`, `Optimizer.start`, `Tuner`, `Sweeper` |
| Simulate | `Simulator.AnalyzeAsync`, `AnalyzeState`, `EMStructure.Simulate` |
| Files | `Project.Save / SaveAs`, `DataFiles.Import` (Touchstone) |

## Phase 1-3 status (20 Nov 2026)

- Exists: project info/new/save (confirmed only), schematics (create, add_element, add_shunt, connect, add_port, add_ground, delete_element/schematic, list, parameters, equations, netlists), model search, frequencies, graphs (create, add/delete measurement, delete_graph, data, PNG), simulate (whole project async, or one graph blocking), status messages.
- Validated: 54/54 checks against RF theory (RC/RL, series and shunt RLC, TL stubs, quarter-wave, microstrip, FET I-V); shunt notch from add_shunt: -28.28 dB at 1.5915 GHz (theory -28.30).
- Known limits: routing is straight or one L, never detours; wires over part bodies or mid-wire joins other than at ends are only partly detected; graph_data reads the real part only.

## Phase 4 status (20 Nov 2026)

- Exists: create/delete EM structure (AXIEM, Analyst), set_em_stackup (isotropic dielectrics, conductors, enclosure, top/bottom/side boundaries), add_em_shape, add_em_port (edge, lumped_down, lumped_diff, wave, wave_custom), em_info, check_em_setup (lint), set_em_option, EM frequencies.
- Validated: 21/21 checks in tests/validate_em.py. AXIEM two-line eeff within 0.4% of Kirschning-Jansen; air line 1.000 +/-0.3%; stub end-effect ratio within 0.06%; microstrip QWT null -0.6%; 2.4 GHz FR4 patch -2.1%. Analyst line: S11 -23.9 dB, two-line eeff +1.5%.
- Root causes found and fixed: MaterialLayers.Remove leaves the layer in the solver input; DielectricConstant only sets er_z (x/y kept AWR defaults). Dielectrics now go through ExportEmInputDataXML -> rewrite -> ImportEmInputData, and every set is checked against the solver's own input. Analyst needs a real boundary object (DrawingObjects.AddBoundary), not a polygon on EMBoundary.
- Known limits: max 3 dielectric layers; stackup must be set before shapes/ports; shapes can't be deleted via COM; PML not settable; AXIEM S-parameters stay 50 Ohm referenced whatever the port impedance; T-junctions not in the stub theory (constant +2.7% offset); theory's patch edge resistance (Balanis G1/G12, 160 Ohm) disagrees with AXIEM (352 Ohm): check before using inset-feed depths; open (Approx Open) Analyst box not yet tested.
- A COM call cannot be interrupted: tool calls time out after 15 min with an error, but AWR keeps working and later calls queue. Hang seen earlier was not reproduced (6 rounds of simulate+simulate+wait, plus a client killed mid-simulation).

## Phases

Each phase ends with a demo that must work end to end from a Claude Code prompt alone.

### Phase 0: foundation (done)
- Connect to the running AWR. Refuse to start a new one if AWR isn't open.
- Read status messages, EM ports and graph data; simulate; get/set parameters.

### Phase 1: inspect everything
Make Claude able to *see* a project as well as a user can.
- `list_elements`, `list_wires` / nets for a schematic.
- `em_layout`: shapes (layer, coordinates), ports, enclosure, stackup (dielectrics, materials, boundaries).
- `frequencies`, `equations`, `measurements` per graph, `simulation_settings`.
- `open_project`, `save_project`, `save_as` (always to a new file by default).
- Pick the AWR instance by project name when several are open (`InstanceCLSID`).

**Demo:** "Why does trace1 fail to simulate?" Claude reads ports, stackup and errors and gives the diagnosis we reached by hand on 19 Nov (port not on boundary, missing negative terminal), without screenshots.

### Phase 2: simulate and plot
- `set_frequencies(start, stop, step | list)`.
- `create_graph(name, type)`, `add_measurement(graph, source, "DB(|S(1,1)|)")`.
- `graph_image(graph)`: render the data with matplotlib and return it as an MCP image so Claude can look at the curve. More reliable than screen-grabbing the AWR window.
- Long EM runs: `simulate` returns at once, then `simulation_state` / `wait_for_simulation(timeout)`. Never block a tool call for minutes.
- `export_touchstone(doc, path)`, `export_trace_data(graph, path)`.

**Demo:** "Compare S11 of Trace1_S11 and Trace_1_Copper_short from 0.5 to 8 GHz and list the resonances." Claude plots both and reports the dips.

### Phase 3: design schematics
The hardest part for an LLM is placing and wiring by coordinates. Hide that.
- `search_models("microstrip line")`: look up AWR element names (`MLIN`, `MSUB`, `RES`, `CAP`, `PORT`…) and their parameters from `app.Models`, so Claude never guesses names.
- `add_element(schematic, model, params, near=...)`: auto-place on a grid.
- `connect(schematic, "R1:2", "C1:1")`: reads both node coordinates and draws the wire. Claude works in pins and nets, never in x/y.
- `add_port`, `add_ground`, `add_subcircuit(em_structure)`.
- `import_netlist(text)`: alternative path where Claude writes an AWR netlist and imports it. Probably more reliable than wiring for larger circuits; build both and compare.
- `set_equation("W=1.9")` for design variables.

**Demo:** "Design a 2 GHz 5th-order Chebyshev microstrip low-pass filter on FR4 1 mm, simulate S11/S21 1–6 GHz and plot." Check the result against the analytic cut-off.

### Phase 4: EM layout and Analyst setup
- `create_em_structure` with stackup: enclosure, dielectric layers, conductor materials, boundaries (Approx Open / PML).
- `add_shape` (rectangle, polygon, path, ellipse, via) by layer.
- `add_em_port(type=lumped_down | lumped_diff ± | wave | wave_custom)`. Encode the rules learned on this project:
  - a default wave port must sit exactly on the boundary;
  - a differential lumped port needs its `−` terminal on the facing edge;
  - Lumped Down needs ground under it.
- `check_em_setup(em)`: a pre-flight lint run before simulating. It flags these rules, plus air margin < λ/4 at the lowest frequency, an odd number of boundary edges, and ports outside the boundary. Cheap, and saves many failed runs.
- Mesh and AMR settings, then read the convergence from `em_simulation_log`.

**Demo:** rebuild a single-element antenna (or a plain patch) from a text description and simulate it.

### Phase 5: optimise, tune, sweep
- `add_opt_goal`, `run_optimizer(type, iterations)`, report the best values.
- `sweep(variable, values)` with results tabulated.
- Tuner save/restore for "try this, undo that".

**Demo:** "Tune R1 and C1 so S11 < −10 dB from 1.5 to 2.5 GHz."

### Phase 6: harden and release
- Tests (see below), README, example prompts, changelog.
- Move to the `mcp` 2.x SDK (`MCPServer`); currently pinned to v1.
- Package as a `uv` tool or pip package; decide on open-sourcing.

## Testing approach

1. **Unit tests without AWR:** a fake COM object (a few Python classes) for logic such as pin→coordinate wiring, status filtering and the EM pre-flight lint. Runs anywhere, fast.
2. **Live integration tests (needs AWR plus a license):** a pytest fixture opens a throw-away copy of a test project in a temp folder, runs the tool, and checks the result through the API. Never touches real projects.
3. **Golden designs:** a small set of known circuits (50 Ω line, RC low-pass, the Chebyshev LPF) whose S-parameters must match stored reference results within a tolerance. This catches regressions when AWR or the server changes.
4. **Prompt demos:** the phase demos above, run by hand in Claude Code before calling a phase done.

## Rule: tidy schematics (user, 20 Nov 2026)
Wires must never overlap or cross other wires, part bodies or pins; schematics must be clean and easy to read (full text in CLAUDE.md). Open work: teach `helpers.route` / `add_element` placement to avoid visual crossings (the FET_IV demo's gate wire crosses the drain lead), then add a crossing check to the schematic tests.

## Suggestions

- **Safety first for write tools.** Before the first change in a session, save a backup with `SaveAs` to `<name>_backup_<time>.emp`. Never call `Save` on the user's file unless asked. Every write tool returns the old value so it can be undone.
- **Keep an escape hatch, off by default.** A `run_script(python)` tool that executes code against the AWR object is the fastest way to prototype new tools. It is also dangerous, so enable it only with an environment variable such as `AWR_MCP_ALLOW_SCRIPT=1`, and turn the useful scripts into real tools.
- **Work in names and pins, not coordinates.** Every tool should accept element IDs (`R1`), pin names (`R1:2`) and doc names. Coordinates stay inside the server.
- **Return compact data.** Summarise large results (for example 2000-point traces into min/max/resonances) and offer the full data on request. This keeps Claude's context small and responses fast.
- **Add MCP prompts** for common workflows (`diagnose_em_failure`, `design_filter`, `compare_s11`), so users can start a task with one command.
- **Split the file at around 400 lines** into `connection.py`, `tools/schematic.py`, `tools/em.py`, `tools/graphs.py`. One file is fine for now.
- **Log every COM call** to a file in debug mode. AWR errors are often vague, and the call log is what makes them fixable.
- **License and IP:** use only the public COM API, ship no AWR files or docs, and test with your own projects. Check your university's AWR license terms before publishing.

## Decisions (20 Nov 2026)

1. Users: the lab.
2. AWR version: v17 (22.1) only, for now.
3. Order: schematics first. Validation ladder: RC and RL, then FET I-V (a library FET), then transmission lines (quarter-wave transformer, stubs, S11).
4. Saving: never automatic. The server asks the user; `save_project` and `new_project` require `user_confirmed=True`.

## Team setup

- Lead agent: owns the plan, reviews all code, runs the validation verdicts, fixes or sends back errors.
- Builder sub-agent: implements tools against live AWR. Only one agent touches AWR at a time, because there is one COM connection to the GUI.
- Theory sub-agent: `tests/rf_theory.py`, analytic references (ABCD/S-parameters, transmission lines, microstrip, FET I-V). Never touches AWR.
- Validator sub-agent: builds each test circuit through MCP and compares it with `rf_theory.py`.

### Model use (token budget)
- Opus: lead only (planning, review, hard diagnosis).
- Sonnet: building tools, fixing bugs, validation runs.
- Haiku: repeat runs, re-checks, formatting.
- Agents return short reports (verdicts, numbers, file paths); graph data in summary mode; continue existing agents instead of starting new ones.
