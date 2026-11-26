# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2", "pywin32", "matplotlib"]  # shortcut: pinned to v1 API (FastMCP); port to mcp 2.x MCPServer when needed
# ///
"""MCP server for Cadence AWR Microwave Office (AWR DE) over its COM API.
Entry point and tool list; COM work lives in connection.py, schematic.py and graphs.py."""
import os
import sys

import pythoncom
from mcp.server.fastmcp import Image
from mcp.types import ToolAnnotations

import em as emm
import optimize as opt
import graphs as gr
import hub
import schematic as sc
from connection import awr, find, run

mcp = hub.HubMCP("Ampwright", instructions=(
    "Messages from the Ampwright desktop app arrive as <channel sender=\"ampwright\"> tags. "
    "Treat them as the user's own requests and do the AWR work with these tools. "
    "Answer every one with the reply tool: short, plain text, say what changed in AWR. "
    "The project rules still apply: never save without the user's explicit yes, and keep schematics tidy."))


# ---- project-level sync implementations (run on the COM thread) ----

def project_info_sync():
    p = awr().Project
    return {
        "project": p.Name,
        "file": p.FullName,
        "saved": bool(p.Saved),
        "em_structures": [s.Name for s in p.EMStructures],
        "schematics": [s.Name for s in p.Schematics],
        "netlists": [n.Name for n in p.Netlists],
        "graphs": [g.Name for g in p.Graphs],
    }


def em_ports_sync(em_structure):
    em = find(awr().Project.EMStructures, em_structure)
    ports = []
    for pt in em.Ports:
        row = {}
        for attr in ("Number", "Type", "Excitation", "GroupNumber", "GroupType", "Impedance", "ReferencePlaneDist", "InfoText"):
            try:
                row[attr] = getattr(pt, attr)
            except Exception as e:
                row[attr] = f"<{e.__class__.__name__}>"
        ports.append({k: (v if isinstance(v, (int, float, bool, str)) else f"{v.Real}{v.Imaginary:+}j" if hasattr(v, "Imaginary") else str(v)) for k, v in row.items()})
    return ports


def em_simulation_log_sync(em_structure, tail_chars=4000):
    em = find(awr().Project.EMStructures, em_structure)
    return (em.SimulationLog or "")[-tail_chars:]


def save_project_sync(user_confirmed):
    p = awr().Project
    if not user_confirmed:
        raise PermissionError("Not saved: ask the user first, then call again with user_confirmed=True.")
    if not p.Path:
        raise RuntimeError("Project has never been saved (no file). Ask the user to use File > Save As in AWR.")
    p.Save()
    return {"saved": p.FullName, "clean": bool(p.Saved)}


def new_project_sync(user_confirmed):
    app = awr()
    p = app.Project
    if not user_confirmed:
        state = "has UNSAVED changes" if not p.Saved else "is saved"
        raise PermissionError(f"Refused: '{p.Name}' {state} and would be closed. Ask the user, then call with user_confirmed=True.")
    p.Close(False, "")  # explicit discard; app.New alone may pop a modal 'save changes?' dialog
    app.New("")
    p = app.Project
    # New("") normally embeds default.lpf; if a project ever comes up without it, import it from the install folder (read-only)
    if not any(pd.Name == "default.lpf" for pd in p.ProcessDefinitions):
        p.ProcessDefinitions.Import(os.path.join(app.Directories(1), "default.lpf"), True)
    return {"project": p.Name, "process_definitions": [pd.Name for pd in p.ProcessDefinitions]}


# ---- MCP tools: project ----

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def project_info() -> dict:
    """Open AWR project: name, file path, saved state, EM structures, schematics, netlists and graphs."""
    return await run(project_info_sync)


@mcp.tool()
async def save_project(user_confirmed: bool = False) -> dict:
    """Save the open project to its file. NEVER call this on your own: ask the user first and only pass
    user_confirmed=True after they said yes. Refuses never-saved (Untitled) projects."""
    return await run(save_project_sync, user_confirmed)


@mcp.tool()
async def new_project(user_confirmed: bool = False) -> dict:
    """Close the open project WITHOUT saving and start a new empty one. Unsaved changes are lost. Ask the user first
    and only pass user_confirmed=True after they said yes."""
    return await run(new_project_sync, user_confirmed)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def em_ports(em_structure: str) -> list:
    """List the ports of an EM structure (number, type, excitation, group, impedance)."""
    return await run(em_ports_sync, em_structure)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def em_simulation_log(em_structure: str, tail_chars: int = 4000) -> str:
    """Tail of an EM structure's simulation log (mesh, AMR convergence, solver output)."""
    return await run(em_simulation_log_sync, em_structure, tail_chars)


# ---- MCP tools: EM layout (AXIEM / Analyst); millimetres everywhere ----

@mcp.tool()
async def create_em_structure(name: str, simulator: str = "AXIEM") -> dict:
    """Create an EM structure. simulator: 'AXIEM' (planar 2.5D, default) or 'Analyst' (3D FEM). It starts with AWR's
    3-layer demo stackup in a 0.8 mm box; call set_em_stackup next. Analyst structures also get their rectangular
    simulation boundary (Approx Open on all four edges); without it Analyst cannot export or simulate."""
    return await run(emm.create_em_structure_sync, name, simulator)


@mcp.tool()
async def delete_em_structure(name: str) -> dict:
    """Delete an EM structure and its shapes and ports."""
    return await run(emm.delete_em_structure_sync, name)


@mcp.tool()
async def set_em_stackup(em: str, dielectrics: list[dict] | None = None, conductors: list[dict] | None = None,
                         enclosure: dict | None = None, boundaries: dict | None = None) -> dict:
    """Define the stackup of an EM structure; every part is optional. dielectrics: top to bottom, 1-3 layers (a limit of
    the AWR COM API), each {thickness_mm, er, tand}, isotropic (er and tand equal in x, y, z; the result's solver_stackup shows what the solver reads and the call fails if it differs). EM layer k is the interface above dielectric k (1 = top lid), so a
    trace on EM layer 2 sits on the first dielectric's floor. conductors: [{name, thickness_mm, sigma (S/m) | 'perfect',
    em_layer (default 2)}]; each becomes a drawing layer called `name` for add_em_shape. enclosure: {x_mm, y_mm, grid_mm}
    (box spans 0..x, 0..y). boundaries: {top, bottom} from perfect_conductor, real_conductor, approx_open,
    infinite_waveguide (PML is not settable via COM). sides: AXIEM walls are always perfect conductor; Analyst takes one value for
    all four edges or {left, right, top, bottom} from perfect_conductor, approx_open, infinite_waveguide (default approx_open;
    setting enclosure redraws the boundary to 0..x, 0..y and keeps the edge values). Returns em_info."""
    return await run(emm.set_em_stackup_sync, em, dielectrics, conductors, enclosure, boundaries)


@mcp.tool()
async def set_em_option(em: str, name: str, value: float) -> dict:
    """Set a solver option of one EM structure by name, e.g. Em3DP_AMR_Tolerance (Analyst adaptive mesh error target,
    default 0.02; 0.005 gave a clean 41 mm microstrip), Em3DP_AMR_MaxIterations, Em3DP_RelativeMeshSize. An unknown name lists
    the Analyst/mesh options. Returns old and new value."""
    return await run(emm.set_em_option_sync, em, name, value)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def em_info(em: str) -> dict:
    """Everything about an EM structure in mm: simulator, dielectrics, enclosure, boundaries, mapped layers (EM layer +
    material + drawing layer name), frequencies, shapes (id, layer, bbox) and ports (number, kind, segment, impedance...)."""
    return await run(emm.em_info_sync, em)


@mcp.tool()
async def add_em_shape(em: str, kind: str, layer: str, x: float | None = None, y: float | None = None,
                       w: float | None = None, h: float | None = None, points: list[list[float]] | None = None,
                       width: float | None = None) -> dict:
    """Draw a shape (mm). kind: rect/ellipse/via (x, y = lower-left of the box, w, h), polygon (points [[x, y]...]) or
    path (points, width). layer: a drawing layer name from set_em_stackup/em_info, or '<em_layer>:<material>' such as
    '2:Perfect Conductor'. Returns id, n_on_layer (use at={'layer': .., 'n': ..} for ports) and bbox. Shapes cannot be deleted via COM."""
    return await run(emm.add_em_shape_sync, em, kind, layer, x, y, w, h, points, width)


@mcp.tool()
async def add_em_port(em: str, type: str, at: dict, number: int | None = None, impedance: float = 50,
                      excitation: bool | None = None, negative_of: int | None = None, extent_mm: float | None = None,
                      deembed: bool | None = None) -> dict:
    """Add a port snapped to a shape edge. type: edge (AXIEM, or Analyst default), lumped_down, lumped_diff, wave,
    wave_custom (Analyst only). at: {'layer': name, 'n': 1, 'edge': 'left|right|top|bottom'} (n-th shape on that layer; stable), {'shape': id, 'edge': ..}
    (id from add_em_shape; AWR sorts shapes by layer so ids can shift) or {'p1': [x, y], 'p2': [x, y]} in mm. number: default next free. lumped_diff: add the + port, then a second one on the facing edge with
    negative_of=<that number> (stored as port -N). wave_custom: extent_mm sets the height only. Returns the port."""
    return await run(emm.add_em_port_sync, em, type, at, number, impedance, excitation, negative_of, extent_mm, deembed)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def check_em_setup(em: str, radiating: bool = False) -> list:
    """Pre-flight lint of an EM structure before simulating: port numbering, wave port off the boundary edge, custom wave
    box outside, lumped_diff without its negative, lumped_down without ground, port not on a shape, air margin < lambda/4
    at the lowest frequency (an error for Analyst only if the top or a side is open or radiating=True, else a warning),
    missing or non-rectangular Analyst boundary, no ports. Returns [{severity, rule, message}]; [] is clean."""
    return await run(emm.check_em_setup_sync, em, radiating)


# ---- MCP tools: schematic design ----

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def search_models(query: str, limit: int = 20) -> dict:
    """Search the AWR element library by name, description or category (all words must match), e.g. 'RES',
    'microstrip line', 'MSUB', 'port', 'ground', 'IV curve', 'swept variable', 'GaAs FET'. Returns exact model names,
    pin count and parameter names. First call reads the whole library (about 15 s)."""
    return await run(sc.search_models_sync, query, limit)


@mcp.tool()
async def create_schematic(name: str) -> dict:
    """Create a new, empty schematic in the open project."""
    return await run(sc.create_schematic_sync, name)


@mcp.tool()
async def add_element(schematic: str, model: str, params: dict | None = None, id: str | None = None,
                      rotation: int = 0, near: str | None = None) -> dict:
    """Place an element (exact model name from search_models, e.g. 'RES', 'CAP', 'MLIN') on a free grid spot.
    params: {'R': 1000} - numbers are SI units (Ohm, F, H, m, Hz, and RADIANS for angles: 90 deg electrical
    length is 1.5707963), even when sent as text ('4.77e-10'). Other strings are expressions or variable names
    from add_equation, read in display units ('2*500' = 1000 pF); a unit suffix such as '1000 pF' fails to simulate. id: e.g. 'R1' (AWR picks one if omitted).
    rotation: 0/90/180/270 degrees; a 2-pin part at 0 runs left->right (pin 1 left), at 270 top->bottom (pin 1 on
    top), handy for shunt parts. near: element id to place it next to. Returns the element with its pins."""
    return await run(sc.add_element_sync, schematic, model, params, id, rotation, near)


@mcp.tool()
async def connect(schematic: str, from_pin: str, to_pin: str) -> dict:
    """Wire two pins, written 'ID:pin' like 'R1:2' and 'C1:1' (pins from list_elements). Reports whether AWR
    sees them on the same net afterwards."""
    return await run(sc.connect_sync, schematic, from_pin, to_pin)


@mcp.tool()
async def add_port(schematic: str, pin: str, number: int | None = None, z0: float = 50) -> dict:
    """Add a PORT wired to a pin ('R1:1'), placed on the side the pin faces. number: port number (AWR picks the
    next one if omitted). z0: port impedance in Ohm."""
    return await run(sc.add_port_sync, schematic, pin, number, z0)


@mcp.tool()
async def add_ground(schematic: str, pin: str) -> dict:
    """Add a GND wired to a pin, e.g. 'C1:2'."""
    return await run(sc.add_ground_sync, schematic, pin)


@mcp.tool()
async def delete_element(schematic: str, element: str) -> dict:
    """Delete an element by id ('R1', 'GND#2') or full name, plus the wires attached to its pins (followed through
    plain corners; the far end stays if other wires meet there). Returns how many wires were removed."""
    return await run(sc.delete_element_sync, schematic, element)


@mcp.tool()
async def add_shunt(schematic: str, pin: str, model: str, params: dict | None = None, id: str | None = None) -> dict:
    """Hang a 2-pin part (RES, IND, CAP...) straight down from a pin ('T1:2'): its pin 1 is wired to that pin and a
    GND is wired to its pin 2. params/id as in add_element. To build a series chain to ground, delete_element the
    returned ground, then add_shunt again on '<part>:2'. Refuses if the wire would touch another pin."""
    return await run(sc.add_shunt_sync, schematic, pin, model, params, id)


@mcp.tool()
async def delete_schematic(name: str) -> dict:
    """Delete a schematic and everything in it. Measurements on graphs that use it will error."""
    return await run(sc.delete_schematic_sync, name)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_elements(schematic: str) -> list:
    """Every element in a schematic: name ('RES.R1'), id ('R1', or 'GND#2' for repeated unnamed parts), model,
    parameters and pins. Pin numbers are what connect() takes ('R1:2'); 'net' is AWR's node number, equal for
    connected pins; x/y are for debugging only."""
    return await run(sc.list_elements_sync, schematic)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_wires(schematic: str) -> list:
    """Wire segments of a schematic (coordinates and net name), mainly for debugging connections."""
    return await run(sc.list_wires_sync, schematic)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_parameters(schematic: str, element: str) -> dict:
    """Parameters of a schematic element. element: full name ('RES.R1') or ID ('R1')."""
    return await run(sc.get_parameters_sync, schematic, element)


@mcp.tool()
async def set_parameter(schematic: str, element: str, parameter: str, value: float | str) -> dict:
    """Set a schematic element parameter. A number is SI (C1 'C' = 1e-9 means 1 nF); a string is an
    expression or variable name in display units ('Cval', '2*500' = 1000 pF). Any plain number is SI, even sent
    as text ('4.775e-9' = 4.775 nF, '477.5' = 477.5 F). A unit suffix ('4775 pF') fails to simulate. Check with
    get_parameters. Not saved."""
    return await run(sc.set_parameter_sync, schematic, element, parameter, value)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def opt_state() -> dict:
    """Optimizer goals (with cost), parameters flagged for optimization (value, SI value, bounds), the current
    method and every method name."""
    return await run(opt.opt_state_sync)


@mcp.tool()
async def set_opt_variable(schematic: str, element: str, parameter: str, optimize: bool = True,
                           lower: float | None = None, upper: float | None = None) -> dict:
    """Flag a parameter for the optimizer, with lower/upper bounds in SI units (C: F, L: H, TLIN EL: radians).
    optimize=False clears the flag. Not saved."""
    return await run(opt.set_opt_variable_sync, schematic, element, parameter, optimize, lower, upper)


@mcp.tool()
async def add_opt_goal(schematic: str, measurement: str, op: str, value: float, start_hz: float, stop_hz: float,
                       weight: float = 1.0) -> dict:
    """Add an optimizer goal on a measurement of the schematic, e.g. measurement='DB(|S(1,1)|)', op '<', value -20,
    over start_hz..stop_hz (equal for one point). op: '<', '>' or '='. value is in the measurement's unit (dB for
    DB(...)). Returns the goal's cost from the last simulation (0 = met; simulate first, or it is stale)."""
    return await run(opt.add_opt_goal_sync, schematic, measurement, op, value, start_hz, stop_hz, weight)


@mcp.tool()
async def delete_opt_goals(schematic: str) -> dict:
    """Remove every optimizer goal on this schematic."""
    return await run(opt.delete_opt_goals_sync, schematic)


@mcp.tool()
async def run_optimizer(schematic: str, method: str = "Simplex Optimizer", iterations: int = 200,
                        timeout_s: int = 300) -> dict:
    """Run the AWR optimizer on this schematic's goals and flagged parameters, and return start/best cost and the
    final values. Refuses if any other document has enabled goals or optimize flags. Stops early at cost 0.
    Changes the parameter values in AWR (not saved); re-simulate before reading graphs."""
    return await run(opt.run_optimizer_sync, schematic, method, iterations, timeout_s, timeout=timeout_s + 60)


@mcp.tool()
async def sweep(schematic: str, element: str, parameter: str, values: list[float | str], graph: str,
                measurement: str, at_hz: float) -> dict:
    """Try each value of one parameter (same value rules as set_parameter), simulate the graph each time and
    return the measurement at at_hz as a table. The old value is restored and re-simulated afterwards."""
    return await run(opt.sweep_sync, schematic, element, parameter, values, graph, measurement, at_hz)


@mcp.tool()
async def add_equation(expression: str, document: str | None = None) -> dict:
    """Add an equation/variable such as 'Cval=1e-12'. Goes to Global Definitions by default, or into the named
    schematic. Use the variable in element parameters as a string, e.g. params={'C': 'Cval'}."""
    return await run(sc.add_equation_sync, expression, document)


@mcp.tool()
async def import_netlist(name: str, text: str) -> dict:
    """Create an AWR-format netlist document, usable as a measurement source like a schematic. Example:
    'DIM\\n FREQ HZ\\n RES OH\\n CAP F\\nCKT\\n RES 1 2 ID=R1 R=1000\\n CAP 2 0 ID=C1 C=1e-9\\n DEF2P 1 2 <name>\\n'
    (node 0 is ground; DEF2P/DEF1P... define the ports on nodes, last argument is the netlist name)."""
    return await run(sc.import_netlist_sync, name, text)


# ---- MCP tools: simulate and plot ----

@mcp.tool()
async def set_frequencies(start_hz: float | None = None, stop_hz: float | None = None, points: int | None = None,
                          step_hz: float | None = None, log: bool = False, document: str | None = None,
                          around_hz: float | None = None) -> dict:
    """Set the sweep: give start_hz and stop_hz with points (linear, or log=True for log spacing) or step_hz (linear).
    If the user gave no frequency or range at all, ask them for the frequency points (start, stop, step) before calling
    this; never guess a sweep. If the user names one frequency f, pass only around_hz=f: the sweep is f/4 to 2.5 f in steps of f/8 (200 kHz gives
    50 to 500 kHz, step 25 kHz). Points are rounded to 2 decimals in the sweep's own unit (kHz stays kHz, never MHz or
    GHz) and AWR's frequency unit is switched to match; the result's unit/first/last are in that unit.
    Project frequencies by default; with document (a schematic or EM structure name) only that document gets its own sweep."""
    return await run(gr.set_frequencies_sync, start_hz, stop_hz, points, step_hz, log, document, around_hz)


@mcp.tool()
async def create_graph(name: str, type: str = "rectangular") -> dict:
    """Create a graph. type: rectangular, rectangular_complex, polar, smith, tabular, antenna, histogram, 3d, constellation."""
    return await run(gr.create_graph_sync, name, type)


@mcp.tool()
async def tidy_graph(graph: str) -> dict:
    """Make a graph read like an engineer's plot: round axis ends and 1/2/5 steps that cover every point (the y axis always
    reaches the deepest dip or highest peak; only nulls >150 dB below the peak are cut as numerical noise), axis titles with units, distinct colour-blind-safe trace colours, short legend text, no symbols on dense
    traces, no stray second y axis. Needs simulated data; simulate(graph=...) already does this. Returns the axes set."""
    return await run(gr.tidy_graph_sync, graph)


@mcp.tool()
async def set_graph_axis(graph: str, axis: str = "y", min: float | None = None, max: float | None = None,
                         step: float | None = None, auto: bool = False, label: str | None = None) -> dict:
    """Set a graph axis (axis: x, y or y2). min/max fix the range (e.g. min=-60, max=0 for a dB plot), step is the
    major grid step (e.g. 10 gives ticks at 0, 10, 20...), label is the axis title. Values are in the graph's display
    units (dB, GHz, mA...). auto=True gives the axis back to AWR. Run simulate first: AWR has no range before data exists.
    Returns the axis as it now stands, so check it."""
    return await run(gr.set_graph_axis_sync, graph, axis, min, max, step, auto, label)


@mcp.tool()
async def set_graph_trace(graph: str, trace: str | int | None = None, color: str | None = None, dash: str | None = None,
                          symbol: str | None = None, symbol_size: int | None = None, legend: str | None = None) -> dict:
    """Style traces on a graph. trace: omit for all, a 1-based index, or part of a measurement name ('S(2,1)').
    color: '#RRGGBB'. dash: solid, thick, thin or thick_thin. symbol: none, triangle, square, diamond, x, horizontal_bar,
    vertical_bar, forward_slash, back_slash, arrow, circle, small_x or cross. symbol_size: AWR default is 5.
    legend: legend text. Returns each trace as it now stands."""
    return await run(gr.set_graph_trace_sync, graph, trace, color, dash, symbol, symbol_size, legend)


@mcp.tool()
async def add_graph_marker(graph: str, measurement: str | int, x: float) -> dict:
    """Put a marker on a graph at x (sweep value in base units, e.g. 2e9 for 2 GHz). measurement: its 1-based index or
    part of its name ('S(2,1)'). Needs simulated data. Returns the marker's sweep value and the data value read there."""
    return await run(gr.add_graph_marker_sync, graph, measurement, x)


@mcp.tool()
async def clear_graph_markers(graph: str) -> dict:
    """Remove every marker from a graph."""
    return await run(gr.clear_graph_markers_sync, graph)


@mcp.tool()
async def add_measurement(graph: str, source_doc: str, measurement: str, simulator: str | None = None) -> dict:
    """Add a measurement to a graph, e.g. source_doc='RC', measurement='DB(|S(2,1)|)' or 'DB(|S(1,1)|)'.
    simulator: omit for the default; models ending in _AP (APLAC) need an APLAC one, e.g. 'aplac_dc' for an IVCURVE
    (also aplac_hb, aplac_ac_hb, aplac_trans, aplac_linear...; an unknown name lists the valid ones). It is appended to the
    source name ('AP_IV.AP_DC'), which graph_data then shows. Bad measurements show up as errors after simulate."""
    return await run(gr.add_measurement_sync, graph, source_doc, measurement, simulator)


@mcp.tool()
async def simulate(wait_seconds: int = 0, graph: str | None = None, tidy: bool = True) -> dict:
    """Without graph: start Simulate > Analyze for the whole project and return at once (or wait up to wait_seconds);
    follow with wait_for_simulation. With graph: simulate only that graph's measurements (their schematics), BLOCKING
    until done (a big sweep can take minutes; the call gives up after 15 min), so a broken schematic elsewhere is not
    touched. Clears the status window first, so errors returned belong to this run.
    With graph, the graph is also tidied (see tidy_graph); pass tidy=False to keep axes you set by hand."""
    return await run(gr.simulate_sync, wait_seconds, graph, tidy)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def simulation_state() -> dict:
    """Current simulation state plus the latest error messages."""
    return await run(gr.simulation_state_sync)


@mcp.tool()
async def wait_for_simulation(timeout_s: int = 600) -> dict:
    """Wait until the running whole-project simulation ends (or timeout_s, max 3600), then return state, errors and
    timed_out (true = still running). Returns at once after a graph-only simulate, which is already finished.
    Other AWR tools queue behind this call while it waits."""
    return await run(gr.wait_for_simulation_sync, timeout_s, timeout=timeout_s + 60)


@mcp.tool()
async def delete_graph(name: str) -> dict:
    """Delete a graph and its measurements."""
    return await run(gr.delete_graph_sync, name)


@mcp.tool()
async def delete_measurement(graph: str, measurement: str) -> dict:
    """Remove one measurement from a graph. measurement: the name graph_data shows (e.g. 'V_RC:DB(|S(2,1)|)') or
    just the expression ('DB(|S(2,1)|)') when that is unique on the graph."""
    return await run(gr.delete_measurement_sync, graph, measurement)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def graph_data(graph: str, max_points: int = 2000, summary: bool = False) -> list:
    """Data of every measurement on a graph, in SI base units (Hz, A, V, Rad...; x_unit/y_unit name them). Each trace has a
    label (a family such as an I-V curve is named by its swept value, 'Vstep = -3 V'). summary=True gives per trace min,
    max, x at each (x_at_min finds a resonance dip) and 5 sample points; summary=False gives the full x/y arrays."""
    return await run(gr.graph_data_sync, graph, max_points, summary)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def graph_image(graph: str) -> Image:
    """Plot every measurement on a graph as a PNG so you can look at the curves. Axes carry the sweep and measurement with the
    project's display units (GHz, mA...); family traces are named by the swept value. Log x-axis when x spans >= 2 decades."""
    traces = await run(gr.graph_data_sync, graph, 10**9, False, True)
    return Image(data=gr.graph_png(graph, traces), format="png")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def status_messages(level: str = "all", limit: int = 200) -> list:
    """Read the AWR Status Window. level: 'error', 'warning', 'info' or 'all'."""
    return await run(gr.status_messages_sync, level, limit)


@mcp.tool()
async def clear_status_messages() -> dict:
    """Empty the AWR Status Window, so the next simulate shows only fresh messages."""
    return await run(gr.clear_status_messages_sync)


if __name__ == "__main__":
    if "--selftest" in sys.argv:  # read-only smoke test against the running AWR
        pythoncom.CoInitialize()
        info = project_info_sync()
        print(info)
        assert "project" in info
        print("errors:", gr.status_messages_sync("error", 10))
        for em in info["em_structures"]:
            print(em, "ports:", em_ports_sync(em))
        for gname in info["graphs"]:
            d = gr.graph_data_sync(gname, 3)
            print(gname, [(m["measurement"], m["x"], m["y"]) for m in d])
        print("state:", gr.simulation_state_sync()["state"])
    else:
        hub.start(mcp)
        mcp.run()
